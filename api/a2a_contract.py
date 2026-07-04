"""A2A authentication contract: token format, claims schema, and trust rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# GitHub Actions OIDC issuer
GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"

# Copilot workspace OIDC issuer
COPILOT_OIDC_ISSUER = "https://copilot-proxy.githubusercontent.com"

# Default trusted issuers (primary Copilot/GitHub)
DEFAULT_TRUSTED_ISSUERS: frozenset = frozenset(
    {GITHUB_OIDC_ISSUER, COPILOT_OIDC_ISSUER}
)

# Default audience that every A2A token must target
DEFAULT_AUDIENCE = "pinkflow-api"

# Scopes that every A2A token must carry
REQUIRED_SCOPES: List[str] = ["a2a:invoke"]


@dataclass(frozen=True)
class A2AContract:
    """Defines the trust rules and expected claims for A2A tokens."""

    audience: str = DEFAULT_AUDIENCE
    trusted_issuers: frozenset = field(
        default_factory=lambda: frozenset(DEFAULT_TRUSTED_ISSUERS)
    )
    required_scopes: tuple = field(
        default_factory=lambda: tuple(REQUIRED_SCOPES)
    )
    # Allowed clock skew in seconds
    leeway: int = 30

    def is_trusted_issuer(self, issuer: str) -> bool:
        return issuer in self.trusted_issuers

    def check_scopes(self, token_scopes: List[str]) -> bool:
        return all(s in token_scopes for s in self.required_scopes)
