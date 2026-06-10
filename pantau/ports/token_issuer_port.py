"""Port: OAuth2 access/refresh token issuing."""

from __future__ import annotations

from typing import Protocol


class TokenIssuerPort(Protocol):
    """Issues access tokens (JWT) and opaque refresh tokens."""

    def issue_access_token(self, user_id: str) -> tuple[str, int]:
        """Return (encoded_token, expires_in_seconds)."""
        ...

    def issue_refresh_token(self) -> str:
        """Return a random, opaque refresh token."""
        ...
