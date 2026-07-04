"""FastAPI router exposing the /a2a/auth endpoint.

The endpoint accepts a ****** via the Authorization header, runs the
full A2A chain (Copilot OIDC primary → MAGI fallback), and returns the
normalized identity on success.

FastAPI is optional: if it is not installed the module imports without error
but ``router`` is not defined, and the endpoint cannot be registered.
"""
from __future__ import annotations

from typing import Optional

try:
    from fastapi import APIRouter, Header, HTTPException, status

    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    _HAS_FASTAPI = False

from core.a2a_chain import A2AAuthChain
from utils.logger import get_logger

logger = get_logger(__name__)

if _HAS_FASTAPI:
    router = APIRouter(prefix="/a2a", tags=["a2a-auth"])

    # Module-level chain with default contract, policy and MAGI config.
    # Override by replacing this instance before the app starts.
    _chain: A2AAuthChain = A2AAuthChain()

    @router.post("/auth", summary="A2A authentication")
    def authenticate(
        authorization: Optional[str] = Header(
            default=None, alias="Authorization"
        ),
    ) -> dict:
        """
        Authenticate an A2A request.

        Reads a ****** from the ``Authorization`` header, runs the
        A2A chain (Copilot OIDC → MAGI fallback) and returns the caller's
        normalized identity on success.

        Returns HTTP 401 if every provider in the chain denies the request.
        """
        token: Optional[str] = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip() or None

        try:
            identity = _chain.authenticate(token)
        except PermissionError as exc:
            logger.warning("a2a.auth.denied", reason=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc

        return {
            "subject": identity.subject,
            "tenant": identity.tenant,
            "roles": identity.roles,
            "scopes": identity.scopes,
            "provenance": identity.provenance,
            "confidence": identity.confidence,
        }
