"""Tests for GetSpeakerStateCommand."""

from __future__ import annotations

import pytest

from pantau.adapters.mock_tv_adapter import MockTvAdapter
from pantau.adapters.yaml_device_registry import YamlDeviceRegistry
from pantau.commands.get_speaker_state import GetSpeakerStateCommand
from pantau.composition import Container
from pantau.domain.errors import DeviceNotFoundError


def _container(adapter: MockTvAdapter) -> Container:
    c = Container()
    c.register(type(adapter), adapter, adapter_name="harmony")
    return c


class TestGetSpeakerStateCommand:
    @pytest.fixture
    def adapter(self) -> MockTvAdapter:
        return MockTvAdapter()

    @pytest.fixture
    def command(
        self, registry: YamlDeviceRegistry, adapter: MockTvAdapter
    ) -> GetSpeakerStateCommand:
        return GetSpeakerStateCommand(registry, _container(adapter))  # type: ignore[arg-type]

    async def test_returns_initial_state(self, command: GetSpeakerStateCommand) -> None:
        muted, volume = await command.execute("tv-audio")
        assert muted is False
        assert volume == 50

    async def test_reflects_mute_after_set(
        self, command: GetSpeakerStateCommand, adapter: MockTvAdapter
    ) -> None:
        adapter._assumed_mute = True
        muted, _ = await command.execute("tv-audio")
        assert muted is True

    async def test_reflects_volume_after_set(
        self, command: GetSpeakerStateCommand, adapter: MockTvAdapter
    ) -> None:
        adapter._assumed_volume = 75
        _, volume = await command.execute("tv-audio")
        assert volume == 75

    async def test_unknown_endpoint_raises(
        self, command: GetSpeakerStateCommand
    ) -> None:
        with pytest.raises(DeviceNotFoundError):
            await command.execute("does-not-exist")
