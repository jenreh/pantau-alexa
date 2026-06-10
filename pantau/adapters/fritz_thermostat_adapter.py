"""Real thermostat adapter — wraps fritzctl-py (AVM clients) with a persistent session."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from fritzctl.avm.clients import AVMClientAbstract, get_avm_client

from pantau.domain.errors import (
    DeviceCapabilityError,
    DeviceNotFoundError,
    DeviceUnavailableError,
)
from pantau.domain.models import ADAPTER_FRITZ, Device, LiveThermostat, Thermostat
from pantau.ports.listable_port import BackendListResult

if TYPE_CHECKING:
    from fritzctl.domain.models import Thermostat as FritzThermostat

log = logging.getLogger(__name__)


def _as_thermostat(device: Device) -> Thermostat:
    """Reject non-thermostat devices instead of casting blindly."""
    if not isinstance(device, Thermostat):
        raise DeviceCapabilityError(device.id, "TemperatureControllable")
    return device


class FritzThermostatAdapter:
    """Implements TemperatureControllablePort and ListablePort via FRITZ!Box.

    Holds a persistent httpx session and AVM client. Call start()/stop() from
    the FastAPI lifespan to initialise/close the session once per server lifetime.

    In tests, inject a pre-built fake client via the ``client`` parameter; that
    skips httpx setup so start()/stop() are no-ops.
    """

    adapter_name = ADAPTER_FRITZ

    def __init__(self, *, client: AVMClientAbstract | None = None) -> None:
        self._injected = client
        self._http: httpx.AsyncClient | None = None
        self._client: AVMClientAbstract | None = client
        self._ain_cache: dict[str, str] = {}  # external_id → AIN

    async def start(self) -> None:
        """Open the httpx session and auto-detect the AVM API. Call once on startup."""
        if self._injected is None:
            self._http = httpx.AsyncClient()
            self._client = await get_avm_client(self._http)
        log.info("FritzThermostat: client initialised")

    async def stop(self) -> None:
        """Close the httpx session. Call once on server shutdown."""
        if self._injected is None and self._http is not None:
            await self._http.aclose()
            self._http = None
            self._client = None
        self._ain_cache.clear()
        log.info("FritzThermostat: client closed")

    # ------------------------------------------------------------------
    # TemperatureControllablePort
    # ------------------------------------------------------------------

    async def set_temperature(self, device: Device, celsius: float) -> None:
        """Set the target temperature for the given device."""
        thermostat = _as_thermostat(device)
        await self._set_temperature_impl(thermostat.external_id, celsius)

    async def get_temperature(self, device: Device) -> float:
        """Return the current target temperature for the given device."""
        thermostat = _as_thermostat(device)
        return await self._get_temperature_impl(thermostat.external_id)

    # ------------------------------------------------------------------
    # ListablePort
    # ------------------------------------------------------------------

    async def list_backend(self) -> BackendListResult:
        """Return all FRITZ!Box smart-home thermostats with live state."""
        try:
            devices = await self._list_devices()
            return BackendListResult(
                status="ok",
                data={"devices": [d.model_dump() for d in devices]},
            )
        except DeviceUnavailableError as exc:
            log.warning("FritzThermostat: list_backend unavailable: %s", exc)
            return BackendListResult(status="unavailable", error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> AVMClientAbstract:
        if self._client is None:
            raise RuntimeError(
                "FritzThermostatAdapter is not started; call start() first"
            )
        return self._client

    async def _set_temperature_impl(self, external_id: str, celsius: float) -> None:
        try:
            client = self._get_client()
            ain = await self._resolve_ain(client, external_id)
            await client.set_temperature(ain, celsius)
            log.info(
                "FritzThermostat: set_temperature name=%s ain=%s celsius=%.1f",
                external_id,
                ain,
                celsius,
            )
        except DeviceNotFoundError:
            raise
        except (httpx.HTTPError, TimeoutError, PermissionError) as exc:
            # The cached AIN may be stale (device re-paired/renamed) — drop it
            # so the next attempt re-resolves instead of failing forever.
            self._ain_cache.pop(external_id, None)
            raise DeviceUnavailableError(str(exc)) from exc

    async def _get_temperature_impl(self, external_id: str) -> float:
        try:
            client = self._get_client()
            device = await self._resolve(client, external_id)
            log.debug(
                "FritzThermostat: get_temperature name=%s ain=%s -> %.1f",
                external_id,
                device.id,
                device.target_temp,
            )
            return device.target_temp
        except DeviceNotFoundError:
            raise
        except (httpx.HTTPError, TimeoutError, PermissionError) as exc:
            raise DeviceUnavailableError(str(exc)) from exc

    async def _list_devices(self) -> list[LiveThermostat]:
        try:
            client = self._get_client()
            raw = await client.list_devices()
            log.debug("FritzThermostat: list_devices count=%d", len(raw))
            return [
                LiveThermostat(
                    id=d.id,
                    name=d.name,
                    adapter=ADAPTER_FRITZ,
                    online=d.online,
                    current_temp=d.current_temp,
                    target_temp=d.target_temp,
                    battery_level=d.battery.level if d.battery else None,
                    battery_low=d.battery.low if d.battery else False,
                )
                for d in raw
            ]
        except (httpx.HTTPError, TimeoutError, PermissionError) as exc:
            raise DeviceUnavailableError(str(exc)) from exc

    async def _resolve(
        self, client: AVMClientAbstract, external_id: str
    ) -> FritzThermostat:
        devices = await client.list_devices()
        self._ain_cache.update({d.name: d.id for d in devices})
        device = next((d for d in devices if d.name == external_id), None)
        if device is None:
            raise DeviceNotFoundError(external_id)
        return device

    async def _resolve_ain(self, client: AVMClientAbstract, external_id: str) -> str:
        """Return the AIN for *external_id*, fetching once and caching."""
        if external_id not in self._ain_cache:
            devices = await client.list_devices()
            self._ain_cache.update({d.name: d.id for d in devices})
        if external_id not in self._ain_cache:
            self._ain_cache.clear()
            raise DeviceNotFoundError(external_id)
        return self._ain_cache[external_id]
