"""Tests for the A2A authentication chain.

Coverage paths
--------------
1. Primary success      – Copilot OIDC verifies → Identity(provenance=COPILOT_OIDC)
2. Fallback success     – primary fails, policy allows, MAGI provisions Identity
3. Full deny (policy)   – primary fails, policy blocks fallback → PermissionError
4. Full deny (MAGI)     – primary fails, policy allows, MAGI also fails → PermissionError
5. Malformed token      – unparseable JWT → primary raises, chain evaluates policy
6. Expired token        – primary raises SENTINEL_EXPIRED → policy hard-denies
7. Replay token         – primary raises SENTINEL_REPLAY → policy hard-denies
8. Missing token        – no token, allow_on_missing_token=True → MAGI success
9. Missing token denied – no token, allow_on_missing_token=False → PermissionError
10. Subject blocklisted – subject in denied_subjects → PermissionError
11. Confidence too low  – MAGI returns confidence < threshold → PermissionError
12. Signature denied    – SENTINEL_SIGNATURE, allow_on_invalid_signature=False → denied
13. Signature allowed   – SENTINEL_SIGNATURE, allow_on_invalid_signature=True → MAGI

Unit tests are also included for:
- Identity model helpers
- A2AContract helpers
- FallbackPolicy helpers
- MAGIProvider static mode
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from api.a2a_contract import A2AContract
from core.a2a_chain import A2AAuthChain
from core.identity import Identity, Provenance
from policy.fallback_policy import (
    SENTINEL_EXPIRED,
    SENTINEL_REPLAY,
    SENTINEL_SIGNATURE,
    FallbackPolicy,
)
from providers.magi import MAGIMode, MAGIProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_identity(
    provenance: Provenance = Provenance.COPILOT_OIDC,
    subject: str = "repo:org/repo:ref:refs/heads/main",
    tenant: str = "org",
    roles: Optional[List[str]] = None,
    scopes: Optional[List[str]] = None,
    confidence: float = 1.0,
    expires_at: Optional[float] = None,
) -> Identity:
    return Identity(
        subject=subject,
        tenant=tenant,
        roles=roles or ["agent"],
        scopes=scopes or ["a2a:invoke"],
        provenance=provenance,
        confidence=confidence,
        expires_at=expires_at,
    )


def _magi_with_map(subject: str, **entry_overrides: Any) -> MAGIProvider:
    """Create a static MAGIProvider pre-loaded with one trust-map entry."""
    entry: Dict[str, Any] = {
        "tenant": "org",
        "roles": ["agent"],
        "scopes": ["a2a:invoke"],
        "confidence": 0.75,
    }
    entry.update(entry_overrides)
    return MAGIProvider(mode=MAGIMode.STATIC, trust_map={subject: entry})


# ---------------------------------------------------------------------------
# Identity model
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_not_expired_when_no_expiry(self) -> None:
        identity = _make_identity(expires_at=None)
        assert not identity.is_expired()

    def test_not_expired_future(self) -> None:
        identity = _make_identity(expires_at=time.time() + 3600)
        assert not identity.is_expired()

    def test_expired_past(self) -> None:
        identity = _make_identity(expires_at=time.time() - 1)
        assert identity.is_expired()

    def test_has_scope(self) -> None:
        identity = _make_identity(scopes=["a2a:invoke", "read:identity"])
        assert identity.has_scope("a2a:invoke")
        assert identity.has_scope("read:identity")
        assert not identity.has_scope("admin:all")

    def test_has_role(self) -> None:
        identity = _make_identity(roles=["agent", "reader"])
        assert identity.has_role("agent")
        assert not identity.has_role("admin")


# ---------------------------------------------------------------------------
# A2AContract
# ---------------------------------------------------------------------------


class TestA2AContract:
    def test_trusted_issuer(self) -> None:
        contract = A2AContract()
        assert contract.is_trusted_issuer(
            "https://token.actions.githubusercontent.com"
        )

    def test_untrusted_issuer(self) -> None:
        contract = A2AContract()
        assert not contract.is_trusted_issuer("https://evil.example.com")

    def test_scopes_sufficient(self) -> None:
        contract = A2AContract()
        assert contract.check_scopes(["a2a:invoke", "read:identity"])

    def test_scopes_insufficient(self) -> None:
        contract = A2AContract()
        assert not contract.check_scopes(["read:identity"])

    def test_custom_audience(self) -> None:
        contract = A2AContract(audience="my-service")
        assert contract.audience == "my-service"


# ---------------------------------------------------------------------------
# FallbackPolicy
# ---------------------------------------------------------------------------


class TestFallbackPolicy:
    def test_allows_generic_failure_by_default(self) -> None:
        policy = FallbackPolicy()
        assert policy.should_fallback("sub", "some_generic_error")

    def test_denies_expired(self) -> None:
        policy = FallbackPolicy()
        assert not policy.should_fallback("sub", f"{SENTINEL_EXPIRED}: token is old")

    def test_denies_replay(self) -> None:
        policy = FallbackPolicy()
        assert not policy.should_fallback("sub", f"detected {SENTINEL_REPLAY}")

    def test_denies_signature_by_default(self) -> None:
        policy = FallbackPolicy()
        assert not policy.should_fallback("sub", f"{SENTINEL_SIGNATURE}: mismatch")

    def test_allows_signature_when_configured(self) -> None:
        policy = FallbackPolicy(allow_on_invalid_signature=True)
        assert policy.should_fallback("sub", f"{SENTINEL_SIGNATURE}: mismatch")

    def test_denies_blocklisted_subject(self) -> None:
        policy = FallbackPolicy(denied_subjects=["bad-actor"])
        assert not policy.should_fallback("bad-actor", "some_error")

    def test_denies_subject_not_in_allowlist(self) -> None:
        policy = FallbackPolicy(allowed_subjects=["approved-sub"])
        assert not policy.should_fallback("other-sub", "some_error")

    def test_allows_subject_in_allowlist(self) -> None:
        policy = FallbackPolicy(allowed_subjects=["approved-sub"])
        assert policy.should_fallback("approved-sub", "some_error")

    def test_allows_missing_token_by_default(self) -> None:
        policy = FallbackPolicy()
        assert policy.should_fallback("", "missing_token")

    def test_denies_missing_token_when_disabled(self) -> None:
        policy = FallbackPolicy(allow_on_missing_token=False)
        assert not policy.should_fallback("", "missing_token")

    def test_validate_identity_above_threshold(self) -> None:
        policy = FallbackPolicy(min_fallback_confidence=0.5)
        assert policy.validate_identity(0.75)

    def test_validate_identity_at_threshold(self) -> None:
        policy = FallbackPolicy(min_fallback_confidence=0.5)
        assert policy.validate_identity(0.5)

    def test_validate_identity_below_threshold(self) -> None:
        policy = FallbackPolicy(min_fallback_confidence=0.5)
        assert not policy.validate_identity(0.3)


# ---------------------------------------------------------------------------
# MAGIProvider (static mode)
# ---------------------------------------------------------------------------


class TestMAGIProviderStatic:
    def test_provisions_known_subject(self) -> None:
        magi = _magi_with_map("user:alice")
        identity = magi.provision("user:alice")
        assert identity.subject == "user:alice"
        assert identity.provenance == Provenance.MAGI
        assert identity.confidence == 0.75

    def test_raises_for_unknown_subject(self) -> None:
        magi = MAGIProvider(mode=MAGIMode.STATIC, trust_map={})
        with pytest.raises(ValueError, match="not found in trust map"):
            magi.provision("unknown")

    def test_deny_mode_always_raises(self) -> None:
        magi = MAGIProvider(mode=MAGIMode.DENY)
        with pytest.raises(ValueError, match="deny"):
            magi.provision("any-subject")

    def test_custom_roles_and_scopes(self) -> None:
        magi = _magi_with_map(
            "svc:builder",
            roles=["builder", "deployer"],
            scopes=["a2a:invoke", "build:run"],
        )
        identity = magi.provision("svc:builder")
        assert "builder" in identity.roles
        assert "build:run" in identity.scopes

    def test_custom_confidence(self) -> None:
        magi = _magi_with_map("svc:x", confidence=0.9)
        identity = magi.provision("svc:x")
        assert identity.confidence == 0.9


# ---------------------------------------------------------------------------
# A2AAuthChain – integration-level (providers mocked)
# ---------------------------------------------------------------------------


class TestA2AAuthChain:
    """Chain-level tests; individual providers are mocked to isolate logic."""

    # ------------------------------------------------------------------
    # Path 1: Primary success
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    def test_primary_success(self, mock_verify: MagicMock) -> None:
        expected = _make_identity(Provenance.COPILOT_OIDC)
        mock_verify.return_value = expected

        chain = A2AAuthChain()
        identity = chain.authenticate("some.valid.token")

        mock_verify.assert_called_once_with("some.valid.token")
        assert identity.provenance == Provenance.COPILOT_OIDC
        assert identity.confidence == 1.0

    # ------------------------------------------------------------------
    # Path 2: Fallback success
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch("core.a2a_chain.MAGIProvider.provision")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="repo:org/app")
    def test_fallback_success(
        self,
        _mock_peek: MagicMock,
        mock_provision: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.side_effect = ValueError("some_error")
        magi_identity = _make_identity(Provenance.MAGI, confidence=0.75)
        mock_provision.return_value = magi_identity

        policy = FallbackPolicy()  # allow generic failures
        chain = A2AAuthChain(policy=policy)
        identity = chain.authenticate("some.token.here")

        mock_provision.assert_called_once()
        assert identity.provenance == Provenance.MAGI

    # ------------------------------------------------------------------
    # Path 3: Full deny – policy blocks fallback
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="blocked")
    def test_full_deny_policy_blocks(
        self, _mock_peek: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.side_effect = ValueError("some_error")
        policy = FallbackPolicy(denied_subjects=["blocked"])
        chain = A2AAuthChain(policy=policy)

        with pytest.raises(PermissionError, match="Fallback not permitted"):
            chain.authenticate("some.token")

    # ------------------------------------------------------------------
    # Path 4: Full deny – MAGI also fails
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch("core.a2a_chain.MAGIProvider.provision")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="repo:org/app")
    def test_full_deny_magi_fails(
        self,
        _mock_peek: MagicMock,
        mock_provision: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.side_effect = ValueError("some_error")
        mock_provision.side_effect = ValueError("MAGI offline")
        chain = A2AAuthChain()

        with pytest.raises(PermissionError, match="MAGI fallback failed"):
            chain.authenticate("some.token")

    # ------------------------------------------------------------------
    # Path 5: Malformed token
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch("core.a2a_chain.MAGIProvider.provision")
    def test_malformed_token_falls_back(
        self,
        mock_provision: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.side_effect = ValueError("Malformed token: ...")
        magi_identity = _make_identity(Provenance.MAGI, subject="", confidence=0.75)
        mock_provision.return_value = magi_identity

        chain = A2AAuthChain()
        identity = chain.authenticate("not.a.real.jwt")

        assert identity.provenance == Provenance.MAGI

    # ------------------------------------------------------------------
    # Path 6: Expired token – hard deny
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="user:alice")
    def test_expired_token_hard_deny(
        self, _mock_peek: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.side_effect = ValueError(
            f"{SENTINEL_EXPIRED}: signature has expired"
        )
        chain = A2AAuthChain()

        with pytest.raises(PermissionError, match="Fallback not permitted"):
            chain.authenticate("expired.token.here")

    # ------------------------------------------------------------------
    # Path 7: Replay token – hard deny
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="user:alice")
    def test_replay_token_hard_deny(
        self, _mock_peek: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.side_effect = ValueError(
            f"detected {SENTINEL_REPLAY} attack"
        )
        chain = A2AAuthChain()

        with pytest.raises(PermissionError, match="Fallback not permitted"):
            chain.authenticate("replayed.token")

    # ------------------------------------------------------------------
    # Path 8: Missing token – fallback allowed
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.MAGIProvider.provision")
    def test_missing_token_fallback_allowed(
        self, mock_provision: MagicMock
    ) -> None:
        magi_identity = _make_identity(Provenance.MAGI, subject="", confidence=0.75)
        mock_provision.return_value = magi_identity

        chain = A2AAuthChain(policy=FallbackPolicy(allow_on_missing_token=True))
        identity = chain.authenticate(None)

        mock_provision.assert_called_once_with("", None)
        assert identity.provenance == Provenance.MAGI

    # ------------------------------------------------------------------
    # Path 9: Missing token – fallback disabled
    # ------------------------------------------------------------------

    def test_missing_token_fallback_denied(self) -> None:
        chain = A2AAuthChain(
            policy=FallbackPolicy(allow_on_missing_token=False)
        )
        with pytest.raises(PermissionError, match="Fallback not permitted"):
            chain.authenticate(None)

    # ------------------------------------------------------------------
    # Path 10: Subject blocklisted
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="bad-actor")
    def test_subject_blocklisted(
        self, _mock_peek: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.side_effect = ValueError("some_error")
        policy = FallbackPolicy(denied_subjects=["bad-actor"])
        chain = A2AAuthChain(policy=policy)

        with pytest.raises(PermissionError, match="Fallback not permitted"):
            chain.authenticate("token.for.bad.actor")

    # ------------------------------------------------------------------
    # Path 11: MAGI confidence below threshold
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch("core.a2a_chain.MAGIProvider.provision")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="low-conf-svc")
    def test_magi_confidence_too_low(
        self,
        _mock_peek: MagicMock,
        mock_provision: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.side_effect = ValueError("some_error")
        mock_provision.return_value = _make_identity(
            Provenance.MAGI, confidence=0.2
        )
        policy = FallbackPolicy(min_fallback_confidence=0.5)
        chain = A2AAuthChain(policy=policy)

        with pytest.raises(PermissionError, match="below the required threshold"):
            chain.authenticate("token.here")

    # ------------------------------------------------------------------
    # Path 12 & 13: Invalid signature – policy-controlled
    # ------------------------------------------------------------------

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="some-svc")
    def test_invalid_signature_denied_by_default(
        self, _mock_peek: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.side_effect = ValueError(
            f"{SENTINEL_SIGNATURE}: sig mismatch"
        )
        chain = A2AAuthChain()  # allow_on_invalid_signature=False by default

        with pytest.raises(PermissionError, match="Fallback not permitted"):
            chain.authenticate("bad.sig.token")

    @patch("core.a2a_chain.CopilotOIDCProvider.verify")
    @patch("core.a2a_chain.MAGIProvider.provision")
    @patch.object(A2AAuthChain, "_peek_subject", return_value="some-svc")
    def test_invalid_signature_allowed_when_configured(
        self,
        _mock_peek: MagicMock,
        mock_provision: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.side_effect = ValueError(
            f"{SENTINEL_SIGNATURE}: sig mismatch"
        )
        mock_provision.return_value = _make_identity(
            Provenance.MAGI, confidence=0.75
        )
        policy = FallbackPolicy(allow_on_invalid_signature=True)
        chain = A2AAuthChain(policy=policy)

        identity = chain.authenticate("bad.sig.token")
        assert identity.provenance == Provenance.MAGI
