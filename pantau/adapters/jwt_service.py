"""Adapter: JWT issuing and validation.

Implements TokenValidatorPort; also used by the OAuth token endpoint to issue
access tokens. Single adapter = single source of truth for secret + algorithm.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from pantau.ports.token_validator_port import TokenClaims

log = logging.getLogger(__name__)

_SCOPE = "alexa"


class JwtService:
    """Issues and validates HS256-signed JWTs for the home-automation skill.

    Implements TokenIssuerPort and TokenValidatorPort. Secret and parameters
    are injected by the composition root (no config-layer dependency here).
    """

    def __init__(
        self,
        secret: str,
        *,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_expire_minutes = access_token_expire_minutes

    # ------------------------------------------------------------------
    # Issuing
    # ------------------------------------------------------------------

    def issue_access_token(self, user_id: str) -> tuple[str, int]:
        """Return (encoded_jwt, expires_in_seconds)."""
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self._access_expire_minutes)
        payload = {
            "sub": user_id,
            "scope": _SCOPE,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": secrets.token_hex(16),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        expires_in = int((expire - now).total_seconds())
        return token, expires_in

    def issue_refresh_token(self) -> str:
        """Return a random, opaque refresh token (stored in the user store)."""
        return secrets.token_urlsafe(32)

    # ------------------------------------------------------------------
    # Validation — implements TokenValidatorPort (sync, as jose.decode is sync)
    # ------------------------------------------------------------------

    def validate(self, token: str) -> TokenClaims:
        """Validate *token* and return its claims. Raises ValueError if invalid."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            log.warning("JWT validation failed: %s", exc)
            raise ValueError("Invalid or expired token") from exc

        user_id = payload.get("sub")
        scope = payload.get("scope", "")
        if not user_id:
            raise ValueError("Token missing 'sub' claim")

        return TokenClaims(user_id=str(user_id), scope=str(scope))
