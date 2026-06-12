"""Command: list live devices from all connected backends."""

from __future__ import annotations

import asyncio
import logging

from tiberio.ports.capability_resolver_port import CapabilityResolverPort
from tiberio.ports.listable_port import ListablePort

log = logging.getLogger(__name__)


class ListConnectedDevicesCommand:
    """Query all registered ListablePort adapters for live connected devices.

    Each backend is queried independently via list_backend().  If one is offline
    its result carries ``status="unavailable"`` and an error message; the other
    backends are unaffected.

    Adding a new adapter (e.g. Hue, Sonos) only requires implementing ListablePort
    and registering it — no changes here.
    """

    def __init__(self, resolver: CapabilityResolverPort) -> None:
        self._resolver = resolver

    async def execute(self) -> dict[str, dict]:
        """Return a mapping of adapter_name → backend-specific serialisable data."""
        adapters = self._resolver.all_implementing(ListablePort)  # type: ignore[type-abstract]
        backends = await asyncio.gather(
            *[a.list_backend() for a in adapters], return_exceptions=True
        )
        result: dict[str, dict] = {}
        for adapter, backend in zip(adapters, backends, strict=True):
            if isinstance(backend, BaseException):
                # One misbehaving backend must not take down the whole listing.
                log.error(
                    "ListConnectedDevices: %s raised: %s",
                    adapter.adapter_name,
                    backend,
                )
                result[adapter.adapter_name] = {
                    "status": "unavailable",
                    "error": "unexpected backend error",
                }
                continue
            data: dict = {"status": backend.status}
            if backend.error:
                data["error"] = backend.error
            else:
                data.update(backend.data)
            result[adapter.adapter_name] = data
            log.info(
                "ListConnectedDevices: %s status=%s",
                adapter.adapter_name,
                backend.status,
            )
        return result
