"""Command: read the current reportable state of a device (for Alexa.ReportState)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from tiberio.commands._base import DeviceCommand
from tiberio.domain.errors import DeviceCapabilityError
from tiberio.domain.models import Thermostat, WindowBlind
from tiberio.ports.range_port import RangeControllablePort
from tiberio.ports.temperature_port import TemperatureControllablePort

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceState:
    """The current state of a device, neutral to any delivery format.

    ``capability`` names which controllable aspect ``value`` describes:
    ``"temperature"`` → degrees Celsius; ``"range"`` → percent (0–100).
    """

    capability: Literal["temperature", "range"]
    value: float


class GetDeviceStateCommand(DeviceCommand):
    async def execute(self, endpoint_id: str) -> DeviceState:
        """Return the current reportable state for the given endpoint."""
        device = self._find_device(endpoint_id)

        if isinstance(device, Thermostat):
            temp_adapter = self._resolver.resolve(device, TemperatureControllablePort)  # type: ignore[type-abstract]
            celsius = await temp_adapter.get_temperature(device)
            log.debug(
                "GetDeviceState: endpoint=%s temperature=%.1f", endpoint_id, celsius
            )
            return DeviceState(capability="temperature", value=celsius)

        if isinstance(device, WindowBlind):
            range_adapter = self._resolver.resolve(device, RangeControllablePort)  # type: ignore[type-abstract]
            percent = await range_adapter.get_range(device)
            log.debug("GetDeviceState: endpoint=%s range=%d", endpoint_id, percent)
            return DeviceState(capability="range", value=percent)

        raise DeviceCapabilityError(endpoint_id, "StateReportable")
