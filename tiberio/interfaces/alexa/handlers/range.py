"""Alexa.RangeController handler — SetRangeValue / AdjustRangeValue for blind endpoints.

Instance identifier: "Blind.Position" (per spec §5).
"""

from __future__ import annotations

import logging

from tiberio.commands.adjust_range import AdjustRangeCommand
from tiberio.commands.set_range import SetRangeCommand
from tiberio.interfaces.alexa.handlers._base import (
    AlexaHandler,
    DirectiveContext,
    require_int,
)
from tiberio.interfaces.alexa.response_builder import build_property

log = logging.getLogger(__name__)

BLIND_INSTANCE = "Blind.Position"


class RangeHandler(AlexaHandler):
    def __init__(
        self,
        set_range: SetRangeCommand,
        adjust_range: AdjustRangeCommand,
    ) -> None:
        self._set_range = set_range
        self._adjust_range = adjust_range

    async def _execute(self, ctx: DirectiveContext) -> list[dict]:
        if ctx.name == "SetRangeValue":
            range_value = require_int(ctx.payload, "rangeValue")
            await self._set_range.execute(ctx.endpoint_id, percent=range_value)
            result_value = range_value
        else:  # AdjustRangeValue
            delta = require_int(ctx.payload, "rangeValueDelta")
            result_value = await self._adjust_range.execute(
                ctx.endpoint_id, delta=delta
            )

        return [
            build_property(
                "Alexa.RangeController",
                "rangeValue",
                result_value,
                instance=BLIND_INSTANCE,
            )
        ]
