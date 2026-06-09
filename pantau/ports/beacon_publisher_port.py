"""Port: S3 beacon publisher — publishes current server address to S3."""

from __future__ import annotations

from typing import Protocol


class BeaconPublisherPort(Protocol):
    """Writes the home server's current public base URL to the S3 beacon object."""

    async def publish(self, base_url: str) -> None:
        """Write { base_url, updated_at, health } to S3 endpoint.json."""
        ...
