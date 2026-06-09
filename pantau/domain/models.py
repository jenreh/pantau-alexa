"""Domain models — immutable data structures representing the home automation domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChannelDevice:
    """A TV channel exposed as an Alexa PowerController endpoint."""

    id: str
    friendly_name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    channel_number: str = ""


@dataclass(frozen=True, slots=True)
class TvAudioDevice:
    """The TV audio endpoint (mute/unmute via Alexa.Speaker)."""

    id: str
    friendly_name: str


@dataclass(frozen=True, slots=True)
class TvConfig:
    """Configuration for the Harmony Hub TV integration."""

    harmony_host: str
    watch_activity: str
    audio: TvAudioDevice
    channels: tuple[ChannelDevice, ...]


@dataclass(frozen=True, slots=True)
class BlindDevice:
    """A roller blind/shutter controlled via HomeKit (Alexa.RangeController)."""

    id: str
    friendly_name: str
    homekit_entity_id: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    invert: bool = False


@dataclass(frozen=True, slots=True)
class ThermostatDevice:
    """A heating thermostat controlled via fritzctl (Alexa.ThermostatController)."""

    id: str
    friendly_name: str
    fritz_name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    min_celsius: float = 8.0
    max_celsius: float = 28.0


@dataclass(frozen=True, slots=True)
class DeviceRegistry:
    """All configured devices, loaded from devices.yaml."""

    tv: TvConfig
    blinds: tuple[BlindDevice, ...]
    thermostats: tuple[ThermostatDevice, ...]
