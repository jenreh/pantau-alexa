"""Domain models — Pydantic-based, adapter-agnostic home automation entities."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Device(BaseModel):
    """Base class for all domain devices.

    ``adapter`` names the backend that owns this device (e.g. ``"homekit"``,
    ``"harmony"``, ``"fritz"``).  A generic command can use it to route to the
    right port without hard-coding the type check:

        async def turn_on(device: Device) -> None:
            port = container.get_by_adapter(device.adapter)
            await port.turn_on(device.id)
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    adapter: str
    aliases: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Configured device types (loaded from devices.yaml)
# ---------------------------------------------------------------------------


class TvChannel(Device):
    """A TV channel exposed as an Alexa PowerController endpoint."""

    channel_number: str = ""


class TvAudio(Device):
    """The TV audio endpoint (mute/unmute via Alexa.Speaker)."""


class Tv(BaseModel):
    """TV configuration — channels, audio and the Harmony activity to activate."""

    model_config = ConfigDict(frozen=True)

    watch_activity: str
    audio: TvAudio
    channels: tuple[TvChannel, ...]


class WindowBlind(Device):
    """A roller blind/shutter (Alexa.RangeController).

    ``external_id`` is the adapter-specific reference used by BlindPort
    (e.g. the HomeKit entity_id ``"cover.kueche"``).
    """

    external_id: str
    invert: bool = False


class Thermostat(Device):
    """A heating thermostat (Alexa.ThermostatController).

    ``external_id`` is the adapter-specific reference used by ThermostatPort
    (e.g. the FRITZ!Box device name ``"Wohnzimmer"``).
    """

    external_id: str
    min_celsius: float = 8.0
    max_celsius: float = 28.0


class DeviceRegistry(BaseModel):
    """All configured devices, loaded from devices.yaml."""

    model_config = ConfigDict(frozen=True)

    tv: Tv
    blinds: tuple[WindowBlind, ...]
    thermostats: tuple[Thermostat, ...]


# ---------------------------------------------------------------------------
# Live-discovered backend types (returned by port list_* methods)
# ---------------------------------------------------------------------------


class Activity(Device):
    """A Harmony Hub activity (e.g. "Watch TV", "PowerOff")."""

    is_power_off: bool = False


class HubDevice(Device):
    """A physical device registered on the Harmony Hub."""

    manufacturer: str | None = None
    model: str | None = None


class HomeDevice(Device):
    """A device discovered on the smart-home network (e.g. via HomeKit)."""

    domain: str
    room: str | None = None


class LiveThermostat(Device):
    """A FRITZ!Box thermostat with real-time state."""

    online: bool
    current_temp: float
    target_temp: float
    battery_level: int | None = None
    battery_low: bool = False
