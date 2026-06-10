"""Startup security validation: empty jwt_secret must fail fast in prod mode."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from pantau.api.app import create_app
from pantau.config.settings import Settings

DEVICES_YAML = """
tv:
  watch_activity: "TV"
  audio:
    id: "tv-audio"
    friendly_name: "Fernseher"
  channels:
    - id: "ard"
      friendly_name: "ARD"
      channel_number: "1"
blinds: []
thermostats: []
"""


@pytest.fixture
def devices_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "devices.yaml"
    cfg.write_text(DEVICES_YAML, encoding="utf-8")
    return cfg


def test_empty_jwt_secret_without_dev_mode_fails_fast(devices_config: Path) -> None:
    settings = Settings(devices_config_path=devices_config, dev_mode=False)
    with pytest.raises(RuntimeError, match="PANTAU_JWT_SECRET"):
        create_app(settings=settings)


def test_empty_jwt_secret_with_dev_mode_boots(devices_config: Path) -> None:
    settings = Settings(devices_config_path=devices_config, dev_mode=True)
    app = create_app(settings=settings)
    assert app is not None


def test_short_jwt_secret_without_dev_mode_fails_fast(devices_config: Path) -> None:
    settings = Settings(
        devices_config_path=devices_config,
        dev_mode=False,
        jwt_secret=SecretStr("short"),
    )
    with pytest.raises(RuntimeError, match="32"):
        create_app(settings=settings)


def test_strong_jwt_secret_without_dev_mode_boots(devices_config: Path) -> None:
    settings = Settings(
        devices_config_path=devices_config,
        dev_mode=False,
        jwt_secret=SecretStr("x" * 32),
    )
    app = create_app(settings=settings)
    assert app is not None
