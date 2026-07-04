"""Primary identity provider: Copilot/GitHub OIDC id-token verification.

Verifies RS256/ES256-signed JWTs issued by GitHub Actions or the Copilot
proxy OIDC provider.  The JWKS endpoint is resolved automatically via the
issuer's OpenID Connect discovery document.

Requires: PyJWT>=2.12.0 cryptography>=48.0.1
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List
from urllib.request import urlopen

try:
    import jwt
    from jwt import InvalidTokenError, PyJWKClient
    from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError

    HAS_JWT = True
except ImportError:  # pragma: no cover
    HAS_JWT = False

from api.a2a_contract import A2AContract
from core.identity import Identity, Provenance
from policy.fallback_policy import SENTINEL_EXPIRED, SENTINEL_SIGNATURE
from utils.logger import get_logger

logger = get_logger(__name__)

_OIDC_DISCOVERY_TEMPLATE = "{}/.well-known/openid-configuration"
_SUPPORTED_ALGORITHMS = ["RS256", "ES256"]


class CopilotOIDCProvider:
    """
    Verifies GitHub/Copilot OIDC id-tokens against the issuer's JWKS.

    Raises:
        ValueError: if the token is malformed, untrusted, expired, or has
            insufficient scopes.  The message starts with one of the policy
            sentinels (SENTINEL_EXPIRED, SENTINEL_SIGNATURE) so that
            FallbackPolicy can make accurate routing decisions.
    """

    def __init__(self, contract: A2AContract) -> None:
        self._contract = contract
        # Lazily populated JWKS clients keyed by issuer
        self._jwks_clients: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def verify(self, token: str) -> Identity:
        """
        Verify *token* and return a normalized Identity.

        Args:
            token: Raw JWT string.

        Returns:
            Identity on success.

        Raises:
            ValueError: on any verification failure.
        """
        if not HAS_JWT:
            raise ImportError(  # pragma: no cover
                "PyJWT is required: pip install 'PyJWT>=2.12.0' 'cryptography>=48.0.1'"
            )

        # Peek at claims without signature verification to get issuer
        try:
            unverified: Dict[str, Any] = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=_SUPPORTED_ALGORITHMS,
            )
        except Exception as exc:
            raise ValueError(f"Malformed token: {exc}") from exc

        issuer: str = unverified.get("iss", "")
        if not self._contract.is_trusted_issuer(issuer):
            raise ValueError(f"Untrusted issuer: {issuer!r}")

        # Full cryptographic verification
        try:
            signing_key = self._jwks_client(issuer).get_signing_key_from_jwt(token)
            claims: Dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=_SUPPORTED_ALGORITHMS,
                audience=self._contract.audience,
                leeway=self._contract.leeway,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except ExpiredSignatureError as exc:
            raise ValueError(f"{SENTINEL_EXPIRED}: {exc}") from exc
        except InvalidSignatureError as exc:
            raise ValueError(f"{SENTINEL_SIGNATURE}: {exc}") from exc
        except InvalidTokenError as exc:
            raise ValueError(f"OIDC token verification failed: {exc}") from exc

        # Scope enforcement
        scope_str: str = claims.get("scope", "")
        token_scopes: List[str] = scope_str.split() if scope_str else []
        if not self._contract.check_scopes(token_scopes):
            raise ValueError(
                f"Insufficient scopes. Required: {list(self._contract.required_scopes)}, "
                f"got: {token_scopes}"
            )

        identity = Identity(
            subject=claims["sub"],
            tenant=claims.get("tenant", claims.get("repository_owner", "unknown")),
            roles=claims.get("roles", []),
            scopes=token_scopes,
            provenance=Provenance.COPILOT_OIDC,
            confidence=1.0,
            issued_at=float(claims.get("iat", time.time())),
            expires_at=float(claims.get("exp", time.time() + 3600)),
            raw_claims=claims,
        )
        logger.info(
            "copilot_oidc.verify.success",
            subject=identity.subject,
            tenant=identity.tenant,
            issuer=issuer,
        )
        return identity

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _jwks_client(self, issuer: str) -> "PyJWKClient":
        if issuer not in self._jwks_clients:
            jwks_uri = self._discover_jwks_uri(issuer)
            self._jwks_clients[issuer] = PyJWKClient(jwks_uri)
        return self._jwks_clients[issuer]

    @staticmethod
    def _discover_jwks_uri(issuer: str) -> str:
        url = _OIDC_DISCOVERY_TEMPLATE.format(issuer)
        with urlopen(url, timeout=10) as resp:  # noqa: S310 – issuer is allowlisted
            doc: Dict[str, Any] = json.loads(resp.read())
        return doc["jwks_uri"]
