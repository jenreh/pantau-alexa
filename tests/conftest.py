"""Root test configuration: isolate the suite from the developer's local ``.env``.

``Settings`` reads ``.env`` at the project root (see ``settings.py``), which leaks
local values such as ``TIBERIO_SHARED_SECRET`` into the test process. A populated
shared secret activates HMAC request signing on ``/alexa/directive``, so the
contract tests — which send no HMAC headers — fail with 401 unless the developer
manually exports ``TIBERIO_SHARED_SECRET=""``.

Tests construct ``Settings`` with explicit keyword arguments and must never depend
on machine-local secrets. Disabling the ``.env`` source for the whole session makes
``task test`` pass cleanly as-is, regardless of what the local ``.env`` contains.
"""

from __future__ import annotations

from tiberio.config.settings import Settings

# Drop the .env source so no developer-local secret leaks into the suite.
Settings.model_config["env_file"] = None
