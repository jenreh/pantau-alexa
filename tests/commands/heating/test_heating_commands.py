"""Tests for heating commands: SetTemperatureCommand."""

from __future__ import annotations

import pytest

from tiberio.adapters.mock_thermostat_adapter import MockThermostatAdapter
from tiberio.adapters.yaml_device_registry import YamlDeviceRegistry
from tiberio.commands.set_temperature import SetTemperatureCommand
from tiberio.composition import Container
from tiberio.domain.errors import DeviceCapabilityError, DeviceNotFoundError


def _container(
    adapter: MockThermostatAdapter, registry: YamlDeviceRegistry
) -> Container:
    c = Container()
    c.register(type(adapter), adapter, adapter_name="fritz")
    return c


class TestSetTemperatureCommand:
    @pytest.fixture
    def adapter(self) -> MockThermostatAdapter:
        return MockThermostatAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockThermostatAdapter
    ) -> SetTemperatureCommand:
        return SetTemperatureCommand(registry, _container(adapter, registry))  # type: ignore[arg-type]

    async def test_sets_temperature_on_adapter(
        self, command: SetTemperatureCommand, adapter: MockThermostatAdapter
    ) -> None:
        await command.execute("wohnzimmer-heizung", 22.0)
        assert len(adapter.set_temperature_calls) == 1
        device, celsius = adapter.set_temperature_calls[0]
        assert device.id == "wohnzimmer-heizung"
        assert celsius == 22.0

    async def test_rounds_to_half_degree(
        self, command: SetTemperatureCommand, adapter: MockThermostatAdapter
    ) -> None:
        await command.execute("wohnzimmer-heizung", 21.3)
        _, celsius = adapter.set_temperature_calls[0]
        assert celsius == 21.5

    async def test_temperature_at_device_min(
        self, command: SetTemperatureCommand, adapter: MockThermostatAdapter
    ) -> None:
        await command.execute("wohnzimmer-heizung", 16.0)
        _, celsius = adapter.set_temperature_calls[0]
        assert celsius == 16.0

    async def test_temperature_at_device_max(
        self, command: SetTemperatureCommand, adapter: MockThermostatAdapter
    ) -> None:
        await command.execute("wohnzimmer-heizung", 24.0)
        _, celsius = adapter.set_temperature_calls[0]
        assert celsius == 24.0

    async def test_temperature_below_device_min_raises(
        self, command: SetTemperatureCommand
    ) -> None:
        with pytest.raises(ValueError, match="valid range"):
            await command.execute("wohnzimmer-heizung", 15.0)

    async def test_temperature_above_device_max_raises(
        self, command: SetTemperatureCommand
    ) -> None:
        with pytest.raises(ValueError, match="valid range"):
            await command.execute("wohnzimmer-heizung", 25.0)

    async def test_unknown_endpoint_raises(
        self, command: SetTemperatureCommand
    ) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("does-not-exist", 20.0)

    async def test_non_thermostat_endpoint_raises_capability_error(
        self, command: SetTemperatureCommand
    ) -> None:
        with pytest.raises(DeviceCapabilityError):
            await command.execute("tv-audio", 20.0)
