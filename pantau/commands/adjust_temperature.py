"""Command: adjust thermostat target temperature by a relative delta."""

from __future__ import annotations

import logging

from pantau.commands._base import DeviceCommand
from pantau.commands.set_temperature import SetTemperatureCommand
from pantau.domain.errors import DeviceCapabilityError
from pantau.domain.models import Thermostat
from pantau.ports.capability_resolver_port import CapabilityResolverPort
from pantau.ports.device_registry_port import DeviceRegistryPort
from pantau.ports.temperature_port import TemperatureControllablePort

log = logging.getLogger(__name__)


class AdjustTemperatureCommand(DeviceCommand):
    """Reads the current target setpoint, applies a delta, delegates to set."""

    def __init__(
        self,
        registry: DeviceRegistryPort,
        resolver: CapabilityResolverPort,
        set_temperature: SetTemperatureCommand,
    ) -> None:
        super().__init__(registry, resolver)
        self._set_temperature = set_temperature

    async def execute(self, endpoint_id: str, delta_celsius: float) -> float:
        """Adjust the target by *delta_celsius*; returns the applied setpoint."""
        device = self._find_device(endpoint_id)
        if not isinstance(device, Thermostat):
            raise DeviceCapabilityError(endpoint_id, "TemperatureControllable")
        adapter = self._resolver.resolve(device, TemperatureControllablePort)  # type: ignore[type-abstract]
        current = await adapter.get_temperature(device)
        log.debug(
            "AdjustTemperature: endpoint=%s current=%.1f delta=%.1f",
            endpoint_id,
            current,
            delta_celsius,
        )
        return await self._set_temperature.execute(
            endpoint_id, celsius=current + delta_celsius
        )
