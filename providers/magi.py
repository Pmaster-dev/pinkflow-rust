"""Secondary identity provider: MAGI identity provisioning engine.

MAGI is invoked only when the primary (Copilot OIDC) provider fails and the
FallbackPolicy permits it.  Three operating modes are supported:

  api    – delegates to a remote MAGI API endpoint (production)
  static – resolves identities from an in-process trust map (offline/testing)
  deny   – always raises (disables fallback without changing policy config)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from core.identity import Identity, Provenance
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_CONFIDENCE = 0.75


class MAGIMode(str, Enum):
    API = "api"
    STATIC = "static"
    DENY = "deny"


class MAGIProvider:
    """
    MAGI identity provisioning engine.

    Args:
        mode: Operating mode – 'api', 'static', or 'deny'.
        endpoint: MAGI API base URL (required when mode='api').
        secret: HMAC-SHA256 shared secret used to sign MAGI API requests.
        trust_map: subject → identity-dict mapping for mode='static'.
        timeout: HTTP request timeout in seconds (default 5).
    """

    def __init__(
        self,
        mode: MAGIMode = MAGIMode.STATIC,
        endpoint: Optional[str] = None,
        secret: Optional[str] = None,
        trust_map: Optional[Dict[str, Dict[str, Any]]] = None,
        timeout: int = 5,
    ) -> None:
        self._mode = MAGIMode(mode)
        self._endpoint = endpoint
        self._secret = secret
        self._trust_map: Dict[str, Dict[str, Any]] = trust_map or {}
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def provision(
        self,
        subject: str,
        claims_hint: Optional[Dict[str, Any]] = None,
    ) -> Identity:
        """
        Provision an Identity for *subject* via MAGI.

        Args:
            subject: Identity subject (e.g. repo slug or user identifier).
            claims_hint: Optional partial claims from an unverified token.

        Returns:
            Identity on success.

        Raises:
            ValueError: if MAGI cannot provision an identity.
        """
        if self._mode == MAGIMode.DENY:
            raise ValueError(
                "MAGI is configured in 'deny' mode – fallback is disabled"
            )

        if self._mode == MAGIMode.STATIC:
            return self._static_provision(subject)

        if self._mode == MAGIMode.API:
            return self._api_provision(subject, claims_hint)

        raise ValueError(f"Unknown MAGI mode: {self._mode!r}")  # pragma: no cover

    # ------------------------------------------------------------------
    # Internal – static
    # ------------------------------------------------------------------

    def _static_provision(self, subject: str) -> Identity:
        if subject not in self._trust_map:
            raise ValueError(
                f"MAGI static: subject {subject!r} not found in trust map"
            )
        entry = self._trust_map[subject]
        identity = self._build_identity(subject, entry)
        logger.info("magi.static.provisioned", subject=subject)
        return identity

    # ------------------------------------------------------------------
    # Internal – API
    # ------------------------------------------------------------------

    def _api_provision(
        self, subject: str, claims_hint: Optional[Dict[str, Any]]
    ) -> Identity:
        if not self._endpoint:
            raise ValueError(
                "MAGI API mode requires 'endpoint' to be configured"
            )

        url = f"{self._endpoint.rstrip('/')}/v1/identity/provision"
        payload = json.dumps(
            {"subject": subject, "claims_hint": claims_hint or {}}
        ).encode()
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._secret:
            sig = hmac.new(
                self._secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            headers["X-MAGI-Signature"] = f"sha256={sig}"

        try:
            req = Request(url, data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                body: Dict[str, Any] = json.loads(resp.read())
        except URLError as exc:
            raise ValueError(f"MAGI API unreachable: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"MAGI API returned invalid JSON: {exc}") from exc

        if not body.get("granted", False):
            reason = body.get("reason", "identity not granted")
            raise ValueError(f"MAGI API denied identity: {reason}")

        entry: Dict[str, Any] = body.get("identity", {})
        identity = self._build_identity(subject, entry)
        logger.info("magi.api.provisioned", subject=subject, url=url)
        return identity

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _build_identity(
        self, subject: str, entry: Dict[str, Any]
    ) -> Identity:
        now = time.time()
        return Identity(
            subject=subject,
            tenant=entry.get("tenant", "unknown"),
            roles=entry.get("roles", []),
            scopes=entry.get("scopes", []),
            provenance=Provenance.MAGI,
            confidence=float(entry.get("confidence", _DEFAULT_CONFIDENCE)),
            issued_at=now,
            expires_at=entry.get("expires_at"),
            raw_claims=entry,
        )
