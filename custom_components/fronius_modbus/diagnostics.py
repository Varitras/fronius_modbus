"""Diagnostics: the identity, the last poll's outcome, and every raw register."""

from __future__ import annotations

import dataclasses
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import FroniusConfigEntry

REDACTED = "**REDACTED**"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FroniusConfigEntry
) -> dict[str, Any]:
    """Everything a bug report needs about one entry, minus the serial numbers."""
    del hass
    runtime = entry.runtime_data
    poll = runtime.modbus.data
    raw = await runtime.device.async_read_raw()
    web_data = runtime.web_data
    return {
        "identity": runtime.device.identity._replace(serial=REDACTED)._asdict(),
        "updated": sorted(poll.report.updated),
        "failed": {name: str(err) for name, err in poll.report.failed.items()},
        "registers": {
            str(unit_id): {
                space: {str(address): word for address, word in words.items()}
                for space, words in spaces.items()
            }
            for unit_id, spaces in raw.items()
        },
        "web": None
        if web_data is None
        else dataclasses.asdict(web_data)
        | {"storage_serial": REDACTED, "modbus_restriction_ip": REDACTED},
    }
