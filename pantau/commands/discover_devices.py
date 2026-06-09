"""Use-case: return all configured devices for Alexa discovery."""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict

from pantau.ports.device_registry_port import DeviceRegistryPort

log = logging.getLogger(__name__)

CapabilityKind = Literal["power", "speaker", "range", "thermostat"]


class DiscoveredDevice(BaseModel):
    """Minimal device descriptor used by Phase 3 to build Alexa Discovery responses."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    capability: CapabilityKind


class DiscoverDevicesCommand:
    def __init__(self, registry: DeviceRegistryPort) -> None:
        self._registry = registry

    async def execute(self) -> list[DiscoveredDevice]:
        registry = self._registry.get_registry()

        channels = [
            DiscoveredDevice(id=ch.id, name=ch.name, capability="power")
            for ch in registry.tv.channels
        ]
        audio = [
            DiscoveredDevice(
                id=registry.tv.audio.id,
                name=registry.tv.audio.name,
                capability="speaker",
            )
        ]
        blinds = [
            DiscoveredDevice(id=b.id, name=b.name, capability="range")
            for b in registry.blinds
        ]
        thermostats = [
            DiscoveredDevice(id=t.id, name=t.name, capability="thermostat")
            for t in registry.thermostats
        ]

        devices = channels + audio + blinds + thermostats
        log.info("DiscoverDevices: %d devices found", len(devices))
        return devices
