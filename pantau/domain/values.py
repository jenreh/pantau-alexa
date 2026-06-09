"""Value objects — validated, invariant-enforcing wrappers for primitive domain values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MuteState(Enum):
    """Assumed mute state of the TV (toggle-only IR, so server tracks this)."""

    MUTED = "muted"
    UNMUTED = "unmuted"


@dataclass(frozen=True, slots=True)
class Temperature:
    """Target temperature in Celsius, constrained to the FRITZ!Box-safe range."""

    celsius: float

    _MIN: float = 8.0
    _MAX: float = 28.0

    def __post_init__(self) -> None:
        if not (self._MIN <= self.celsius <= self._MAX):
            msg = f"Temperature {self.celsius}°C is outside the valid range {self._MIN}–{self._MAX}°C"
            raise ValueError(msg)

    @classmethod
    def from_float(cls, value: float) -> Temperature:
        return cls(celsius=round(value * 2) / 2)  # round to 0.5-step


@dataclass(frozen=True, slots=True)
class Percentage:
    """A position value in percent (0–100), used for blind position."""

    value: int

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            msg = f"Percentage {self.value} is outside the valid range 0–100"
            raise ValueError(msg)

    @classmethod
    def half(cls) -> Percentage:
        return cls(value=50)

    @classmethod
    def closed(cls) -> Percentage:
        return cls(value=0)

    @classmethod
    def open(cls) -> Percentage:
        return cls(value=100)
