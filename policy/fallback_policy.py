"""Fallback policy: controls when MAGI is permitted as a secondary provider.

Sentinels embedded in ValueError messages by the primary provider allow the
policy to distinguish denial causes without leaking internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from utils.logger import get_logger

logger = get_logger(__name__)

# Sentinels that primary providers must embed in ValueError messages
SENTINEL_EXPIRED = "token_expired"
SENTINEL_REPLAY = "token_replay"
SENTINEL_SIGNATURE = "token_invalid_signature"


@dataclass
class FallbackPolicy:
    """
    Determines whether MAGI fallback is permitted for a given failure.

    Attributes:
        allow_on_missing_token: Permit MAGI when no token is presented at all.
        allow_on_invalid_signature: Permit MAGI when signature verification
            fails (disabled by default – never recommended in production).
        deny_on_expired: Hard-deny when the primary token is expired.
        deny_on_replay: Hard-deny when a replay attempt is detected.
        allowed_subjects: Allowlist – if non-empty only listed subjects may
            use MAGI fallback.
        denied_subjects: Blocklist – these subjects are always denied, even
            via MAGI (anti-loop safeguard).
        min_fallback_confidence: MAGI identity confidence must be ≥ this
            value to be accepted.
    """

    allow_on_missing_token: bool = True
    allow_on_invalid_signature: bool = False
    deny_on_expired: bool = True
    deny_on_replay: bool = True
    allowed_subjects: List[str] = field(default_factory=list)
    denied_subjects: List[str] = field(default_factory=list)
    min_fallback_confidence: float = 0.5

    def should_fallback(self, subject: str, failure_reason: str) -> bool:
        """
        Return True if MAGI fallback is permitted for this failure.

        Args:
            subject: The requesting subject extracted from the (unverified)
                token, or an empty string if none could be determined.
            failure_reason: Failure message from the primary provider.
        """
        # Hard-deny: blocked subjects may never use fallback (anti-loop)
        if subject and subject in self.denied_subjects:
            logger.warning(
                "fallback.denied.subject_blocklisted", subject=subject
            )
            return False

        # Hard-deny: expired tokens must never fall through
        if self.deny_on_expired and SENTINEL_EXPIRED in failure_reason:
            logger.warning("fallback.denied.token_expired", subject=subject)
            return False

        # Hard-deny: detected replay attacks must never fall through
        if self.deny_on_replay and SENTINEL_REPLAY in failure_reason:
            logger.warning("fallback.denied.token_replay", subject=subject)
            return False

        # Hard-deny: invalid signature (configurable, off by default)
        if SENTINEL_SIGNATURE in failure_reason and not self.allow_on_invalid_signature:
            logger.warning(
                "fallback.denied.invalid_signature", subject=subject
            )
            return False

        # Missing-token fallback gating
        if not subject and not self.allow_on_missing_token:
            logger.warning("fallback.denied.missing_token")
            return False

        # Subject allowlist enforcement
        if self.allowed_subjects and subject not in self.allowed_subjects:
            logger.warning(
                "fallback.denied.not_in_allowlist", subject=subject
            )
            return False

        return True

    def validate_identity(self, confidence: float) -> bool:
        """Return True if a MAGI identity meets the minimum confidence."""
        return confidence >= self.min_fallback_confidence
