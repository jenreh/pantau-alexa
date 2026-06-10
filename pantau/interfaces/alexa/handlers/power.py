"""Alexa.PowerController handler — TurnOn/TurnOff for channel endpoints."""

from __future__ import annotations

import logging

from pantau.commands.turn_off import TurnOffCommand
from pantau.commands.turn_on import TurnOnCommand
from pantau.interfaces.alexa.handlers._base import AlexaHandler, DirectiveContext
from pantau.interfaces.alexa.response_builder import build_property

log = logging.getLogger(__name__)


class PowerHandler(AlexaHandler):
    def __init__(self, turn_on: TurnOnCommand, turn_off: TurnOffCommand) -> None:
        self._turn_on = turn_on
        self._turn_off = turn_off

    async def _execute(self, ctx: DirectiveContext) -> list[dict]:
        if ctx.name == "TurnOn":
            await self._turn_on.execute(ctx.endpoint_id)
            power_state = "ON"
        else:
            await self._turn_off.execute(ctx.endpoint_id)
            power_state = "OFF"

        return [build_property("Alexa.PowerController", "powerState", power_state)]
