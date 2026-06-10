"""Tests for HomeKitBlindAdapter using an injected fake client."""

from __future__ import annotations

from typing import cast

import pytest
from homekit.client import HomeKitClient
from homekit.exceptions import AccessoryNotFoundError, HomeKitError

from pantau.adapters.homekit_blind_adapter import HomeKitBlindAdapter
from pantau.domain.errors import DeviceUnavailableError
from pantau.domain.models import WindowBlind


class FakeEntityState:
    def __init__(self, state: str) -> None:
        self.state = state


class FakeHomeKitClient:
    def __init__(
        self,
        *,
        position: int = 50,
        raise_on_set: Exception | None = None,
        raise_on_get: Exception | None = None,
    ) -> None:
        self._position = position
        self._raise_on_set = raise_on_set
        self._raise_on_get = raise_on_get
        self.set_position_calls: list[tuple[str, int]] = []
        self.start_count = 0
        self.stop_count = 0

    async def start(self) -> None:
        self.start_count += 1

    async def stop(self) -> None:
        self.stop_count += 1

    async def set_position(self, entity_id: str, percent: int) -> None:
        if self._raise_on_set:
            raise self._raise_on_set
        self.set_position_calls.append((entity_id, percent))

    async def get_state(self, entity_id: str) -> FakeEntityState:
        if self._raise_on_get:
            raise self._raise_on_get
        return FakeEntityState(state=str(self._position))


def _adapter(client: FakeHomeKitClient) -> HomeKitBlindAdapter:
    return HomeKitBlindAdapter(client=cast(HomeKitClient, client))


def _blind(external_id: str = "cover.kueche", invert: bool = False) -> WindowBlind:
    return WindowBlind(
        id="kueche-rollo",
        name="Rollo Küche",
        adapter="homekit",
        external_id=external_id,
        invert=invert,
    )


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    async def test_start_delegates_to_client(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client).start()
        assert client.start_count == 1

    async def test_stop_delegates_to_client(self) -> None:
        client = FakeHomeKitClient()
        adapter = _adapter(client)
        await adapter.start()
        await adapter.stop()
        assert client.stop_count == 1


# ---------------------------------------------------------------------------
# set_range (capability port)
# ---------------------------------------------------------------------------


class TestSetRange:
    async def test_delegates_to_client_with_external_id(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client).set_range(_blind(), 50)
        assert client.set_position_calls == [("cover.kueche", 50)]

    async def test_closed_position(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client).set_range(_blind(), 0)
        assert client.set_position_calls == [("cover.kueche", 0)]

    async def test_open_position(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client).set_range(_blind(), 100)
        assert client.set_position_calls == [("cover.kueche", 100)]

    async def test_invert_flips_position(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client).set_range(_blind(invert=True), 30)
        assert client.set_position_calls == [("cover.kueche", 70)]

    async def test_invert_half_stays_half(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client).set_range(_blind(invert=True), 50)
        assert client.set_position_calls == [("cover.kueche", 50)]

    async def test_accessory_not_found_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(
            raise_on_set=AccessoryNotFoundError("cover.kueche not found")
        )
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client).set_range(_blind(), 50)

    async def test_homekit_error_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(raise_on_set=HomeKitError("connection failed"))
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client).set_range(_blind(), 50)


# ---------------------------------------------------------------------------
# adjust_range (capability port)
# ---------------------------------------------------------------------------


class TestAdjustRange:
    async def test_increases_position(self) -> None:
        client = FakeHomeKitClient(position=40)
        new_pos = await _adapter(client).adjust_range(_blind(), 20)
        assert new_pos == 60
        assert client.set_position_calls == [("cover.kueche", 60)]

    async def test_decreases_position(self) -> None:
        client = FakeHomeKitClient(position=60)
        new_pos = await _adapter(client).adjust_range(_blind(), -20)
        assert new_pos == 40

    async def test_clamps_at_100(self) -> None:
        client = FakeHomeKitClient(position=90)
        new_pos = await _adapter(client).adjust_range(_blind(), 20)
        assert new_pos == 100

    async def test_clamps_at_0(self) -> None:
        client = FakeHomeKitClient(position=5)
        new_pos = await _adapter(client).adjust_range(_blind(), -20)
        assert new_pos == 0

    async def test_invert_adjust_position(self) -> None:
        # HomeKit stores 30, which maps to Alexa 70 (inverted).
        # Delta +10 → Alexa 80 → HomeKit 20.
        client = FakeHomeKitClient(position=30)
        new_pos = await _adapter(client).adjust_range(_blind(invert=True), 10)
        assert new_pos == 80
        assert client.set_position_calls[-1] == ("cover.kueche", 20)


# ---------------------------------------------------------------------------
# get_range (capability port)
# ---------------------------------------------------------------------------


class TestGetRange:
    async def test_returns_parsed_position(self) -> None:
        client = FakeHomeKitClient(position=75)
        pos = await _adapter(client).get_range(_blind())
        assert pos == 75

    async def test_returns_zero_for_closed(self) -> None:
        client = FakeHomeKitClient(position=0)
        assert await _adapter(client).get_range(_blind()) == 0

    async def test_invert_maps_homekit_to_alexa(self) -> None:
        client = FakeHomeKitClient(position=30)
        pos = await _adapter(client).get_range(_blind(invert=True))
        assert pos == 70

    async def test_accessory_not_found_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(raise_on_get=AccessoryNotFoundError("cover missing"))
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client).get_range(_blind())

    async def test_homekit_error_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(raise_on_get=HomeKitError("ble error"))
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client).get_range(_blind())


# ---------------------------------------------------------------------------
# Internal helpers — tests to protect existing behaviour
# ---------------------------------------------------------------------------


class TestSetPositionInternal:
    async def test_delegates_to_client(self) -> None:
        client = FakeHomeKitClient()
        await _adapter(client)._set_position("cover.kueche", 50)
        assert client.set_position_calls == [("cover.kueche", 50)]

    async def test_accessory_not_found_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(
            raise_on_set=AccessoryNotFoundError("cover.kueche not found")
        )
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client)._set_position("cover.kueche", 50)

    async def test_homekit_error_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(raise_on_set=HomeKitError("connection failed"))
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client)._set_position("cover.kueche", 50)


class TestGetPositionInternal:
    async def test_returns_parsed_position(self) -> None:
        client = FakeHomeKitClient(position=75)
        pos = await _adapter(client)._get_position("cover.kueche")
        assert pos == 75

    async def test_returns_zero_for_closed(self) -> None:
        client = FakeHomeKitClient(position=0)
        assert await _adapter(client)._get_position("cover.kueche") == 0

    async def test_returns_hundred_for_open(self) -> None:
        client = FakeHomeKitClient(position=100)
        assert await _adapter(client)._get_position("cover.kueche") == 100

    async def test_accessory_not_found_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(raise_on_get=AccessoryNotFoundError("cover missing"))
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client)._get_position("cover.kueche")

    async def test_homekit_error_raises_unavailable(self) -> None:
        client = FakeHomeKitClient(raise_on_get=HomeKitError("ble error"))
        with pytest.raises(DeviceUnavailableError):
            await _adapter(client)._get_position("cover.kueche")


class TestCapabilityGuard:
    async def test_non_blind_device_raises_capability_error(self) -> None:
        from pantau.domain.errors import DeviceCapabilityError
        from pantau.domain.models import TvAudio

        adapter = HomeKitBlindAdapter(client=cast(HomeKitClient, FakeHomeKitClient()))
        audio = TvAudio(id="tv-audio", name="Fernseher", adapter="harmony")
        with pytest.raises(DeviceCapabilityError):
            await adapter.set_range(audio, 50)
