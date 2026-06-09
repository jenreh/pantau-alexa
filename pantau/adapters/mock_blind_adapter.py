"""Mock blind adapter — logs operations, records calls, no real HomeKit connection."""

from __future__ import annotations

import logging

from pantau.domain.models import HomeDevice

log = logging.getLogger(__name__)


class MockBlindAdapter:
    """Stub implementation of BlindPort for development and testing."""

    def __init__(self) -> None:
        self._positions: dict[str, int] = {}
        self.set_position_calls: list[tuple[str, int]] = []
        self._devices: list[HomeDevice] = []

    async def set_position(self, external_id: str, percent: int) -> None:
        log.info("MockBlind: set_position entity=%s percent=%d", external_id, percent)
        self._positions[external_id] = percent
        self.set_position_calls.append((external_id, percent))

    async def get_position(self, external_id: str) -> int:
        position = self._positions.get(external_id, 0)
        log.info("MockBlind: get_position entity=%s -> %d", external_id, position)
        return position

    async def list_devices(self) -> list[HomeDevice]:
        log.info("MockBlind: list_devices count=%d", len(self._devices))
        return list(self._devices)
