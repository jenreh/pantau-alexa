"""Port: user and refresh-token persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class UserRecord(BaseModel):
    """A stored user."""

    model_config = ConfigDict(frozen=True)

    id: str
    username: str
    password_hash: str


class UserStorePort(Protocol):
    """Persistent store for users and rotating refresh tokens."""

    async def get_user_by_username(self, username: str) -> UserRecord | None: ...

    async def create_user(self, username: str, password_hash: str) -> UserRecord: ...

    async def save_refresh_token(
        self, token: str, user_id: str, expires_at: datetime
    ) -> None: ...

    async def revoke_refresh_token(self, token: str) -> None: ...

    async def pop_refresh_token(self, token: str) -> str | None: ...
