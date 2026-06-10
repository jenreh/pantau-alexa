"""Real blind adapter — wraps homekit-py (HomeKitClient) with a persistent daemon."""

from __future__ import annotations

import logging

from homekit.client import HomeKitClient
from homekit.exceptions import AccessoryNotFoundError, HomeKitError

from pantau.domain.errors import DeviceCapabilityError, DeviceUnavailableError
from pantau.domain.models import ADAPTER_HOMEKIT, Device, HomeDevice, WindowBlind
from pantau.ports.listable_port import BackendListResult

log = logging.getLogger(__name__)


def _as_blind(device: Device) -> WindowBlind:
    """Reject non-blind devices instead of casting blindly."""
    if not isinstance(device, WindowBlind):
        raise DeviceCapabilityError(device.id, "RangeControllable")
    return device


class HomeKitBlindAdapter:
    """Implements RangeControllablePort and ListablePort via HomeKit accessories.

    Holds a single persistent HomeKitClient whose daemon is started once on
    server startup and stopped on server shutdown (call start()/stop() from the
    FastAPI lifespan). This avoids per-call BLE/IP connection overhead.

    In tests, inject a pre-built fake client via the ``client`` parameter.
    """

    adapter_name = ADAPTER_HOMEKIT

    def __init__(self, *, client: HomeKitClient | None = None) -> None:
        self._client = client or HomeKitClient()

    async def start(self) -> None:
        """Start the HomeKit daemon. Call once when the server starts."""
        await self._client.start()
        log.info("HomeKitBlind: daemon started")

    async def stop(self) -> None:
        """Stop the HomeKit daemon. Call once when the server shuts down."""
        await self._client.stop()
        log.info("HomeKitBlind: daemon stopped")

    # ------------------------------------------------------------------
    # RangeControllablePort
    # ------------------------------------------------------------------

    async def set_range(self, device: Device, value: int) -> None:
        """Set blind position (0=closed, 100=open). Handles device.invert."""
        blind = _as_blind(device)
        actual = (100 - value) if blind.invert else value
        await self._set_position(blind.external_id, actual)
        log.info(
            "HomeKitBlind: set_range device=%s value=%d actual=%d",
            blind.id,
            value,
            actual,
        )

    async def adjust_range(self, device: Device, delta: int) -> int:
        """Adjust position by delta, returning the new Alexa-space position."""
        blind = _as_blind(device)
        homekit_pos = await self._get_position(blind.external_id)
        alexa_pos = (100 - homekit_pos) if blind.invert else homekit_pos
        new_alexa = max(0, min(100, alexa_pos + delta))
        homekit_new = (100 - new_alexa) if blind.invert else new_alexa
        await self._set_position(blind.external_id, homekit_new)
        log.info(
            "HomeKitBlind: adjust_range device=%s delta=%d -> %d",
            blind.id,
            delta,
            new_alexa,
        )
        return new_alexa

    async def get_range(self, device: Device) -> int:
        """Return the current Alexa-space position (handles device.invert)."""
        blind = _as_blind(device)
        homekit_pos = await self._get_position(blind.external_id)
        return (100 - homekit_pos) if blind.invert else homekit_pos

    # ------------------------------------------------------------------
    # ListablePort
    # ------------------------------------------------------------------

    async def list_backend(self) -> BackendListResult:
        """Return all paired HomeKit devices."""
        try:
            devices = await self._list_devices()
            return BackendListResult(
                status="ok",
                data={"devices": [d.model_dump() for d in devices]},
            )
        except DeviceUnavailableError as exc:
            log.warning("HomeKitBlind: list_backend unavailable: %s", exc)
            return BackendListResult(status="unavailable", error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _set_position(self, external_id: str, percent: int) -> None:
        """Set the blind position (0 = closed, 100 = open)."""
        try:
            await self._client.set_position(external_id, percent)
            log.info(
                "HomeKitBlind: set_position entity=%s percent=%d",
                external_id,
                percent,
            )
        except AccessoryNotFoundError as exc:
            raise DeviceUnavailableError(str(exc)) from exc
        except HomeKitError as exc:
            raise DeviceUnavailableError(str(exc)) from exc

    async def _get_position(self, external_id: str) -> int:
        """Return the current position percentage of a blind."""
        try:
            state = await self._client.get_state(external_id)
            position = int(float(state.state))
            log.debug(
                "HomeKitBlind: get_position entity=%s -> %d",
                external_id,
                position,
            )
            return position
        except (ValueError, TypeError) as exc:
            raise DeviceUnavailableError(
                f"Unexpected state value for {external_id!r}: {exc}"
            ) from exc
        except AccessoryNotFoundError as exc:
            raise DeviceUnavailableError(str(exc)) from exc
        except HomeKitError as exc:
            raise DeviceUnavailableError(str(exc)) from exc

    async def _list_devices(self) -> list[HomeDevice]:
        """Return all paired smart-home devices."""
        try:
            entities = await self._client.list_entities()
            log.debug("HomeKitBlind: list_devices count=%d", len(entities))
            return [
                HomeDevice(
                    id=e.entity_id,
                    name=e.name,
                    adapter=ADAPTER_HOMEKIT,
                    domain=e.domain,
                    room=e.room,
                )
                for e in entities
            ]
        except HomeKitError as exc:
            raise DeviceUnavailableError(str(exc)) from exc
