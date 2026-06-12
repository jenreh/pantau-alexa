"""Lifespan: partial-start failures must stop already-started adapters."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tiberio.api.app import create_app
from tiberio.composition import build_test_container
from tiberio.config.settings import Settings

DEVICES_YAML = """
tv:
  watch_activity: "TV"
  audio:
    id: "tv-audio"
    friendly_name: "Fernseher"
  channels: []
blinds: []
thermostats: []
"""


class FakeLifecycleAdapter:
    def __init__(self, *, fail_on_start: bool = False) -> None:
        self._fail_on_start = fail_on_start
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        if self._fail_on_start:
            raise RuntimeError("start failed")
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


@pytest.fixture
def devices_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "devices.yaml"
    cfg.write_text(DEVICES_YAML, encoding="utf-8")
    return cfg


def test_partial_start_failure_stops_started_adapters(devices_config: Path) -> None:
    container = build_test_container(devices_config)
    first = FakeLifecycleAdapter()
    second = FakeLifecycleAdapter(fail_on_start=True)
    container.register(FakeLifecycleAdapter, first, adapter_name="fake-1")
    container.register(type("Second", (FakeLifecycleAdapter,), {}), second)

    app = create_app(settings=Settings(dev_mode=True), container=container)
    with pytest.raises(RuntimeError, match="start failed"), TestClient(app):
        pass

    assert first.started
    assert first.stopped, "already-started adapter must be stopped on failure"


def test_clean_startup_stops_all_adapters_on_shutdown(devices_config: Path) -> None:
    container = build_test_container(devices_config)
    adapter = FakeLifecycleAdapter()
    container.register(FakeLifecycleAdapter, adapter)

    app = create_app(settings=Settings(dev_mode=True), container=container)
    with TestClient(app):
        assert adapter.started
    assert adapter.stopped
