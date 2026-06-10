"""Command: set absolute volume on a device."""

from __future__ import annotations

import logging

from pantau.commands._base import DeviceCommand
from pantau.domain.values import Percentage
from pantau.ports.volume_port import VolumeControllablePort

log = logging.getLogger(__name__)


class SetVolumeCommand(DeviceCommand):
    async def execute(self, endpoint_id: str, level: int) -> None:
        device, adapter = self._find_and_resolve(endpoint_id, VolumeControllablePort)  # type: ignore[type-abstract]
        Percentage(value=level)  # validates 0–100
        log.debug(
            "SetVolume: endpoint=%s level=%d adapter=%s",
            endpoint_id,
            level,
            device.adapter,
        )
        await adapter.set_volume(device, level)
