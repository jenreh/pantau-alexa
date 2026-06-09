"""Mock thermostat adapter — logs operations, records calls, no real FRITZ!Box connection."""

from __future__ import annotations

import logging

from pantau.domain.models import LiveThermostat

log = logging.getLogger(__name__)


class MockThermostatAdapter:
    """Stub implementation of ThermostatPort for development and testing."""

    def __init__(self) -> None:
        self._temperatures: dict[str, float] = {}
        self.set_temperature_calls: list[tuple[str, float]] = []
        self._devices: list[LiveThermostat] = []

    async def set_temperature(self, external_id: str, celsius: float) -> None:
        log.info(
            "MockThermostat: set_temperature name=%s celsius=%.1f", external_id, celsius
        )
        self._temperatures[external_id] = celsius
        self.set_temperature_calls.append((external_id, celsius))

    async def get_temperature(self, external_id: str) -> float:
        temp = self._temperatures.get(external_id, 20.0)
        log.info("MockThermostat: get_temperature name=%s -> %.1f", external_id, temp)
        return temp

    async def list_devices(self) -> list[LiveThermostat]:
        log.info("MockThermostat: list_devices count=%d", len(self._devices))
        return list(self._devices)
