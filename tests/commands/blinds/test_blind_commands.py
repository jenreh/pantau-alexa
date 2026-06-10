"""Tests for blind commands: SetRangeCommand and AdjustRangeCommand."""

from __future__ import annotations

import pytest

from pantau.adapters.mock_blind_adapter import MockBlindAdapter
from pantau.adapters.yaml_device_registry import YamlDeviceRegistry
from pantau.commands.adjust_range import AdjustRangeCommand
from pantau.commands.set_range import SetRangeCommand
from pantau.composition import Container
from pantau.domain.errors import DeviceNotFoundError


def _container(adapter: MockBlindAdapter, registry: YamlDeviceRegistry) -> Container:
    c = Container()
    c.register(type(adapter), adapter, adapter_name="homekit")
    return c


class TestSetRangeCommand:
    @pytest.fixture
    def adapter(self) -> MockBlindAdapter:
        return MockBlindAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockBlindAdapter
    ) -> SetRangeCommand:
        return SetRangeCommand(registry, _container(adapter, registry))  # type: ignore[arg-type]

    async def test_sets_range_on_adapter(
        self, command: SetRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        await command.execute("kueche-rollo", 50)
        assert len(adapter.set_range_calls) == 1
        device, value = adapter.set_range_calls[0]
        assert device.id == "kueche-rollo"
        assert value == 50

    async def test_position_closed(
        self, command: SetRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        await command.execute("kueche-rollo", 0)
        _, value = adapter.set_range_calls[0]
        assert value == 0

    async def test_position_open(
        self, command: SetRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        await command.execute("kueche-rollo", 100)
        _, value = adapter.set_range_calls[0]
        assert value == 100

    async def test_invalid_percentage_raises(self, command: SetRangeCommand) -> None:
        with pytest.raises(ValueError):
            await command.execute("kueche-rollo", 101)

    async def test_invalid_negative_raises(self, command: SetRangeCommand) -> None:
        with pytest.raises(ValueError):
            await command.execute("kueche-rollo", -1)

    async def test_unknown_endpoint_raises(self, command: SetRangeCommand) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("does-not-exist", 50)


class TestAdjustRangeCommand:
    @pytest.fixture
    def adapter(self) -> MockBlindAdapter:
        return MockBlindAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockBlindAdapter
    ) -> AdjustRangeCommand:
        return AdjustRangeCommand(registry, _container(adapter, registry))  # type: ignore[arg-type]

    async def test_adjust_range_returns_new_position(
        self, command: AdjustRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        adapter._positions["kueche-rollo"] = 40
        result = await command.execute("kueche-rollo", delta=20)
        assert result == 60

    async def test_adjust_range_clamps_to_100(
        self, command: AdjustRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        adapter._positions["kueche-rollo"] = 90
        result = await command.execute("kueche-rollo", delta=20)
        assert result == 100

    async def test_adjust_range_clamps_to_0(
        self, command: AdjustRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        adapter._positions["kueche-rollo"] = 10
        result = await command.execute("kueche-rollo", delta=-20)
        assert result == 0

    async def test_adjust_range_records_call(
        self, command: AdjustRangeCommand, adapter: MockBlindAdapter
    ) -> None:
        await command.execute("kueche-rollo", delta=10)
        assert len(adapter.adjust_range_calls) == 1
        device, delta = adapter.adjust_range_calls[0]
        assert device.id == "kueche-rollo"
        assert delta == 10

    async def test_unknown_endpoint_raises(self, command: AdjustRangeCommand) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("does-not-exist", delta=10)
