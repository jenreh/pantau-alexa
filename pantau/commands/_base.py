"""Shared base for device commands that need a registry and capability resolver."""

from __future__ import annotations

from typing import TypeVar

from pantau.domain.errors import DeviceNotFoundError
from pantau.domain.models import Device
from pantau.ports.capability_resolver_port import CapabilityResolverPort
from pantau.ports.device_registry_port import DeviceRegistryPort

T = TypeVar("T")


class DeviceCommand:
    def __init__(
        self, registry: DeviceRegistryPort, resolver: CapabilityResolverPort
    ) -> None:
        self._registry = registry
        self._resolver = resolver

    def _find_device(self, endpoint_id: str) -> Device:
        """Return the configured device or raise DeviceNotFoundError."""
        device = self._registry.find_device(endpoint_id)
        if device is None:
            raise DeviceNotFoundError(endpoint_id)
        return device

    def _find_and_resolve(
        self, endpoint_id: str, capability: type[T]
    ) -> tuple[Device, T]:
        """Find the device and resolve the adapter implementing *capability*."""
        device = self._find_device(endpoint_id)
        return device, self._resolver.resolve(device, capability)
