"""Value objects — validated, invariant-enforcing wrappers for primitive domain values."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class MuteState(Enum):
    """Assumed mute state of the TV (toggle-only IR, so server tracks this)."""

    MUTED = "muted"
    UNMUTED = "unmuted"


class Temperature(BaseModel):
    """Target temperature in Celsius (rounded to 0.5-step).

    Range is not validated here; per-device min/max is enforced by the command layer
    using ``Thermostat.min_celsius`` / ``Thermostat.max_celsius``.
    """

    model_config = ConfigDict(frozen=True)

    celsius: float

    @classmethod
    def from_float(cls, value: float) -> Temperature:
        return cls(celsius=round(value * 2) / 2)  # round to 0.5-step


class Percentage(BaseModel):
    """A position value in percent (0–100), used for blind position."""

    model_config = ConfigDict(frozen=True)

    value: int

    @model_validator(mode="after")
    def _validate_range(self) -> Percentage:
        if not (0 <= self.value <= 100):
            msg = f"Percentage {self.value} is outside the valid range 0–100"
            raise ValueError(msg)
        return self

    @classmethod
    def half(cls) -> Percentage:
        return cls(value=50)

    @classmethod
    def closed(cls) -> Percentage:
        return cls(value=0)

    @classmethod
    def open(cls) -> Percentage:
        return cls(value=100)
