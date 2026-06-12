"""Adapter: bcrypt password hashing.

Single source of truth for password hashing — used by the OAuth login flow
(via PasswordHasherPort) and the tiberio-users CLI.
"""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plain-text password for storage."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class BcryptPasswordHasher:
    """Implements PasswordHasherPort with a lazy dummy hash for unknown users."""

    def __init__(self) -> None:
        self._dummy_hash: str | None = None

    def hash_password(self, plain: str) -> str:
        return hash_password(plain)

    def verify_password(self, plain: str, hashed: str | None) -> bool:
        """Verify *plain*; for hashed=None burns equal time and returns False.

        The dummy hash uses the same cost factor as real hashes (both come
        from ``hash_password``), keeping verification timing comparable.
        """
        if self._dummy_hash is None:
            self._dummy_hash = hash_password("dummy-password")
        target = hashed if hashed is not None else self._dummy_hash
        matches = verify_password(plain, target)
        return matches and hashed is not None
