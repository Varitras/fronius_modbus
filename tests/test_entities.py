"""Entity descriptions read against a real runtime, and the total-sensor behaviour."""

from datetime import timedelta

from modbus_connection import ModbusTimeoutError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fronius_modbus import entities
from custom_components.fronius_modbus.const import DOMAIN
from custom_components.fronius_modbus.coordinator import (
    FroniusModbusCoordinator,
    FroniusRuntimeData,
)
from custom_components.fronius_modbus.fronius_modbus_api.device import FroniusInverter

from .conftest import INVERTER_UNIT_ID, METER_UNIT_ID


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.1"})
    entry.add_to_hass(hass)
    return entry


async def make_runtime(hass, entry, connection) -> FroniusRuntimeData:
    """A FroniusRuntimeData built on a fully-refreshed Modbus coordinator."""
    device = FroniusInverter(
        connection.for_unit(INVERTER_UNIT_ID),
        INVERTER_UNIT_ID,
        {METER_UNIT_ID: connection.for_unit(METER_UNIT_ID)},
    )
    coordinator = FroniusModbusCoordinator(
        hass,
        entry,
        device,
        interval=timedelta(seconds=10),
        primary_meter_unit_id=METER_UNIT_ID,
        meter_locations={METER_UNIT_ID: 0},
    )
    await coordinator.async_refresh()
    return FroniusRuntimeData(
        device=device,
        modbus=coordinator,
        web=None,
        web_control=None,
        meter_locations={METER_UNIT_ID: 0},
        primary_meter_unit_id=METER_UNIT_ID,
    )


@pytest.fixture
async def runtime(hass, entry, connection):
    return await make_runtime(hass, entry, connection)


def _description(descriptions, key):
    return next(d for d in descriptions if d.key == key)


async def test_sensor_descriptions_carry_the_polled_values(runtime):
    descriptions = entities.sensor_descriptions(runtime)
    assert _description(descriptions, "acpower").value_fn(runtime) == 3075.1
    assert _description(descriptions, "meter_200_power").value_fn(runtime) == 30.0
    assert (
        _description(descriptions, "mppt_module_0_dc_power").value_fn(runtime) == 2908.2
    )
    assert not any(d.key.startswith("mppt_module_2_") for d in descriptions)


async def test_a_meter_entity_is_unavailable_after_its_meter_fails(
    hass, entry, runtime, connection
):
    description = _description(entities.sensor_descriptions(runtime), "meter_200_power")
    entity = entities.FroniusEntity(runtime, entry, description)
    entity.hass = hass
    assert entity.available is True

    meter_unit = connection.for_unit(METER_UNIT_ID)
    meter_unit.fail_requests(ModbusTimeoutError())
    await runtime.modbus.async_refresh()

    assert entity.available is False


async def test_a_total_sensor_keeps_its_value_when_a_poll_reports_none(
    hass, entry, runtime
):
    description = _description(entities.sensor_descriptions(runtime), "acenergy")
    sensor = entities.FroniusTotalSensor(runtime, entry, description)
    sensor.hass = hass

    assert sensor.native_value == 33187794.59

    # The description is a frozen dataclass; bypass __setattr__ to swap in a poll that
    # reports no value, the same way a real Modbus timeout on "wh" alone would.
    object.__setattr__(description, "value_fn", lambda r: None)
    assert sensor.native_value == 33187794.59
