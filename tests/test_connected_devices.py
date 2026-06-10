"""Tests for the GET /devices/connected endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pantau.adapters.mock_blind_adapter import MockBlindAdapter
from pantau.adapters.mock_thermostat_adapter import MockThermostatAdapter
from pantau.adapters.mock_tv_adapter import MockTvAdapter
from pantau.api.app import create_app
from pantau.composition import build_test_container
from pantau.config.settings import Settings
from pantau.domain.models import (
    Activity,
    HomeDevice,
    HubDevice,
    LiveThermostat,
)
from pantau.ports.listable_port import BackendListResult

DEVICES_YAML = """
tv:
  watch_activity: "Fernseher"
  audio:
    id: "tv-audio"
    friendly_name: "Fernseher"
  channels:
    - id: "ard"
      friendly_name: "ARD"
      channel_number: "1"
blinds:
  - id: "kueche-rollo"
    friendly_name: "Rollo Küche"
    homekit_entity_id: "cover.kueche"
thermostats:
  - id: "wohnzimmer-heizung"
    friendly_name: "Heizung Wohnzimmer"
    fritz_name: "Wohnzimmer"
"""


@pytest.fixture
def devices_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "devices.yaml"
    cfg.write_text(DEVICES_YAML, encoding="utf-8")
    return cfg


def _make_client(
    devices_config: Path,
    tv: MockTvAdapter | None = None,
    blind: MockBlindAdapter | None = None,
    thermostat: MockThermostatAdapter | None = None,
) -> TestClient:
    container = build_test_container(devices_config)
    # Override adapter instances so tests can inject canned data.
    # The ListConnectedDevicesCommand holds a reference to container and calls
    # all_implementing() at execute-time, so updating _by_adapter here is enough.
    if tv is not None:
        container.register(type(tv), tv, adapter_name="harmony")
    if blind is not None:
        container.register(type(blind), blind, adapter_name="homekit")
    if thermostat is not None:
        container.register(type(thermostat), thermostat, adapter_name="fritz")
    app = create_app(settings=Settings(dev_mode=True), container=container)
    # MockTokenValidator accepts any non-empty bearer token.
    return TestClient(app, headers={"Authorization": "Bearer test-token"})


@pytest.fixture
def client(devices_config: Path) -> TestClient:
    return _make_client(devices_config)


# ---------------------------------------------------------------------------
# Basic shape
# ---------------------------------------------------------------------------


class TestConnectedDevicesAuth:
    def test_missing_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/devices/connected", headers={"Authorization": ""})
        assert response.status_code == 401

    def test_malformed_header_returns_401(self, client: TestClient) -> None:
        response = client.get(
            "/devices/connected", headers={"Authorization": "Basic abc"}
        )
        assert response.status_code == 401


class TestConnectedDevicesShape:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/devices/connected")
        assert response.status_code == 200

    def test_response_has_three_backend_keys(self, client: TestClient) -> None:
        body = client.get("/devices/connected").json()
        assert set(body.keys()) == {"harmony", "homekit", "fritz"}

    def test_each_backend_has_status_key(self, client: TestClient) -> None:
        body = client.get("/devices/connected").json()
        for key in ("harmony", "homekit", "fritz"):
            assert "status" in body[key], f"missing 'status' in {key}"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestConnectedDevicesHappyPath:
    def test_harmony_activities_appear_in_response(self, devices_config: Path) -> None:
        tv = MockTvAdapter()
        tv._activities = [
            Activity(id="1", name="Watch TV", adapter="harmony"),
            Activity(id="-1", name="PowerOff", adapter="harmony", is_power_off=True),
        ]
        body = _make_client(devices_config, tv=tv).get("/devices/connected").json()
        activities = body["harmony"]["activities"]
        assert len(activities) == 2
        assert activities[0]["name"] == "Watch TV"
        assert activities[1]["is_power_off"] is True

    def test_harmony_devices_appear_in_response(self, devices_config: Path) -> None:
        tv = MockTvAdapter()
        tv._devices = [
            HubDevice(
                id="10",
                name="Samsung TV",
                adapter="harmony",
                manufacturer="Samsung",
                model="QN55",
            )
        ]
        body = _make_client(devices_config, tv=tv).get("/devices/connected").json()
        devices = body["harmony"]["devices"]
        assert len(devices) == 1
        assert devices[0]["manufacturer"] == "Samsung"

    def test_homekit_entities_appear_in_response(self, devices_config: Path) -> None:
        blind = MockBlindAdapter()
        blind._devices = [
            HomeDevice(
                id="cover.kueche",
                name="Küche Rollo",
                adapter="homekit",
                domain="cover",
                room="Küche",
            )
        ]
        body = (
            _make_client(devices_config, blind=blind).get("/devices/connected").json()
        )
        devices = body["homekit"]["devices"]
        assert len(devices) == 1
        assert devices[0]["id"] == "cover.kueche"
        assert devices[0]["room"] == "Küche"

    def test_fritz_devices_appear_in_response(self, devices_config: Path) -> None:
        thermostat = MockThermostatAdapter()
        thermostat._devices = [
            LiveThermostat(
                id="11630 0000001",
                name="Wohnzimmer",
                adapter="fritz",
                online=True,
                current_temp=20.5,
                target_temp=21.0,
                battery_level=75,
                battery_low=False,
            )
        ]
        body = (
            _make_client(devices_config, thermostat=thermostat)
            .get("/devices/connected")
            .json()
        )
        fritz_devices = body["fritz"]["devices"]
        assert len(fritz_devices) == 1
        assert fritz_devices[0]["name"] == "Wohnzimmer"
        assert fritz_devices[0]["current_temp"] == pytest.approx(20.5)
        assert fritz_devices[0]["battery_level"] == 75


# ---------------------------------------------------------------------------
# Partial failure
# ---------------------------------------------------------------------------


class TestConnectedDevicesPartialFailure:
    def test_unavailable_harmony_still_returns_200(self, devices_config: Path) -> None:
        class FailingTvAdapter(MockTvAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="hub down")

        body = (
            _make_client(devices_config, tv=FailingTvAdapter())
            .get("/devices/connected")
            .json()
        )
        assert body["harmony"]["status"] == "unavailable"
        assert "hub down" in body["harmony"]["error"]
        assert body["homekit"]["status"] == "ok"
        assert body["fritz"]["status"] == "ok"

    def test_unavailable_homekit_still_returns_200(self, devices_config: Path) -> None:
        class FailingBlindAdapter(MockBlindAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(status="unavailable", error="daemon offline")

        body = (
            _make_client(devices_config, blind=FailingBlindAdapter())
            .get("/devices/connected")
            .json()
        )
        assert body["homekit"]["status"] == "unavailable"
        assert body["harmony"]["status"] == "ok"
        assert body["fritz"]["status"] == "ok"

    def test_unavailable_fritz_still_returns_200(self, devices_config: Path) -> None:
        class FailingThermostatAdapter(MockThermostatAdapter):
            async def list_backend(self) -> BackendListResult:
                return BackendListResult(
                    status="unavailable", error="fritz unreachable"
                )

        body = (
            _make_client(devices_config, thermostat=FailingThermostatAdapter())
            .get("/devices/connected")
            .json()
        )
        assert body["fritz"]["status"] == "unavailable"
        assert body["harmony"]["status"] == "ok"
        assert body["homekit"]["status"] == "ok"

    def test_error_field_absent_when_backend_ok(self, client: TestClient) -> None:
        body = client.get("/devices/connected").json()
        for key in ("harmony", "homekit", "fritz"):
            assert "error" not in body[key], f"unexpected 'error' in {key}"
