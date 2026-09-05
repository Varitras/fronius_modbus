"""FroniusInverter: discovery over the SunSpec chain, and one poll as a report."""

from modbus_connection import (
    GatewayTargetError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection
import pytest

from custom_components.fronius_modbus.fronius_modbus_api.device import (
    REPORT_INVERTER,
    REPORT_MPPT,
    REPORT_STORAGE,
    FroniusInverter,
    meter_report_name,
)
from custom_components.fronius_modbus.fronius_modbus_api.exceptions import (
    NotAFroniusInverter,
)

from .conftest import INVERTER_UNIT_ID, METER_UNIT_ID


@pytest.fixture
def device(connection):
    return FroniusInverter(
        connection.for_unit(INVERTER_UNIT_ID),
        INVERTER_UNIT_ID,
        {METER_UNIT_ID: connection.for_unit(METER_UNIT_ID)},
    )


async def test_probe_returns_the_identity(inverter_unit):
    identity = await FroniusInverter.async_probe(inverter_unit)
    assert (identity.manufacturer, identity.model, identity.version) == (
        "Fronius",
        "Symo GEN24 10.0",
        "1.38.6-1",
    )
    assert identity.address == 1


async def test_probe_rejects_a_device_without_an_inverter_model():
    unit = MockModbusConnection().for_unit(1)
    unit.load_raw({"holding": {40000: 0x5375, 40001: 0x6E53, 40002: 0xFFFF, 40003: 0}})
    with pytest.raises(NotAFroniusInverter):
        await FroniusInverter.async_probe(unit)


async def test_the_first_update_discovers_every_sub_system(device):
    report = await device.async_update()
    assert device.three_phase is True
    assert device.storage is not None and device.mppt is not None
    assert set(report.updated) == {
        "inverter",
        "nameplate",
        "settings",
        "status",
        "controls",
        "mppt",
        "storage",
        meter_report_name(METER_UNIT_ID),
    }
    assert report.failed == {}
    assert device.inverter.w == 3075.1
    assert device.meters[METER_UNIT_ID].phases == 3
    assert device.meters[METER_UNIT_ID].identity.model == "Smart Meter TS 65A-3"


async def test_a_missing_meter_is_absent_not_an_error(connection):
    absent = connection.for_unit(201)
    absent.fail_requests(GatewayTargetError())
    device = FroniusInverter(
        connection.for_unit(INVERTER_UNIT_ID),
        INVERTER_UNIT_ID,
        {METER_UNIT_ID: connection.for_unit(METER_UNIT_ID), 201: absent},
    )
    report = await device.async_update()
    assert 201 not in device.meters
    assert meter_report_name(201) not in report.updated
    assert meter_report_name(201) not in report.failed


async def test_a_meter_that_stops_answering_fails_only_its_own_report(
    device, meter_unit
):
    await device.async_update()
    meter_unit.fail_requests(ModbusTimeoutError())
    report = await device.async_update()
    assert REPORT_INVERTER in report.updated
    assert isinstance(
        report.failed[meter_report_name(METER_UNIT_ID)], ModbusTimeoutError
    )


async def test_an_inverter_without_storage_and_mppt(symo_gen24):
    connection = MockModbusConnection()
    holding = dict(symo_gen24[1]["holding"])
    holding[40253], holding[40254] = 0xFFFF, 0  # chain ends after model 123
    connection.for_unit(1).load_raw({"holding": holding})
    device = FroniusInverter(connection.for_unit(1), 1, {})
    report = await device.async_update()
    assert device.storage is None and device.mppt is None
    assert REPORT_STORAGE not in report.updated and REPORT_MPPT not in report.updated


async def test_a_dead_link_propagates(device, inverter_unit):
    inverter_unit.fail_requests(ModbusConnectionError())
    with pytest.raises(ModbusConnectionError):
        await device.async_update()
    assert device.is_set_up is False


async def test_isolation_resistance_is_reported_in_megaohm(device):
    await device.async_update()
    assert device.isolation_resistance_megaohm == 8.607


async def test_raw_diagnostics_drop_the_serial_number(device):
    await device.async_update()
    raw = await device.async_read_raw()
    assert (
        40052 not in raw[INVERTER_UNIT_ID]["holding"]
        and 40067 not in raw[INVERTER_UNIT_ID]["holding"]
    )
    assert raw[INVERTER_UNIT_ID]["holding"][40002] == 1
