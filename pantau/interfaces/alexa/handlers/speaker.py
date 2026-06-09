"""Alexa.Speaker handler — SetMute for the TV audio endpoint."""

from __future__ import annotations

import logging

from pantau.commands.tv.set_tv_mute import SetTvMuteCommand
from pantau.domain.errors import DeviceNotFoundError, DeviceUnavailableError
from pantau.interfaces.alexa.models import AlexaDirectiveRequest
from pantau.interfaces.alexa.response_builder import (
    build_error_response,
    build_property,
    build_response,
)

log = logging.getLogger(__name__)


class SpeakerHandler:
    def __init__(self, set_mute: SetTvMuteCommand) -> None:
        self._set_mute = set_mute

    async def handle(self, req: AlexaDirectiveRequest) -> dict:
        header = req.directive.header
        endpoint = req.directive.endpoint
        endpoint_id = endpoint.endpointId if endpoint else ""
        correlation_token = header.correlationToken
        bearer_token = endpoint.scope.token if endpoint and endpoint.scope else None

        mute: bool = bool(req.directive.payload.get("mute", False))

        try:
            await self._set_mute.execute(endpoint_id, mute=mute)
            properties = [
                build_property("Alexa.Speaker", "muted", mute),
                # volume is not tracked by this server; report a static assumed value
                build_property("Alexa.Speaker", "volume", 50, uncertainty_ms=0),
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
            log.exception(
                "SpeakerHandler: unexpected error for endpoint=%s", endpoint_id
            )
            return build_error_response(
                correlation_token, endpoint_id, "INTERNAL_ERROR", str(exc)
            )
