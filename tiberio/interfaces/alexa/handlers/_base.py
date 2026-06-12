"""Shared base for Alexa capability handlers.

Centralises directive-context extraction, payload validation helpers, and
the mapping of domain errors to Alexa error types so each handler only
implements its capability logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from tiberio.domain.errors import (
    DeviceCapabilityError,
    DeviceNotFoundError,
    DeviceUnavailableError,
)
from tiberio.interfaces.alexa.models import AlexaDirectiveRequest
from tiberio.interfaces.alexa.response_builder import (
    build_error_response,
    build_response,
)

log = logging.getLogger(__name__)


class InvalidPayloadError(Exception):
    """A required payload field is missing or has the wrong type.

    Maps to Alexa INVALID_VALUE in the directive handler.
    """


@dataclass(frozen=True)
class DirectiveContext:
    """The parts of a directive every handler needs."""

    name: str
    endpoint_id: str
    correlation_token: str | None
    bearer_token: str | None
    payload: dict


def require_field(payload: dict, field: str) -> object:
    """Return payload[field] or raise InvalidPayloadError when absent."""
    if field not in payload:
        raise InvalidPayloadError(f"Missing required payload field: {field!r}")
    return payload[field]


def require_int(payload: dict, field: str) -> int:
    """Return payload[field] as int; raise InvalidPayloadError if absent/not numeric."""
    value = require_field(payload, field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidPayloadError(f"Payload field {field!r} must be a number")
    return int(value)


class AlexaHandler:
    """Template method: subclasses implement _execute() returning properties."""

    async def handle(self, req: AlexaDirectiveRequest) -> dict:
        header = req.directive.header
        endpoint = req.directive.endpoint
        ctx = DirectiveContext(
            name=header.name,
            endpoint_id=endpoint.endpointId if endpoint else "",
            correlation_token=header.correlationToken,
            bearer_token=endpoint.scope.token if endpoint and endpoint.scope else None,
            payload=req.directive.payload,
        )

        try:
            properties = await self._execute(ctx)
            return self._build_success(ctx, properties)
        except InvalidPayloadError as exc:
            return self._error(ctx, "INVALID_VALUE", str(exc))
        except ValueError as exc:
            return self._error(ctx, "VALUE_OUT_OF_RANGE", str(exc))
        except DeviceCapabilityError as exc:
            return self._error(ctx, "INVALID_VALUE", str(exc))
        except DeviceNotFoundError as exc:
            return self._error(ctx, "NO_SUCH_ENDPOINT", str(exc))
        except DeviceUnavailableError as exc:
            return self._error(ctx, "ENDPOINT_UNREACHABLE", str(exc))
        except Exception:
            log.exception(
                "%s: unexpected error for endpoint=%s",
                type(self).__name__,
                ctx.endpoint_id,
            )
            return self._error(
                ctx, "INTERNAL_ERROR", "Internal error while handling the directive"
            )

    async def _execute(self, ctx: DirectiveContext) -> list[dict]:
        """Run the directive; returns the Alexa context properties."""
        raise NotImplementedError

    def _build_success(self, ctx: DirectiveContext, properties: list[dict]) -> dict:
        """Wrap the properties in an Alexa.Response. Override for StateReport."""
        return build_response(
            ctx.correlation_token, ctx.endpoint_id, ctx.bearer_token, properties
        )

    @staticmethod
    def _error(ctx: DirectiveContext, error_type: str, message: str) -> dict:
        return build_error_response(
            ctx.correlation_token, ctx.endpoint_id, error_type, message
        )
