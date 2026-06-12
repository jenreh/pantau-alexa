"""Port: short-lived OAuth2 authorization-code storage (PKCE)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class AuthCodeEntry(BaseModel):
    """A stored authorization code with its binding claims."""

    model_config = ConfigDict(frozen=True)

    code: str
    user_id: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    expires_at: datetime


class AuthCodeStorePort(Protocol):
    """Store for single-use PKCE authorization codes."""

    async def save(
        self,
        *,
        user_id: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> str: ...

    async def lookup(self, code: str) -> AuthCodeEntry | None: ...

    async def redeem(self, code: str) -> AuthCodeEntry | None: ...
