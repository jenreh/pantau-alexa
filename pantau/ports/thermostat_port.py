"""Port: thermostat control."""

from __future__ import annotations

from typing import Protocol

from pantau.domain.models import LiveThermostat


class ThermostatPort(Protocol):
    """Abstracts the FRITZ!Box thermostat library (fritzctl)."""

    async def set_temperature(self, external_id: str, celsius: float) -> None:
        """Set the target temperature of a thermostat."""
        ...

    async def get_temperature(self, external_id: str) -> float:
        """Return the current target temperature in Celsius."""
        ...

    async def list_devices(self) -> list[LiveThermostat]:
        """Return all FRITZ!Box smart-home thermostats with live state."""
        ...
