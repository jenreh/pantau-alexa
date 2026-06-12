"""Port: password hashing and verification."""

from __future__ import annotations

from typing import Protocol


class PasswordHasherPort(Protocol):
    """Hashes and verifies user passwords.

    ``verify_password`` accepts ``hashed=None`` for unknown users: the
    implementation must burn comparable CPU time against a dummy hash and
    return False, so login latency does not reveal whether a username exists.
    """

    def hash_password(self, plain: str) -> str: ...

    def verify_password(self, plain: str, hashed: str | None) -> bool: ...
