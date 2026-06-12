"""Builds Alexa Smart Home response objects.

All shapes are taken verbatim from the Alexa Smart Home API v3 docs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _new_message_id() -> str:
    return str(uuid.uuid4())


def build_property(
    namespace: str,
    name: str,
    value: object,
    instance: str | None = None,
    uncertainty_ms: int = 500,
) -> dict:
    prop: dict = {
        "namespace": namespace,
        "name": name,
        "value": value,
        "timeOfSample": _now_iso(),
        "uncertaintyInMilliseconds": uncertainty_ms,
    }
    if instance is not None:
        prop["instance"] = instance
    return prop


def build_response(
    correlation_token: str | None,
    endpoint_id: str,
    bearer_token: str | None,
    properties: list[dict],
) -> dict:
    endpoint: dict = {"endpointId": endpoint_id}
    if bearer_token:
        endpoint["scope"] = {"type": "BearerToken", "token": bearer_token}

    header: dict = {
        "namespace": "Alexa",
        "name": "Response",
        "messageId": _new_message_id(),
        "payloadVersion": "3",
    }
    if correlation_token is not None:
        header["correlationToken"] = correlation_token

    return {
        "event": {
            "header": header,
            "endpoint": endpoint,
            "payload": {},
        },
        "context": {"properties": properties},
    }


def build_discovery_response(endpoints: list[dict]) -> dict:
    return {
        "event": {
            "header": {
                "namespace": "Alexa.Discovery",
                "name": "Discover.Response",
                "messageId": _new_message_id(),
                "payloadVersion": "3",
            },
            "payload": {"endpoints": endpoints},
        },
    }


def build_error_response(
    correlation_token: str | None,
    endpoint_id: str | None,
    error_type: str,
    message: str,
) -> dict:
    header: dict = {
        "namespace": "Alexa",
        "name": "ErrorResponse",
        "messageId": _new_message_id(),
        "payloadVersion": "3",
    }
    if correlation_token is not None:
        header["correlationToken"] = correlation_token

    event: dict = {
        "header": header,
        "payload": {"type": error_type, "message": message},
    }
    if endpoint_id is not None:
        event["endpoint"] = {"endpointId": endpoint_id}

    return {"event": event}
