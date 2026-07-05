"""Normalized internal identity model shared across all A2A providers."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Provenance(str, Enum):
    COPILOT_OIDC = "copilot_oidc"
    MAGI = "magi"
    UNKNOWN = "unknown"


@dataclass
class Identity:
    """Normalized identity produced by any A2A identity provider."""

    subject: str
    tenant: str
    roles: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    provenance: Provenance = Provenance.UNKNOWN
    confidence: float = 0.0  # 0.0–1.0
    issued_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    raw_claims: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_role(self, role: str) -> bool:
        return role in self.roles
