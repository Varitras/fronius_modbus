"""The Fronius Modbus integration.

Entry setup is rebuilt on the shared Modbus connection in the coordinator
work; until then the package only declares its platforms.
"""

from homeassistant.const import Platform

PLATFORMS = [
    Platform.SELECT,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.BUTTON,
]
