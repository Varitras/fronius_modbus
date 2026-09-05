"""The Modbus coordinator turns the device's report into entity data, and fails the right way."""

from datetime import timedelta
from unittest.mock import MagicMock

from modbus_connection import ModbusConnectionError, ModbusTimeoutError
from modbus_connection.model.sunspec import SunSpecMapShiftError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fronius_modbus.const import DOMAIN
from custom_components.fronius_modbus.coordinator import FroniusModbusCoordinator
from custom_components.fronius_modbus.fronius_modbus_api.device import FroniusInverter
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import INVERTER_UNIT_ID, METER_UNIT_ID


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.1"})
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def coordinator(hass, entry, connection):
    device = FroniusInverter(
        connection.for_unit(INVERTER_UNIT_ID),
        INVERTER_UNIT_ID,
        {METER_UNIT_ID: connection.for_unit(METER_UNIT_ID)},
    )
    return FroniusModbusCoordinator(
        hass,
        entry,
        device,
        interval=timedelta(seconds=10),
        primary_meter_unit_id=METER_UNIT_ID,
        meter_locations={METER_UNIT_ID: 0},
    )


async def test_a_poll_yields_report_load_and_grid_status(coordinator):
    poll = await coordinator._async_update_data()
    assert "inverter" in poll.report.updated
    assert poll.load_w == 3105.1  # meter 30 W + inverter 3075.1 W
    assert poll.grid_status == "On grid operating"
    assert (
        coordinator.storage_control is not None
        and coordinator.inverter_controls is not None
    )


async def test_a_dead_link_is_a_failed_update(coordinator, inverter_unit):
    inverter_unit.fail_requests(ModbusConnectionError())
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_failures_are_tolerated_inside_the_write_window(
    coordinator, inverter_unit
):
    first = await coordinator._async_update_data()
    coordinator.data = first
    coordinator.tolerate_failures_until(10**9)
    inverter_unit.fail_requests(ModbusConnectionError())
    assert await coordinator._async_update_data() is first


async def test_three_timeouts_recycle_the_link(coordinator, inverter_unit, connection):
    await coordinator._async_update_data()
    inverter_unit.fail_requests(ModbusTimeoutError())
    for _ in range(3):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    assert connection.connected is False


async def test_a_shifted_map_reloads_the_entry(coordinator, hass, entry, monkeypatch):
    await coordinator._async_update_data()
    reload = MagicMock()
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", reload)

    async def shifted():
        raise SunSpecMapShiftError("moved")

    monkeypatch.setattr(coordinator.device, "async_update", shifted)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    reload.assert_called_once_with(entry.entry_id)
