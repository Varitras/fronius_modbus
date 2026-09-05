"""The config flow, with the web client stubbed and Modbus served by the mock connection."""

from modbus_connection import ModbusConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import fronius_modbus
from custom_components.fronius_modbus import config_flow
from custom_components.fronius_modbus.const import DOMAIN
from homeassistant.data_entry_flow import FlowResultType

from .conftest import INVERTER_UNIT_ID

HOST = "192.0.2.10"
USER_INPUT = {"host": HOST, "scan_interval": 10, "restrict_modbus_to_this_ip": False}


@pytest.fixture(autouse=True)
def _custom_integration(enable_custom_integrations):
    return enable_custom_integrations


@pytest.fixture(autouse=True)
def _stub_web_client(monkeypatch):
    """The web API is not what this flow test is about: login and token minting succeed."""
    monkeypatch.setattr(config_flow.FroniusWebClient, "login", lambda self: True)
    monkeypatch.setattr(
        config_flow.FroniusWebClient, "ensure_modbus_enabled", lambda self, *a: True
    )
    monkeypatch.setattr(
        config_flow,
        "mint_token",
        lambda host, user, password: {"realm": "r", "token": "t"},
    )

    # A created entry is set up right away; that path is what test_e2e covers, and
    # letting it run here would take the stubbed web client onto the real network.
    async def _skip_setup(hass, entry):
        return True

    monkeypatch.setattr(fronius_modbus, "async_setup_entry", _skip_setup)


async def run_flow(hass) -> dict:
    """Walk the user step and the password step it asks for."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["step_id"] == "user_password"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_password": "secret", "technician_password": ""}
    )


async def test_the_config_flow_creates_an_entry(hass, mock_modbus):
    result = await run_flow(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Fronius 192.0.2.10"
    assert result["data"]["host"] == HOST


async def test_a_second_flow_for_the_same_host_aborts(hass, mock_modbus):
    MockConfigEntry(domain=DOMAIN, data={"host": HOST}, unique_id=HOST).add_to_hass(
        hass
    )

    result = await run_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_an_unreachable_inverter_shows_cannot_connect(hass, mock_modbus):
    mock_modbus.fail_requests(INVERTER_UNIT_ID, ModbusConnectionError())

    result = await run_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
