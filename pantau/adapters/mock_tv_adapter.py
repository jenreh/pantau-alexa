"""Mock TV adapter — logs operations, no real hardware connection."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class MockTvAdapter:
    """Stub implementation of TvPort for development and testing."""

    def __init__(self) -> None:
        self._current_activity: str | None = None

    async def ensure_activity(self, activity_name: str) -> None:
        log.info("MockTV: ensure_activity=%s", activity_name)
        self._current_activity = activity_name

    async def set_channel(self, channel_number: str) -> None:
        log.info("MockTV: set_channel=%s", channel_number)

    async def toggle_mute(self) -> None:
        log.info("MockTV: toggle_mute")

    async def get_current_activity(self) -> str | None:
        log.info("MockTV: get_current_activity -> %s", self._current_activity)
        return self._current_activity
