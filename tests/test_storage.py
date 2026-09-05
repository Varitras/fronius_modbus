"""The storage mode automaton and its write sequences, watched through the mock's write events."""

from modbus_connection.model.sunspec import scan
import pytest

from custom_components.fronius_modbus.fronius_modbus_api.storage import (
    ExtendedMode,
    StorageControl,
)
from custom_components.fronius_modbus.fronius_modbus_api.sunspec_models import (
    STORAGE_MODEL_ID,
    Storage,
)

STORAGE_HEADER = 40343
STOR_CTL_MOD = STORAGE_HEADER + 5
MIN_RSV_PCT = STORAGE_HEADER + 7
OUT_W_RTE = STORAGE_HEADER + 12
IN_W_RTE = STORAGE_HEADER + 13


@pytest.fixture
async def control(inverter_unit):
    chain = await scan(inverter_unit, 40000)
    storage = Storage(inverter_unit, chain.first(STORAGE_MODEL_ID))
    await storage.async_update()
    control = StorageControl(
        storage, max_charge_rate_w=10240, max_discharge_rate_w=10240
    )
    control.sync_from_device()
    return control


@pytest.fixture
def writes(inverter_unit):
    events = []
    inverter_unit.on_write(events.append)
    return events


def _words(events, address):
    return [event.values[0] for event in events if event.address == address]


async def test_auto_on_the_device_reads_as_auto(control):
    assert control.extended_mode is ExtendedMode.AUTO
    assert control.control_mode == 0
    assert (control.charge_limit_pct, control.discharge_limit_pct) == (100.0, 100.0)
    assert (control.grid_charge_power_pct, control.grid_discharge_power_pct) == (
        0.0,
        0.0,
    )
    assert control.soc_minimum == 5


@pytest.mark.parametrize(
    ("stor_ctl_mod", "out_w_rte", "in_w_rte", "expected"),
    [
        (1, 10000, 0, ExtendedMode.BLOCK_CHARGING),
        (1, 10000, 10000, ExtendedMode.PV_CHARGE_LIMIT),
        (2, -3000 & 0xFFFF, 10000, ExtendedMode.CHARGE_FROM_GRID),
        (2, 10000, -3000 & 0xFFFF, ExtendedMode.DISCHARGE_TO_GRID),
        (3, 0, 10000, ExtendedMode.BLOCK_DISCHARGING),
        (2, 10000, 10000, ExtendedMode.DISCHARGE_LIMIT),
        (3, 10000, 10000, ExtendedMode.CHARGE_AND_DISCHARGE_LIMIT),
    ],
)
async def test_the_extended_mode_is_derived_from_the_registers(
    inverter_unit, stor_ctl_mod, out_w_rte, in_w_rte, expected
):
    inverter_unit.holding[STOR_CTL_MOD] = stor_ctl_mod
    inverter_unit.holding[OUT_W_RTE] = out_w_rte
    inverter_unit.holding[IN_W_RTE] = in_w_rte
    chain = await scan(inverter_unit, 40000)
    storage = Storage(inverter_unit, chain.first(STORAGE_MODEL_ID))
    await storage.async_update()
    control = StorageControl(
        storage, max_charge_rate_w=10240, max_discharge_rate_w=10240
    )
    control.sync_from_device()
    assert control.extended_mode is expected


async def test_charge_from_grid_writes_mode_then_rates(control, writes):
    await control.set_mode(ExtendedMode.CHARGE_FROM_GRID)
    assert _words(writes, STOR_CTL_MOD) == [2]
    assert _words(writes, IN_W_RTE) == [10000]
    assert _words(writes, OUT_W_RTE) == [0]
    assert control.extended_mode is ExtendedMode.CHARGE_FROM_GRID


async def test_grid_charge_power_is_a_negative_discharge_rate(control, writes):
    await control.set_mode(ExtendedMode.CHARGE_FROM_GRID)
    await control.set_grid_charge_power_w(2560)
    assert _words(writes, OUT_W_RTE)[-1] == (-2500) & 0xFFFF
    assert control.grid_charge_power_pct == 25.0


async def test_a_limit_is_refused_outside_its_mode(control):
    with pytest.raises(ValueError, match="Charge limit cannot be changed"):
        await control.set_charge_limit_w(5000)


async def test_a_rate_above_the_maximum_is_clamped_to_100_percent(control, writes):
    await control.set_mode(ExtendedMode.PV_CHARGE_LIMIT)
    await control.set_charge_limit_w(99999)
    assert _words(writes, IN_W_RTE)[-1] == 10000


async def test_minimum_reserve_is_written_as_whole_percent(control, writes):
    await control.set_minimum_reserve(7)
    assert _words(writes, MIN_RSV_PCT) == [700]
    with pytest.raises(ValueError):
        await control.set_minimum_reserve(4)
