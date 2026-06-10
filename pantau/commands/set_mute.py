"""Command: set mute state on a device by resolving its adapter via device.adapter."""

from __future__ import annotations

import logging

from pantau.commands._base import DeviceCommand
from pantau.ports.mute_port import MuteControllablePort

log = logging.getLogger(__name__)


class SetMuteCommand(DeviceCommand):
    async def execute(self, endpoint_id: str, mute: bool) -> None:
        device, adapter = self._find_and_resolve(endpoint_id, MuteControllablePort)  # type: ignore[type-abstract]
        log.debug(
            "SetMute: endpoint=%s mute=%s adapter=%s", endpoint_id, mute, device.adapter
        )
        await adapter.set_mute(device, mute)
