"""Web control: battery mode rules and the write side effects, with the HTTP client stubbed."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fronius_modbus.const import DOMAIN
from custom_components.fronius_modbus.web_control import FroniusWebControl


class FakeWebClient:
    def __init__(self):
        self.battery = {
            "HYB_EM_MODE": 0,
            "HYB_EM_POWER": 0,
            "BAT_M0_SOC_MODE": "auto",
            "BAT_M0_SOC_MIN": 5,
            "BAT_M0_SOC_MAX": 100,
            "HYB_BACKUP_RESERVED": 5,
            "HYB_BM_CHARGEFROMAC": False,
            "HYB_EVU_CHARGEFROMGRID": False,
        }
        self.calls = []

    def get_inverter_info(self):
        return {"temperature": 41.5}

    def get_modbus_config(self):
        return {
            "slave": {
                "mode": "tcp",
                "sunspecMode": "int+sf",
                "ctr": {"on": True, "restriction": {"on": False, "ip": ""}},
            }
        }

    def get_solar_api_config(self):
        return {"SolarAPIv1Enabled": False}

    def get_storage_info(self):
        return {
            "manufacturer": "BYD",
            "model": "HVS",
            "serial": "S",
            "cell_temperature": 22.0,
        }

    def get_battery_config(self):
        return dict(self.battery)

    def get_export_limit_config(self):
        return {
            "exportLimits": {
                "activePower": {"softLimit": {"enabled": True, "powerLimit": 7000}}
            }
        }

    def set_battery_config(self, mode, power, soc_min=None):
        self.calls.append(("battery", mode, power, soc_min))
        self.battery.update(
            HYB_EM_MODE=mode, BAT_M0_SOC_MODE="manual" if mode else "auto"
        )
        return True

    def set_battery_soc_config(self, soc_min, soc_max, backup):
        self.calls.append(("soc", soc_min, soc_max, backup))
        return True

    def set_battery_charge_sources(self, grid, ac):
        self.calls.append(("sources", grid, ac))
        return True

    def set_solar_api_enabled(self, enabled):
        self.calls.append(("solar", enabled))
        return True

    def reset_modbus_control(self):
        self.calls.append(("reset",))
        return True


@pytest.fixture
def control(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.1"}, title="Fronius")
    entry.add_to_hass(hass)
    events = []
    control = FroniusWebControl(
        hass,
        entry,
        host="192.0.2.1",
        client=FakeWebClient(),
        technician_client=None,
        storage_present=True,
        inverter_firmware="1.38.6-1",
        on_battery_write=lambda: events.append("write"),
    )
    control.events = events
    yield control
    control.shutdown()


async def test_refresh_fills_the_web_data(control):
    data = await control.async_refresh()
    assert data.inverter_temperature == 41.5
    assert (data.modbus_mode, data.modbus_control, data.modbus_restriction) == (
        "TCP",
        "Enabled",
        "Disabled",
    )
    assert data.battery_mode == "Auto" and data.battery_mode_effective == 0
    assert data.export_soft_limit_w == 7000
    assert data.storage_temperature == 22.0


async def test_switching_to_manual_sends_power_and_soc_minimum(control):
    await control.async_refresh()
    await control.set_battery_mode(1)
    assert control._client.calls[-1] == ("battery", 1, 0, 5)
    assert control.battery_mode_is_manual
    assert control.events == ["write"]


async def test_battery_power_needs_manual_mode(control):
    await control.async_refresh()
    with pytest.raises(ValueError, match="Manual"):
        await control.set_battery_power_w(500)


async def test_charge_from_grid_implies_charge_from_ac(control):
    await control.async_refresh()
    await control.set_charge_sources(charge_from_grid=True)
    assert control._client.calls[-1] == ("sources", True, True)
    assert (control.data.charge_from_grid, control.data.charge_from_ac) == (True, True)
