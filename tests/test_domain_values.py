"""Tests for domain value objects."""

from __future__ import annotations

import pytest

from pantau.domain.values import MuteState, Percentage, Temperature


class TestTemperature:
    def test_valid_temperature(self) -> None:
        t = Temperature.from_float(22.0)
        assert t.celsius == 22.0

    def test_rounds_to_half_degree(self) -> None:
        t = Temperature.from_float(22.3)
        assert t.celsius == 22.5

    def test_rounds_down(self) -> None:
        t = Temperature.from_float(22.2)
        assert t.celsius == 22.0

    def test_accepts_any_numeric_value(self) -> None:
        # Range is enforced by SetThermostatTemperatureCommand using per-device min/max.
        assert Temperature(celsius=7.9).celsius == 7.9
        assert Temperature(celsius=28.1).celsius == 28.1


class TestPercentage:
    def test_valid_percentage(self) -> None:
        p = Percentage(value=50)
        assert p.value == 50

    def test_zero_is_valid(self) -> None:
        p = Percentage(value=0)
        assert p.value == 0

    def test_hundred_is_valid(self) -> None:
        p = Percentage(value=100)
        assert p.value == 100

    def test_below_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            Percentage(value=-1)

    def test_above_hundred_raises(self) -> None:
        with pytest.raises(ValueError):
            Percentage(value=101)


class TestMuteState:
    def test_muted(self) -> None:
        assert MuteState.MUTED.value == "muted"

    def test_unmuted(self) -> None:
        assert MuteState.UNMUTED.value == "unmuted"
