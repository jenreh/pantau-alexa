"""Tests for ListConnectedDevicesCommand."""

from __future__ import annotations

from pantau.adapters.mock_blind_adapter import MockBlindAdapter
from pantau.adapters.mock_thermostat_adapter import MockThermostatAdapter
from pantau.adapters.mock_tv_adapter import MockTvAdapter
from pantau.commands.list_connected_devices import ListConnectedDevicesCommand
from pantau.composition import Container
from pantau.domain.models import (
    Activity,
    HomeDevice,
    HubDevice,
    LiveThermostat,
)
from pantau.ports.listable_port import BackendListResult


def _command(
    tv: MockTvAdapter | None = None,
    blind: MockBlindAdapter | None = None,
    thermostat: MockThermostatAdapter | None = None,
) -> ListConnectedDevicesCommand:
    tv = tv or MockTvAdapter()
    blind = blind or MockBlindAdapter()
    thermostat = thermostat or MockThermostatAdapter()
    container = Container()
    container.register(type(tv), tv, adapter_name="harmony")
    container.register(type(blind), blind, adapter_name="homekit")
    container.register(type(thermostat), thermostat, adapter_name="fritz")
    return ListConnectedDevicesCommand(container)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Harmony
# ---------------------------------------------------------------------------


class TestHarmonyResult:
    async def test_returns_activities_and_devices(self) -> None:
        tv = MockTvAdapter()
        tv._activities = [Activity(id="1", name="Watch TV", adapter="harmony")]
        tv._devices = [HubDevice(id="10", name="Samsung TV", adapter="harmony")]

        result = await _command(tv=tv).execute()

        assert result["harmony"]["status"] == "ok"
        assert len(result["harmony"]["activities"]) == 1
        assert result["harmony"]["activities"][0]["name"] == "Watch TV"
        assert len(result["harmony"]["devices"]) == 1
        assert result["harmony"]["devices"][0]["id"] == "10"
        assert "error" not in result["harmony"]

    async def test_unavailable_when_hub_backend_fails(self) -> None:
        class FailingTvAdapter(MockTvAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="hub offline")

        result = await _command(tv=FailingTvAdapter()).execute()

        assert result["harmony"]["status"] == "unavailable"
        assert "hub offline" in result["harmony"]["error"]

    async def test_empty_lists_when_no_devices_configured(self) -> None:
        result = await _command().execute()

        assert result["harmony"]["status"] == "ok"
        assert result["harmony"]["activities"] == []
        assert result["harmony"]["devices"] == []


# ---------------------------------------------------------------------------
# HomeKit
# ---------------------------------------------------------------------------


class TestHomeKitResult:
    async def test_returns_entities(self) -> None:
        blind = MockBlindAdapter()
        blind._devices = [
            HomeDevice(
                id="cover.wohnzimmer",
                name="Wohnzimmer Rollo",
                adapter="homekit",
                domain="cover",
                room="Wohnzimmer",
            )
        ]

        result = await _command(blind=blind).execute()

        assert result["homekit"]["status"] == "ok"
        assert len(result["homekit"]["devices"]) == 1
        assert result["homekit"]["devices"][0]["id"] == "cover.wohnzimmer"

    async def test_unavailable_when_homekit_backend_fails(self) -> None:
        class FailingBlindAdapter(MockBlindAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(
                    status="unavailable", error="daemon not running"
                )

        result = await _command(blind=FailingBlindAdapter()).execute()

        assert result["homekit"]["status"] == "unavailable"
        assert "daemon not running" in result["homekit"]["error"]


# ---------------------------------------------------------------------------
# FRITZ!Box
# ---------------------------------------------------------------------------


class TestFritzResult:
    async def test_returns_devices(self) -> None:
        thermostat = MockThermostatAdapter()
        thermostat._devices = [
            LiveThermostat(
                id="11630 0000001",
                name="Wohnzimmer",
                adapter="fritz",
                online=True,
                current_temp=20.5,
                target_temp=21.0,
                battery_level=80,
                battery_low=False,
            )
        ]

        result = await _command(thermostat=thermostat).execute()

        assert result["fritz"]["status"] == "ok"
        assert len(result["fritz"]["devices"]) == 1
        assert result["fritz"]["devices"][0]["name"] == "Wohnzimmer"

    async def test_unavailable_when_fritz_backend_fails(self) -> None:
        class FailingThermostatAdapter(MockThermostatAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(
                    status="unavailable", error="connection refused"
                )

        result = await _command(thermostat=FailingThermostatAdapter()).execute()

        assert result["fritz"]["status"] == "unavailable"
        assert "connection refused" in result["fritz"]["error"]


# ---------------------------------------------------------------------------
# Partial failure
# ---------------------------------------------------------------------------


class TestPartialFailure:
    async def test_one_backend_down_does_not_block_others(self) -> None:
        class FailingBlindAdapter(MockBlindAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="offline")

        tv = MockTvAdapter()
        tv._activities = [Activity(id="1", name="Watch TV", adapter="harmony")]
        thermostat = MockThermostatAdapter()
        thermostat._devices = [
            LiveThermostat(
                id="1",
                name="Küche",
                adapter="fritz",
                online=True,
                current_temp=19.0,
                target_temp=20.0,
            )
        ]

        result = await _command(
            tv=tv, blind=FailingBlindAdapter(), thermostat=thermostat
        ).execute()

        assert result["harmony"]["status"] == "ok"
        assert result["homekit"]["status"] == "unavailable"
        assert result["fritz"]["status"] == "ok"

    async def test_all_backends_down_returns_all_unavailable(self) -> None:
        class FailingTvAdapter(MockTvAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="tv down")

        class FailingBlindAdapter(MockBlindAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="blind down")

        class FailingThermostatAdapter(MockThermostatAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="fritz down")

        result = await _command(
            tv=FailingTvAdapter(),
            blind=FailingBlindAdapter(),
            thermostat=FailingThermostatAdapter(),
        ).execute()

        assert result["harmony"]["status"] == "unavailable"
        assert result["homekit"]["status"] == "unavailable"
        assert result["fritz"]["status"] == "unavailable"


# ---------------------------------------------------------------------------
# Exception isolation
# ---------------------------------------------------------------------------


class TestExceptionIsolation:
    async def test_raising_backend_does_not_break_others(self) -> None:
        class RaisingTvAdapter(MockTvAdapter):
            async def list_backend(self) -> BackendListResult:
                raise RuntimeError("adapter not started")

        result = await _command(tv=RaisingTvAdapter()).execute()

        assert result["harmony"]["status"] == "unavailable"
        assert result["harmony"]["error"] == "unexpected backend error"
        assert result["homekit"]["status"] == "ok"
        assert result["fritz"]["status"] == "ok"
