"""Alexa.ThermostatController handler — SetTargetTemperature."""

from __future__ import annotations

import logging

from pantau.commands.heating.set_thermostat_temperature import (
    SetThermostatTemperatureCommand,
)
from pantau.domain.errors import DeviceNotFoundError, DeviceUnavailableError
from pantau.interfaces.alexa.models import AlexaDirectiveRequest
from pantau.interfaces.alexa.response_builder import (
    build_error_response,
    build_property,
    build_response,
)

log = logging.getLogger(__name__)

_FAHRENHEIT_TO_CELSIUS = lambda f: (f - 32) * 5 / 9  # noqa: E731


def _to_celsius(value: float, scale: str) -> float:
    if scale == "CELSIUS":
        return value
    if scale == "FAHRENHEIT":
        return _FAHRENHEIT_TO_CELSIUS(value)
    raise ValueError(f"Unsupported temperature scale: {scale!r}")


class ThermostatHandler:
    def __init__(self, set_temperature: SetThermostatTemperatureCommand) -> None:
        self._set_temperature = set_temperature

    async def handle(self, req: AlexaDirectiveRequest) -> dict:
        header = req.directive.header
        endpoint = req.directive.endpoint
        endpoint_id = endpoint.endpointId if endpoint else ""
        correlation_token = header.correlationToken
        bearer_token = endpoint.scope.token if endpoint and endpoint.scope else None

        try:
            target = req.directive.payload.get("targetSetpoint", {})
            raw_value: float = float(target.get("value", 0.0))
            scale: str = target.get("scale", "CELSIUS")
            celsius = _to_celsius(raw_value, scale)

            await self._set_temperature.execute(endpoint_id, celsius=celsius)
            properties = [
                build_property(
                    "Alexa.ThermostatController",
                    "targetSetpoint",
                    {"value": celsius, "scale": "CELSIUS"},
                ),
            ]
            return build_response(
                correlation_token, endpoint_id, bearer_token, properties
            )
        except ValueError as exc:
            return build_error_response(
                correlation_token, endpoint_id, "VALUE_OUT_OF_RANGE", str(exc)
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
                "ThermostatHandler: unexpected error for endpoint=%s", endpoint_id
            )
            return build_error_response(
                correlation_token, endpoint_id, "INTERNAL_ERROR", str(exc)
            )
