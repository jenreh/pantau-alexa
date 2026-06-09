"""Port: OAuth2 bearer token validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Validated claims extracted from a bearer token."""

    user_id: str
    scope: str


class TokenValidatorPort(Protocol):
    """Validates Alexa bearer tokens (JWTs issued by our OAuth2 server)."""

    def validate(self, token: str) -> TokenClaims:
        """Validate the token and return its claims. Raises ValueError if invalid."""
        ...
