"""Shared fixtures: the captured inverter replayed into the in-memory Modbus backend."""

import json
import pathlib

from modbus_connection.mock import MockModbusConnection
import pytest

pytest_plugins = ("pytest_homeassistant_custom_component",)

FIXTURES = pathlib.Path(__file__).with_name("fixtures")
INVERTER_UNIT_ID = 1
METER_UNIT_ID = 200


def load_fixture(name: str) -> dict[int, dict[str, dict[int, int]]]:
    """A captured device as {unit_id: {"holding": {address: word}}}."""
    raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return {
        int(unit_id): {
            space: {int(a): v for a, v in words.items()}
            for space, words in spaces.items()
        }
        for unit_id, spaces in raw.items()
    }


@pytest.fixture
def symo_gen24() -> dict:
    return load_fixture("symo_gen24_fw1386.json")


@pytest.fixture
def connection(symo_gen24) -> MockModbusConnection:
    """A Symo GEN24 10.0 with one Smart Meter on unit 200, in memory."""
    connection = MockModbusConnection()
    for unit_id, spaces in symo_gen24.items():
        connection.for_unit(unit_id).load_raw(spaces)
    return connection


@pytest.fixture
def inverter_unit(connection):
    return connection.for_unit(INVERTER_UNIT_ID)


@pytest.fixture
def meter_unit(connection):
    return connection.for_unit(METER_UNIT_ID)
