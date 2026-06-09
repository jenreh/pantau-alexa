"""Port: device registry — lookup of configured devices."""

from __future__ import annotations

from typing import Protocol

from pantau.domain.models import (
    BlindDevice,
    ChannelDevice,
    DeviceRegistry,
    ThermostatDevice,
)


class DeviceRegistryPort(Protocol):
    """Provides access to the configured device list."""

    def get_registry(self) -> DeviceRegistry:
        """Return the full device registry."""
        ...

    def find_channel(self, endpoint_id: str) -> ChannelDevice | None:
        """Find a channel device by its endpoint ID."""
        ...

    def find_blind(self, endpoint_id: str) -> BlindDevice | None:
        """Find a blind device by its endpoint ID."""
        ...

    def find_thermostat(self, endpoint_id: str) -> ThermostatDevice | None:
        """Find a thermostat device by its endpoint ID."""
        ...
