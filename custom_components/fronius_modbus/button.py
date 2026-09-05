"""Button platform: every FroniusButtonDescription becomes a FroniusButton."""

from __future__ import annotations

from modbus_connection import ModbusError

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FroniusConfigEntry
from .entities import FroniusButtonDescription, FroniusEntity, button_descriptions


class FroniusButton(FroniusEntity, ButtonEntity):
    """A button that runs its description's press action."""

    entity_description: FroniusButtonDescription

    async def async_press(self) -> None:
        """Run the description's press action, then request a refresh on Modbus writes."""
        try:
            await self.entity_description.press(self._runtime)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except (ModbusError, RuntimeError) as err:
            raise HomeAssistantError(str(err)) from err
        if self.entity_description.source == "modbus":
            await self._runtime.modbus.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FroniusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add every button the current runtime produces."""
    runtime = entry.runtime_data
    async_add_entities(
        FroniusButton(runtime, entry, description)
        for description in button_descriptions(runtime)
    )
