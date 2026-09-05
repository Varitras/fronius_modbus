"""Number platform: every FroniusNumberDescription becomes a FroniusNumber."""

from __future__ import annotations

from modbus_connection import ModbusError

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FroniusConfigEntry
from .entities import FroniusEntity, FroniusNumberDescription, number_descriptions


class FroniusNumber(FroniusEntity, NumberEntity):
    """A number whose value and max are its description's value_fn/max_fn."""

    entity_description: FroniusNumberDescription

    @property
    def native_value(self):
        """The description's value for the current runtime."""
        return self.entity_description.value_fn(self._runtime)

    @property
    def native_max_value(self) -> float:
        """The description's dynamic max, falling back to its static one."""
        dynamic_max = self.entity_description.max_fn(self._runtime)
        return dynamic_max if dynamic_max is not None else super().native_max_value

    async def async_set_native_value(self, value: float) -> None:
        """Write the value through the description's set_fn, then request a refresh."""
        try:
            await self.entity_description.set_fn(self._runtime, value)
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
    """Add every number the current runtime produces."""
    runtime = entry.runtime_data
    async_add_entities(
        FroniusNumber(runtime, entry, description)
        for description in number_descriptions(runtime)
    )
