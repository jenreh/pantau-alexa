"""Port: OAuth2 bearer token validation."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class TokenClaims(BaseModel):
    """Validated claims extracted from a bearer token."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    scope: str


class TokenValidatorPort(Protocol):
    """Validates Alexa bearer tokens (JWTs issued by our OAuth2 server)."""

    def validate(self, token: str) -> TokenClaims:
        """Validate the token and return its claims. Raises ValueError if invalid."""
        ...
