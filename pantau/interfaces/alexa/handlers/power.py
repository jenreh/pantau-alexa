"""Alexa.PowerController handler — TurnOn/TurnOff for channel endpoints."""

from __future__ import annotations

import logging

from pantau.commands.tv.activate_channel import ActivateChannelCommand
from pantau.domain.errors import DeviceNotFoundError, DeviceUnavailableError
from pantau.interfaces.alexa.models import AlexaDirectiveRequest
from pantau.interfaces.alexa.response_builder import (
    build_error_response,
    build_property,
    build_response,
)

log = logging.getLogger(__name__)


class PowerHandler:
    def __init__(self, activate_channel: ActivateChannelCommand) -> None:
        self._activate_channel = activate_channel

    async def handle(self, req: AlexaDirectiveRequest) -> dict:
        header = req.directive.header
        endpoint = req.directive.endpoint
        endpoint_id = endpoint.endpointId if endpoint else ""
        correlation_token = header.correlationToken
        bearer_token = endpoint.scope.token if endpoint and endpoint.scope else None

        try:
            if header.name == "TurnOn":
                await self._activate_channel.execute(endpoint_id)
                power_state = "ON"
            else:
                # TurnOff is a no-op for channel devices (documented in spec)
                log.info("PowerHandler: TurnOff no-op for endpoint=%s", endpoint_id)
                power_state = "OFF"

            properties = [
                build_property("Alexa.PowerController", "powerState", power_state)
            ]
            return build_response(
                correlation_token, endpoint_id, bearer_token, properties
            )
        except DeviceNotFoundError as exc:
            return build_error_response(
                correlation_token, endpoint_id, "NO_SUCH_ENDPOINT", str(exc)
            )
        except DeviceUnavailableError as exc:
            return build_error_response(
                correlation_token, endpoint_id, "ENDPOINT_UNREACHABLE", str(exc)
            )
        except Exception as exc:
            log.exception("PowerHandler: unexpected error for endpoint=%s", endpoint_id)
            return build_error_response(
                correlation_token, endpoint_id, "INTERNAL_ERROR", str(exc)
            )
