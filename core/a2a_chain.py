"""A2A auth chain: orchestrates Copilot OIDC (primary) → MAGI (fallback).

Authentication flow
-------------------
1. If no token is present, go directly to fallback evaluation.
2. Attempt full cryptographic verification via CopilotOIDCProvider.
3. On failure, extract the subject from unverified claims and ask
   FallbackPolicy whether MAGI is permitted.
4. If permitted, call MAGIProvider.provision(); validate confidence.
5. Return the first successfully verified Identity, or raise PermissionError.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from api.a2a_contract import A2AContract
from core.identity import Identity
from policy.fallback_policy import FallbackPolicy
from providers.copilot_oidc import CopilotOIDCProvider
from providers.magi import MAGIMode, MAGIProvider
from utils.logger import get_logger

logger = get_logger(__name__)


class A2AAuthChain:
    """
    Ordered identity-provider chain for A2A authentication.

    Args:
        contract: A2A contract describing trust rules and required claims.
        policy: Fallback policy governing when MAGI is invoked.
        magi: Pre-configured MAGIProvider instance.
    """

    def __init__(
        self,
        contract: Optional[A2AContract] = None,
        policy: Optional[FallbackPolicy] = None,
        magi: Optional[MAGIProvider] = None,
    ) -> None:
        self._contract = contract or A2AContract()
        self._policy = policy or FallbackPolicy()
        self._primary = CopilotOIDCProvider(self._contract)
        self._magi = magi or MAGIProvider(mode=MAGIMode.STATIC)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def authenticate(self, token: Optional[str]) -> Identity:
        """
        Authenticate a request using the A2A chain.

        Args:
            token: Raw JWT string, or None / empty string if not provided.

        Returns:
            Verified Identity.

        Raises:
            PermissionError: if every provider in the chain denies the request.
        """
        if not token:
            logger.info("a2a.chain.no_token")
            return self._fallback("", "missing_token", token=None)

        # --- Primary: Copilot / GitHub OIDC ---
        primary_error: Optional[str] = None
        try:
            identity = self._primary.verify(token)
            logger.info(
                "a2a.chain.primary.success",
                subject=identity.subject,
                provenance=identity.provenance,
                confidence=identity.confidence,
            )
            return identity
        except (ValueError, ImportError) as exc:
            primary_error = str(exc)
            logger.warning("a2a.chain.primary.failed", reason=primary_error)

        subject = self._peek_subject(token)
        return self._fallback(subject, primary_error or "unknown", token=token)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fallback(
        self, subject: str, failure_reason: str, token: Optional[str]
    ) -> Identity:
        if not self._policy.should_fallback(subject, failure_reason):
            raise PermissionError(
                f"A2A auth denied. Primary failure: {failure_reason}. "
                "Fallback not permitted by policy."
            )

        claims_hint: Optional[Dict[str, Any]] = (
            self._peek_claims(token) if token else None
        )

        try:
            identity = self._magi.provision(subject, claims_hint)
        except ValueError as exc:
            raise PermissionError(
                f"A2A auth denied. Primary: {failure_reason}. "
                f"MAGI fallback failed: {exc}"
            ) from exc

        if not self._policy.validate_identity(identity.confidence):
            raise PermissionError(
                f"A2A auth denied. MAGI identity confidence "
                f"{identity.confidence:.2f} is below the required threshold "
                f"{self._policy.min_fallback_confidence:.2f}."
            )

        logger.info(
            "a2a.chain.magi.success",
            subject=identity.subject,
            confidence=identity.confidence,
            primary_failure=failure_reason,
        )
        return identity

    @staticmethod
    def _peek_subject(token: str) -> str:
        """Extract subject from an unverified token (best-effort)."""
        try:
            import jwt  # noqa: PLC0415

            claims = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256", "ES256", "HS256"],
            )
            return str(claims.get("sub", ""))
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _peek_claims(token: str) -> Dict[str, Any]:
        """Extract all claims from an unverified token (best-effort)."""
        try:
            import jwt  # noqa: PLC0415

            return jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256", "ES256", "HS256"],
            )
        except Exception:  # noqa: BLE001
            return {}
