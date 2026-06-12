"""Command: adjust volume by a relative delta on a device."""

from __future__ import annotations

import logging

from tiberio.commands._base import DeviceCommand
from tiberio.ports.volume_port import VolumeControllablePort

log = logging.getLogger(__name__)


class AdjustVolumeCommand(DeviceCommand):
    async def execute(self, endpoint_id: str, delta: int) -> int:
        """Adjust volume by delta steps; returns the new assumed level."""
        device, adapter = self._find_and_resolve(endpoint_id, VolumeControllablePort)  # type: ignore[type-abstract]
        log.debug(
            "AdjustVolume: endpoint=%s delta=%d adapter=%s",
            endpoint_id,
            delta,
            device.adapter,
        )
        return await adapter.adjust_volume(device, delta)
