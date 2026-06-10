"""Command: read the current mute and volume state of a speaker device."""

from __future__ import annotations

import logging

from pantau.commands._base import DeviceCommand
from pantau.ports.mute_port import MuteControllablePort
from pantau.ports.volume_port import VolumeControllablePort

log = logging.getLogger(__name__)


class GetSpeakerStateCommand(DeviceCommand):
    async def execute(self, endpoint_id: str) -> tuple[bool, int]:
        """Return (muted, volume) for the given endpoint."""
        device = self._find_device(endpoint_id)
        mute_adapter = self._resolver.resolve(device, MuteControllablePort)  # type: ignore[type-abstract]
        volume_adapter = self._resolver.resolve(device, VolumeControllablePort)  # type: ignore[type-abstract]
        muted = await mute_adapter.get_mute(device)
        volume = await volume_adapter.get_volume(device)
        log.debug(
            "GetSpeakerState: endpoint=%s muted=%s volume=%d",
            endpoint_id,
            muted,
            volume,
        )
        return muted, volume
