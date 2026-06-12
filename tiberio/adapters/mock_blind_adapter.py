"""Mock blind adapter — logs operations, records calls, no real HomeKit connection."""

from __future__ import annotations

import logging

from tiberio.domain.models import ADAPTER_HOMEKIT, Device, HomeDevice
from tiberio.ports.listable_port import BackendListResult

log = logging.getLogger(__name__)


class MockBlindAdapter:
    """Stub implementation of RangeControllablePort and ListablePort for testing."""

    adapter_name = ADAPTER_HOMEKIT

    def __init__(self) -> None:
        self._positions: dict[str, int] = {}
        self.set_range_calls: list[tuple[Device, int]] = []
        self.adjust_range_calls: list[tuple[Device, int]] = []
        self._devices: list[HomeDevice] = []

    async def set_range(self, device: Device, value: int) -> None:
        log.info("MockBlind: set_range device=%s value=%d", device.id, value)
        self._positions[device.id] = value
        self.set_range_calls.append((device, value))

    async def adjust_range(self, device: Device, delta: int) -> int:
        current = self._positions.get(device.id, 0)
        new_pos = max(0, min(100, current + delta))
        self._positions[device.id] = new_pos
        self.adjust_range_calls.append((device, delta))
        log.info(
            "MockBlind: adjust_range device=%s delta=%d -> %d",
            device.id,
            delta,
            new_pos,
        )
        return new_pos

    async def get_range(self, device: Device) -> int:
        position = self._positions.get(device.id, 0)
        log.info("MockBlind: get_range device=%s -> %d", device.id, position)
        return position

    async def list_backend(self) -> BackendListResult:
        log.info("MockBlind: list_backend devices=%d", len(self._devices))
        return BackendListResult(
            status="ok",
            data={"devices": [d.model_dump() for d in self._devices]},
        )
