"""Pydantic models for Alexa Smart Home directive parsing.

Shapes are sourced from the official Alexa Smart Home API v3 docs.
"""

from __future__ import annotations

from pydantic import BaseModel


class Scope(BaseModel):
    type: str
    token: str


class DirectiveEndpoint(BaseModel):
    endpointId: str  # noqa: N815
    scope: Scope | None = None
    cookie: dict = {}


class DirectiveHeader(BaseModel):
    namespace: str
    name: str
    messageId: str  # noqa: N815
    correlationToken: str | None = None  # noqa: N815
    payloadVersion: str  # noqa: N815
    instance: str | None = None  # present on Alexa.RangeController directives


class AlexaDirective(BaseModel):
    header: DirectiveHeader
    endpoint: DirectiveEndpoint | None = None  # absent on Discover directive
    payload: dict = {}


class AlexaDirectiveRequest(BaseModel):
    directive: AlexaDirective
