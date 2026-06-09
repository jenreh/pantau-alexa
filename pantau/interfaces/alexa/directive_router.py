"""FastAPI router — POST /alexa/directive.

Token validation is Phase 4; this endpoint accepts the bearer token but does not
validate it yet.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from pantau.interfaces.alexa.router import AlexaDirectiveRouter

log = logging.getLogger(__name__)

alexa_router = APIRouter(prefix="/alexa", tags=["alexa"])


@alexa_router.post("/directive")
async def handle_directive(request: Request) -> JSONResponse:
    """Receive an Alexa Smart Home directive and return an Alexa response."""
    body = await request.json()
    router: AlexaDirectiveRouter = request.app.state.container.get(AlexaDirectiveRouter)
    response = await router.route(body)
    return JSONResponse(response)
