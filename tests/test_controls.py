"""AC limit and power factor writes with the enable pulse the inverter needs to apply a new value."""

from modbus_connection.model.sunspec import scan
import pytest

from custom_components.fronius_modbus.fronius_modbus_api.controls import (
    APPLY_MASK_SECONDS,
    InverterControls,
)
from custom_components.fronius_modbus.fronius_modbus_api.sunspec_models import (
    CONTROLS_MODEL_ID,
    Controls,
)

CONTROLS_HEADER = 40227
CONN = CONTROLS_HEADER + 4
W_MAX_LIM_PCT = CONTROLS_HEADER + 5
W_MAX_LIM_ENA = CONTROLS_HEADER + 9
OUT_PF_SET = CONTROLS_HEADER + 10
OUT_PF_SET_ENA = CONTROLS_HEADER + 14


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def monotonic(self):
        return self.now

    async def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
async def controls(inverter_unit, clock):
    chain = await scan(inverter_unit, 40000)
    component = Controls(inverter_unit, chain.first(CONTROLS_MODEL_ID))
    await component.async_update()
    return InverterControls(
        component, max_power_w=10000, monotonic=clock.monotonic, sleep=clock.sleep
    )


@pytest.fixture
def writes(inverter_unit):
    events = []
    inverter_unit.on_write(events.append)
    return events


def _at(events, address):
    return [(i, e.values[0]) for i, e in enumerate(events) if e.address == address]


async def test_ac_limit_in_watts_becomes_percent_of_max_power(controls, writes):
    await controls.set_ac_limit_w(2500)
    assert [w for _, w in _at(writes, W_MAX_LIM_PCT)] == [2500]  # 25.00 % with SF -2
    assert controls.ac_limit_w == 2500


async def test_an_enabled_limit_is_pulsed_off_and_on_around_the_write(
    controls, writes, inverter_unit, clock
):
    inverter_unit.holding[W_MAX_LIM_ENA] = 1
    await controls.set_ac_limit_w(5000)
    order = sorted(_at(writes, W_MAX_LIM_ENA) + _at(writes, W_MAX_LIM_PCT))
    assert [w for _, w in order] == [0, 5000, 1]
    assert clock.slept == [1.0]
    assert controls.ac_limit_enabled is True
    clock.now += APPLY_MASK_SECONDS + 1
    inverter_unit.holding[W_MAX_LIM_ENA] = 0
    await controls._controls.async_update()
    assert controls.ac_limit_enabled is False


async def test_a_power_factor_outside_the_unit_range_is_refused(controls):
    with pytest.raises(ValueError):
        await controls.set_power_factor(1.5)


async def test_power_factor_is_written_scaled(controls, writes):
    await controls.set_power_factor(-0.95)
    assert [w for _, w in _at(writes, OUT_PF_SET)] == [(-950) & 0xFFFF]


async def test_connection_control(controls, writes):
    await controls.set_connected(False)
    assert [w for _, w in _at(writes, CONN)] == [0]
