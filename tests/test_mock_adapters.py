"""Tests for mock adapters — cover getter paths."""

from __future__ import annotations

import pytest

from pantau.adapters.mock_blind_adapter import MockBlindAdapter
from pantau.adapters.mock_thermostat_adapter import MockThermostatAdapter
from pantau.adapters.mock_tv_adapter import MockTvAdapter


class TestMockTvAdapter:
    @pytest.fixture
    def adapter(self) -> MockTvAdapter:
        return MockTvAdapter()

    async def test_get_current_activity_initially_none(
        self, adapter: MockTvAdapter
    ) -> None:
        assert await adapter.get_current_activity() is None

    async def test_ensure_activity_sets_current(self, adapter: MockTvAdapter) -> None:
        await adapter.ensure_activity("Fernseher")
        assert await adapter.get_current_activity() == "Fernseher"

    async def test_set_channel(self, adapter: MockTvAdapter) -> None:
        await adapter.set_channel("2")  # no exception

    async def test_toggle_mute(self, adapter: MockTvAdapter) -> None:
        await adapter.toggle_mute()  # no exception


class TestMockBlindAdapter:
    @pytest.fixture
    def adapter(self) -> MockBlindAdapter:
        return MockBlindAdapter()

    async def test_get_position_default_zero(self, adapter: MockBlindAdapter) -> None:
        assert await adapter.get_position("cover.kueche") == 0

    async def test_set_and_get_position(self, adapter: MockBlindAdapter) -> None:
        await adapter.set_position("cover.kueche", 50)
        assert await adapter.get_position("cover.kueche") == 50


class TestMockThermostatAdapter:
    @pytest.fixture
    def adapter(self) -> MockThermostatAdapter:
        return MockThermostatAdapter()

    async def test_get_temperature_default(
        self, adapter: MockThermostatAdapter
    ) -> None:
        assert await adapter.get_temperature("Wohnzimmer") == 20.0

    async def test_set_and_get_temperature(
        self, adapter: MockThermostatAdapter
    ) -> None:
        await adapter.set_temperature("Wohnzimmer", 22.0)
        assert await adapter.get_temperature("Wohnzimmer") == 22.0
