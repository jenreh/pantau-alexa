"""Port: thermostat control."""

from __future__ import annotations

from typing import Protocol


class ThermostatPort(Protocol):
    """Abstracts the FRITZ!Box thermostat library (fritzctl)."""

    async def set_temperature(self, fritz_name: str, celsius: float) -> None:
        """Set the target temperature of a thermostat identified by its FRITZ!Box name."""
        ...

    async def get_temperature(self, fritz_name: str) -> float:
        """Return the current target temperature in Celsius."""
        ...
