"""Mock TV adapter — logs operations, records calls, no real hardware connection."""

from __future__ import annotations

import logging

from tiberio.domain.models import ADAPTER_HARMONY, Activity, Device, HubDevice
from tiberio.ports.listable_port import BackendListResult

log = logging.getLogger(__name__)


class MockTvAdapter:
    """Stub implementation of PowerablePort and MuteControllablePort for testing."""

    adapter_name = ADAPTER_HARMONY

    def __init__(self) -> None:
        self.turn_on_calls: list[Device] = []
        self.turn_off_calls: list[Device] = []
        self.set_mute_calls: list[tuple[Device, bool]] = []
        self.set_volume_calls: list[tuple[Device, int]] = []
        self.adjust_volume_calls: list[tuple[Device, int]] = []
        self.toggle_mute_count: int = 0
        self._assumed_mute: bool = False
        self._assumed_volume: int = 50
        self._activities: list[Activity] = []
        self._devices: list[HubDevice] = []

    async def turn_on(self, device: Device) -> None:
        log.info("MockTV: turn_on device=%s", device.id)
        self.turn_on_calls.append(device)

    async def turn_off(self, device: Device) -> None:
        log.info("MockTV: turn_off device=%s", device.id)
        self.turn_off_calls.append(device)

    async def set_mute(self, device: Device, muted: bool) -> None:
        log.info("MockTV: set_mute device=%s muted=%s", device.id, muted)
        self._assumed_mute = muted
        self.set_mute_calls.append((device, muted))

    async def get_mute(self, device: Device) -> bool:
        log.debug("MockTV: get_mute device=%s -> %s", device.id, self._assumed_mute)
        return self._assumed_mute

    async def set_volume(self, device: Device, level: int) -> None:
        log.info("MockTV: set_volume device=%s level=%d", device.id, level)
        self._assumed_volume = max(0, min(100, level))
        self.set_volume_calls.append((device, level))

    async def adjust_volume(self, device: Device, delta: int) -> int:
        self._assumed_volume = max(0, min(100, self._assumed_volume + delta))
        self.adjust_volume_calls.append((device, delta))
        log.info(
            "MockTV: adjust_volume device=%s delta=%d -> %d",
            device.id,
            delta,
            self._assumed_volume,
        )
        return self._assumed_volume

    async def get_volume(self, device: Device) -> int:
        log.debug("MockTV: get_volume device=%s -> %d", device.id, self._assumed_volume)
        return self._assumed_volume

    async def toggle_mute(self) -> None:
        log.info("MockTV: toggle_mute")
        self.toggle_mute_count += 1

    async def list_backend(self) -> BackendListResult:
        log.info(
            "MockTV: list_backend activities=%d devices=%d",
            len(self._activities),
            len(self._devices),
        )
        return BackendListResult(
            status="ok",
            data={
                "activities": [a.model_dump() for a in self._activities],
                "devices": [d.model_dump() for d in self._devices],
            },
        )
