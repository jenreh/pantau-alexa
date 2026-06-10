"""Reusable bearer-token dependency for protected non-Alexa HTTP endpoints."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request

from pantau.ports.token_validator_port import TokenClaims, TokenValidatorPort

log = logging.getLogger(__name__)


async def require_bearer_token(request: Request) -> TokenClaims:
    """Validate the ``Authorization: Bearer`` header; returns the token claims.

    Raises HTTP 401 when the header is missing, malformed, or the token is
    invalid or expired.
    """
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    validator: TokenValidatorPort = request.app.state.container.get(TokenValidatorPort)  # type: ignore[type-abstract]
    try:
        return validator.validate(token)
    except ValueError as exc:
        log.warning("Bearer token validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
