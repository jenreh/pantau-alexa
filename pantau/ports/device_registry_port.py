"""Port: device registry — lookup of configured devices."""

from __future__ import annotations

from typing import Protocol

from pantau.domain.models import (
    DeviceRegistry,
    Thermostat,
    TvChannel,
    WindowBlind,
)


class DeviceRegistryPort(Protocol):
    """Provides access to the configured device list."""

    def get_registry(self) -> DeviceRegistry:
        """Return the full device registry."""
        ...

    def find_channel(self, endpoint_id: str) -> TvChannel | None:
        """Find a TV channel by its endpoint ID."""
        ...

    def find_blind(self, endpoint_id: str) -> WindowBlind | None:
        """Find a window blind by its endpoint ID."""
        ...

    def find_thermostat(self, endpoint_id: str) -> Thermostat | None:
        """Find a thermostat by its endpoint ID."""
        ...
