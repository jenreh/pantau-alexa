"""Command: turn off a device by resolving its adapter via device.adapter."""

from __future__ import annotations

import logging

from tiberio.commands._base import DeviceCommand
from tiberio.ports.power_port import PowerablePort

log = logging.getLogger(__name__)


class TurnOffCommand(DeviceCommand):
    async def execute(self, endpoint_id: str) -> None:
        device, adapter = self._find_and_resolve(endpoint_id, PowerablePort)  # type: ignore[type-abstract]
        log.debug("TurnOff: endpoint=%s adapter=%s", endpoint_id, device.adapter)
        await adapter.turn_off(device)
