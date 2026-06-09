"""Use-case: adjust the position of a roller blind by a relative delta."""

from __future__ import annotations

import logging

from pantau.domain.errors import DeviceNotFoundError
from pantau.ports.blind_port import BlindPort
from pantau.ports.device_registry_port import DeviceRegistryPort

log = logging.getLogger(__name__)


class AdjustBlindPositionCommand:
    def __init__(self, registry: DeviceRegistryPort, blind: BlindPort) -> None:
        self._registry = registry
        self._blind = blind

    async def execute(self, endpoint_id: str, delta: int) -> int:
        """Apply *delta* to the current blind position and return the new position (0–100)."""
        device = self._registry.find_blind(endpoint_id)
        if device is None:
            raise DeviceNotFoundError(endpoint_id)

        homekit_current = await self._blind.get_position(device.external_id)
        alexa_current = (100 - homekit_current) if device.invert else homekit_current
        new_alexa = max(0, min(100, alexa_current + delta))
        homekit_new = (100 - new_alexa) if device.invert else new_alexa

        log.info(
            "AdjustBlindPosition: endpoint=%s entity=%s delta=%d %d%%->%d%%",
            endpoint_id,
            device.external_id,
            delta,
            alexa_current,
            new_alexa,
        )
        await self._blind.set_position(device.external_id, homekit_new)
        return new_alexa
