"""Port: device registry — lookup of configured devices."""

from __future__ import annotations

from typing import Protocol

from pantau.domain.models import Device, DeviceRegistry


class DeviceRegistryPort(Protocol):
    """Provides access to the configured device list."""

    def get_registry(self) -> DeviceRegistry:
        """Return the full device registry."""
        ...

    def find_device(self, endpoint_id: str) -> Device | None:
        """Find any configured device by its endpoint ID."""
        ...
