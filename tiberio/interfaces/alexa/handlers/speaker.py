"""Alexa.Speaker handler — SetMute, SetVolume, AdjustVolume."""

from __future__ import annotations

import logging

from tiberio.commands.adjust_volume import AdjustVolumeCommand
from tiberio.commands.get_speaker_state import GetSpeakerStateCommand
from tiberio.commands.set_mute import SetMuteCommand
from tiberio.commands.set_volume import SetVolumeCommand
from tiberio.interfaces.alexa.handlers._base import (
    AlexaHandler,
    DirectiveContext,
    InvalidPayloadError,
    require_field,
    require_int,
)
from tiberio.interfaces.alexa.response_builder import build_property

log = logging.getLogger(__name__)


class SpeakerHandler(AlexaHandler):
    def __init__(
        self,
        set_mute: SetMuteCommand,
        set_volume: SetVolumeCommand,
        adjust_volume: AdjustVolumeCommand,
        get_speaker_state: GetSpeakerStateCommand,
    ) -> None:
        self._set_mute = set_mute
        self._set_volume = set_volume
        self._adjust_volume = adjust_volume
        self._get_speaker_state = get_speaker_state

    async def _execute(self, ctx: DirectiveContext) -> list[dict]:
        if ctx.name == "SetMute":
            mute = require_field(ctx.payload, "mute")
            if not isinstance(mute, bool):
                raise InvalidPayloadError("Payload field 'mute' must be a boolean")
            await self._set_mute.execute(ctx.endpoint_id, mute=mute)
        elif ctx.name == "SetVolume":
            volume = require_int(ctx.payload, "volume")
            await self._set_volume.execute(ctx.endpoint_id, level=volume)
        else:  # AdjustVolume
            delta = require_int(ctx.payload, "volume")
            await self._adjust_volume.execute(ctx.endpoint_id, delta=delta)

        muted, volume_level = await self._get_speaker_state.execute(ctx.endpoint_id)
        return [
            build_property("Alexa.Speaker", "muted", muted),
            build_property("Alexa.Speaker", "volume", volume_level),
        ]
