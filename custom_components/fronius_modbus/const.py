"""Constants, SunSpec state maps, and shared value-mapping helpers."""

from collections.abc import Mapping
import re

DOMAIN = "fronius_modbus"
CONNECTION_MODBUS = "modbus"
DEFAULT_NAME = "Fronius"
ENTITY_PREFIX = "fm"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_WEB_SCAN_INTERVAL = 60
MINIMUM_SCAN_INTERVAL = 5
DEFAULT_PORT = 502
DEFAULT_INVERTER_UNIT_ID = 1
DEFAULT_METER_UNIT_ID = 200
DEFAULT_METER_UNIT_IDS = [DEFAULT_METER_UNIT_ID]
DEFAULT_AUTO_ENABLE_MODBUS = True
DEFAULT_RESTRICT_MODBUS_TO_THIS_IP = False
API_USERNAME = "customer"
TECHNICIAN_USERNAME = "technician"
CONF_RECONFIGURE_REQUIRED = "_reconfigure_required"
MIGRATION_RECONFIGURE_ISSUE_ID_PREFIX = "legacy_modbus_only_reconfigure_"
SOLAR_API_LOW_FIRMWARE_ISSUE_ID_PREFIX = "solar_api_low_firmware_"
CONF_INVERTER_UNIT_ID = "inverter_modbus_unit_id"
CONF_METER_UNIT_ID = "meter_modbus_unit_id"
CONF_METER_UNIT_IDS = "meter_modbus_unit_ids"
CONF_API_USERNAME = "api_username"
CONF_API_PASSWORD = "api_password"
CONF_AUTO_ENABLE_MODBUS = "auto_enable_modbus"
CONF_RESTRICT_MODBUS_TO_THIS_IP = "restrict_modbus_to_this_ip"
CONF_WEB_SCAN_INTERVAL = "web_scan_interval"
ATTR_MANUFACTURER = "Fronius"
SUPPORTED_MANUFACTURERS = ["Fronius"]
SUPPORTED_MODELS = ["Primo GEN24", "Symo GEN24", "Verto"]

API_BATTERY_MODE = {
    0: "Auto",
    1: "Manual",
}

API_SOC_MODE = {
    "auto": "Automatic",
    "manual": "Manual",
}

STORAGE_CONTROL_MODE = {
    0: "Auto",
    1: "Charge",
    2: "Discharge",
    3: "Charge and Discharge",
}

CHARGE_STATUS = {
    1: "Off",
    2: "Empty",
    3: "Discharging",
    4: "Charging",
    5: "Full",
    6: "Holding",
    7: "Testing",
}

INVERTER_STATUS = {
    1: "Off",
    2: "Sleeping",
    3: "Starting",
    4: "Normal",
    5: "Throttled",
    6: "Shutdown",
    7: "Fault",
    8: "Standby",
}

INVERTER_CONTROLS = [
    "Power reduction",
    "Constant reactive power",
    "Constant power factor",
]

INVERTER_EVENTS = [
    "Error",
    "Warning",
    "Info",
]

FRONIUS_INVERTER_STATUS = {
    1: "Off",
    2: "Sleeping",
    3: "Starting",
    4: "Normal",
    5: "Throttled",
    6: "Shutdown",
    7: "Fault",
    8: "Standby",
    9: "No solarnet",
    10: "No inverter communication",
    11: "Overcurrent solarnet",
    12: "Firmware updating",
    13: "ACFI event",
}

CHARGE_GRID_STATUS = {
    0: "Disabled",
    1: "Enabled",
}

GRID_STATUS = {
    0: "Off grid",
    1: "Off grid operating",
    2: "On grid",
    3: "On grid operating",
}

CONNECTION_STATUS_CONDENSED = {
    0: "Disconnected",
    1: "Connected",
    3: "Available",
    7: "Operating",
}

ECP_CONNECTION_STATUS = {
    0: "Disconnected",
    1: "Connected",
}

CONTROL_STATUS = {
    0: "Disabled",
    1: "Enabled",
}

AC_LIMIT_STATUS = {
    0: "Disabled",
    1: "Enabled",
}

STORAGE_EXT_CONTROL_MODE = {
    0: "Auto",
    1: "PV Charge Limit",
    2: "Discharge Limit",
    3: "PV Charge and Discharge Limit",
    4: "Charge from Grid",
    5: "Discharge to Grid",
    6: "Block Discharging",
    7: "Block Charging",
}


def _state_values(*mappings: Mapping[int, str]) -> list[str]:
    return list(
        dict.fromkeys(value for mapping in mappings for value in mapping.values())
    )


INVERTER_CONTROL_STATE_VALUES = [
    "Normal",
    "Power reduction",
    "Constant reactive power",
    "Constant power factor",
    "Power reduction,Constant reactive power",
    "Power reduction,Constant power factor",
    "Constant reactive power,Constant power factor",
    "Power reduction,Constant reactive power,Constant power factor",
]


SENSOR_STATE_OPTIONS = {
    "pv_connection": _state_values(CONNECTION_STATUS_CONDENSED),
    "storage_connection": _state_values(CONNECTION_STATUS_CONDENSED),
    "ecp_connection": _state_values(ECP_CONNECTION_STATUS),
    "status": _state_values(INVERTER_STATUS),
    "statusvendor": _state_values(FRONIUS_INVERTER_STATUS),
    "grid_status": _state_values(GRID_STATUS),
    "Conn": _state_values(CONTROL_STATUS),
    "WMaxLim_Ena": _state_values(CONTROL_STATUS),
    "OutPFSet_Ena": _state_values(CONTROL_STATUS),
    "VArPct_Ena": _state_values(CONTROL_STATUS),
    "ac_limit_enable": _state_values(AC_LIMIT_STATUS, {2: "Unknown"}),
    "control_mode": _state_values(STORAGE_CONTROL_MODE) + INVERTER_CONTROL_STATE_VALUES,
    "charge_status": _state_values(CHARGE_STATUS),
    "grid_charging": _state_values(CHARGE_GRID_STATUS),
    "api_modbus_control": _state_values(CONTROL_STATUS),
    "api_modbus_restriction": _state_values(CONTROL_STATUS),
}


_NOT_A_KEY_CHARACTER = re.compile(r"[^a-z0-9]+")


def instance_key(entry_id: str) -> str:
    """The per-entry key every unique id and device identifier is built on since 0.2."""
    return _NOT_A_KEY_CHARACTER.sub("_", entry_id.lower()).strip("_") or "fronius"


def entity_prefix(entry_id: str) -> str:
    """The unique-id/entity-id prefix for one config entry."""
    return f"{ENTITY_PREFIX}_{instance_key(entry_id)}"


def map_code(mapping: dict[int, str], code: int | None) -> str | None:
    """Look up a SunSpec state code, keeping an unmapped one visible instead of hiding it."""
    if code is None:
        return None
    return mapping.get(code, f"Unknown ({code})")


def bitmask_to_string(
    bitmask: int | None, names: list[str], default: str, bits: int = 16
) -> str | None:
    """Render a SunSpec bitfield as its comma-joined set flag names."""
    if bitmask is None:
        return None
    set_names = [
        names[bit] if bit < len(names) else f"bit {bit} undefined"
        for bit in range(bits)
        if bitmask & (1 << bit)
    ]
    return ",".join(set_names) if set_names else default
