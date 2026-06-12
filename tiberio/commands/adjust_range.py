"""Command: adjust range value by a delta (e.g. blind position delta)."""

from __future__ import annotations

import logging

from tiberio.commands._base import DeviceCommand
from tiberio.ports.range_port import RangeControllablePort

log = logging.getLogger(__name__)


class AdjustRangeCommand(DeviceCommand):
    async def execute(self, endpoint_id: str, delta: int) -> int:
        """Adjust the range by delta; returns the new position."""
        device, adapter = self._find_and_resolve(endpoint_id, RangeControllablePort)  # type: ignore[type-abstract]
        log.debug(
            "AdjustRange: endpoint=%s delta=%d adapter=%s",
            endpoint_id,
            delta,
            device.adapter,
        )
        return await adapter.adjust_range(device, delta)
