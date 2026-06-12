"""Tests for mock adapters — cover new capability port paths."""

from __future__ import annotations

import pytest

from tiberio.adapters.mock_blind_adapter import MockBlindAdapter
from tiberio.adapters.mock_thermostat_adapter import MockThermostatAdapter
from tiberio.adapters.mock_tv_adapter import MockTvAdapter
from tiberio.domain.models import Thermostat as DomainThermostat
from tiberio.domain.models import TvAudio, TvChannel, WindowBlind


def _channel() -> TvChannel:
    return TvChannel(
        id="zdf",
        name="ZDF",
        adapter="harmony",
        channel_number="2",
        watch_activity="Fernseher",
    )


def _audio() -> TvAudio:
    return TvAudio(id="tv-audio", name="Fernseher", adapter="harmony")


def _blind(device_id: str = "kueche-rollo") -> WindowBlind:
    return WindowBlind(
        id=device_id, name="Rollo Küche", adapter="homekit", external_id="cover.kueche"
    )


def _thermostat() -> DomainThermostat:
    return DomainThermostat(
        id="wohnzimmer-heizung",
        name="Heizung Wohnzimmer",
        adapter="fritz",
        external_id="Wohnzimmer",
    )


class TestMockTvAdapter:
    @pytest.fixture
    def adapter(self) -> MockTvAdapter:
        return MockTvAdapter()

    async def test_turn_on_records_call(self, adapter: MockTvAdapter) -> None:
        device = _channel()
        await adapter.turn_on(device)
        assert adapter.turn_on_calls == [device]

    async def test_turn_off_records_call(self, adapter: MockTvAdapter) -> None:
        device = _channel()
        await adapter.turn_off(device)
        assert adapter.turn_off_calls == [device]

    async def test_set_mute_records_call(self, adapter: MockTvAdapter) -> None:
        device = _audio()
        await adapter.set_mute(device, True)
        assert adapter.set_mute_calls == [(device, True)]

    async def test_toggle_mute_increments_count(self, adapter: MockTvAdapter) -> None:
        await adapter.toggle_mute()
        await adapter.toggle_mute()
        assert adapter.toggle_mute_count == 2

    async def test_list_backend_returns_ok(self, adapter: MockTvAdapter) -> None:
        result = await adapter.list_backend()
        assert result.status == "ok"


class TestMockBlindAdapter:
    @pytest.fixture
    def adapter(self) -> MockBlindAdapter:
        return MockBlindAdapter()

    async def test_set_range_records_call(self, adapter: MockBlindAdapter) -> None:
        device = _blind()
        await adapter.set_range(device, 50)
        assert adapter.set_range_calls == [(device, 50)]

    async def test_get_range_default_zero(self, adapter: MockBlindAdapter) -> None:
        device = _blind()
        assert await adapter.get_range(device) == 0

    async def test_set_and_get_range(self, adapter: MockBlindAdapter) -> None:
        device = _blind()
        await adapter.set_range(device, 75)
        assert await adapter.get_range(device) == 75

    async def test_adjust_range_returns_clamped_value(
        self, adapter: MockBlindAdapter
    ) -> None:
        device = _blind()
        adapter._positions[device.id] = 90
        result = await adapter.adjust_range(device, 20)
        assert result == 100

    async def test_list_backend_returns_ok(self, adapter: MockBlindAdapter) -> None:
        result = await adapter.list_backend()
        assert result.status == "ok"


class TestMockThermostatAdapter:
    @pytest.fixture
    def adapter(self) -> MockThermostatAdapter:
        return MockThermostatAdapter()

    async def test_set_temperature_records_call(
        self, adapter: MockThermostatAdapter
    ) -> None:
        device = _thermostat()
        await adapter.set_temperature(device, 22.0)
        assert adapter.set_temperature_calls == [(device, 22.0)]

    async def test_get_temperature_default(
        self, adapter: MockThermostatAdapter
    ) -> None:
        device = _thermostat()
        assert await adapter.get_temperature(device) == 20.0

    async def test_set_and_get_temperature(
        self, adapter: MockThermostatAdapter
    ) -> None:
        device = _thermostat()
        await adapter.set_temperature(device, 22.0)
        assert await adapter.get_temperature(device) == 22.0

    async def test_list_backend_returns_ok(
        self, adapter: MockThermostatAdapter
    ) -> None:
        result = await adapter.list_backend()
        assert result.status == "ok"
