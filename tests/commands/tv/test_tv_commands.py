"""Tests for TV commands: TurnOnCommand and SetMuteCommand."""

from __future__ import annotations

import pytest

from tiberio.adapters.mock_tv_adapter import MockTvAdapter
from tiberio.adapters.yaml_device_registry import YamlDeviceRegistry
from tiberio.commands.set_mute import SetMuteCommand
from tiberio.commands.turn_off import TurnOffCommand
from tiberio.commands.turn_on import TurnOnCommand
from tiberio.composition import Container
from tiberio.domain.errors import DeviceNotFoundError
from tiberio.domain.models import TvChannel


def _container(adapter: MockTvAdapter, registry: YamlDeviceRegistry) -> Container:
    c = Container()
    c.register(type(adapter), adapter, adapter_name="harmony")
    return c


class TestTurnOnCommand:
    @pytest.fixture
    def adapter(self) -> MockTvAdapter:
        return MockTvAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockTvAdapter
    ) -> TurnOnCommand:
        return TurnOnCommand(registry, _container(adapter, registry))  # type: ignore[arg-type]

    async def test_turn_on_channel_calls_adapter(
        self, command: TurnOnCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("zdf")
        assert len(adapter.turn_on_calls) == 1
        device = adapter.turn_on_calls[0]
        assert isinstance(device, TvChannel)
        assert device.id == "zdf"
        assert device.channel_number == "2"
        assert device.watch_activity == "Fernseher"

    async def test_turn_on_ard(
        self, command: TurnOnCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("ard")
        assert adapter.turn_on_calls[0].id == "ard"

    async def test_multiple_calls_recorded(
        self, command: TurnOnCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("zdf")
        await command.execute("ard")
        assert len(adapter.turn_on_calls) == 2

    async def test_unknown_endpoint_raises(self, command: TurnOnCommand) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("sky-sport")


class TestTurnOffCommand:
    @pytest.fixture
    def adapter(self) -> MockTvAdapter:
        return MockTvAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockTvAdapter
    ) -> TurnOffCommand:
        return TurnOffCommand(registry, _container(adapter, registry))  # type: ignore[arg-type]

    async def test_turn_off_channel_calls_adapter(
        self, command: TurnOffCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("zdf")
        assert len(adapter.turn_off_calls) == 1
        assert adapter.turn_off_calls[0].id == "zdf"

    async def test_unknown_endpoint_raises(self, command: TurnOffCommand) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("unknown")


class TestSetMuteCommand:
    @pytest.fixture
    def adapter(self) -> MockTvAdapter:
        return MockTvAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockTvAdapter
    ) -> SetMuteCommand:
        return SetMuteCommand(registry, _container(adapter, registry))  # type: ignore[arg-type]

    async def test_set_mute_true_calls_adapter(
        self, command: SetMuteCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("tv-audio", mute=True)
        assert len(adapter.set_mute_calls) == 1
        device, muted = adapter.set_mute_calls[0]
        assert device.id == "tv-audio"
        assert muted is True

    async def test_set_mute_false_calls_adapter(
        self, command: SetMuteCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("tv-audio", mute=False)
        _, muted = adapter.set_mute_calls[0]
        assert muted is False

    async def test_multiple_mute_calls_recorded(
        self, command: SetMuteCommand, adapter: MockTvAdapter
    ) -> None:
        await command.execute("tv-audio", mute=True)
        await command.execute("tv-audio", mute=False)
        assert len(adapter.set_mute_calls) == 2

    async def test_unknown_endpoint_raises(self, command: SetMuteCommand) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("bad-endpoint", mute=True)
