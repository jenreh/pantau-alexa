"""Composition root — the only place that wires ports to adapters.

Instantiate once at application startup; inject into routers/use-cases via
FastAPI dependency injection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pantau.adapters.mock_blind_adapter import MockBlindAdapter
from pantau.adapters.mock_thermostat_adapter import MockThermostatAdapter
from pantau.adapters.mock_tv_adapter import MockTvAdapter
from pantau.adapters.yaml_device_registry import YamlDeviceRegistry
from pantau.config.settings import Settings

log = logging.getLogger(__name__)


@dataclass
class Container:
    """Holds all wired adapters. Use as FastAPI app state."""

    device_registry: YamlDeviceRegistry
    tv: MockTvAdapter
    blind: MockBlindAdapter
    thermostat: MockThermostatAdapter


def build_container(settings: Settings) -> Container:
    """Build the dependency container from settings."""
    log.info("Building dependency container (mock adapters)")
    return Container(
        device_registry=YamlDeviceRegistry(settings.devices_config_path),
        tv=MockTvAdapter(),
        blind=MockBlindAdapter(),
        thermostat=MockThermostatAdapter(),
    )
