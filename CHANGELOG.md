# Changelog

## 1.0.0

### Breaking
- **Enum states are now translation keys.** Every select option and every enumerated sensor state changed from an English display text to a lowercase key (shown translated in the UI): `Auto` → `auto`, `PV Charge Limit` → `pv_charge_limit`, `Charge from Grid` → `charge_from_grid`, `Block Discharging` → `block_discharging`, `Enabled`/`Disabled` → `enabled`/`disabled`, `On grid operating` → `on_grid_operating`, `Off grid` → `off_grid`, `Normal` → `normal`, `Throttled` → `throttled`, `Charge and Discharge` → `charge_and_discharge`, `Power reduction,Constant power factor` → `power_reduction_constant_power_factor`, and so on — the rule is lowercase with every non-alphanumeric run replaced by `_`. Automations, templates and dashboards that compare against the old texts (`is_state(..., "Auto")`, `select_option: "Charge from Grid"`) must use the new keys. An unmapped device code now reads `unknown` instead of `Unknown (<code>)`. Reason: hassfest only validates translation keys of the form `[a-z0-9-_]+`, so the German state texts could not be shipped otherwise.

- Minimum supported Home Assistant version is now 2026.9.0.
- The integration now requires Home Assistant's built-in `modbus` integration and connects through it via `async_get_unit` instead of opening its own Modbus TCP connection.

### Changed
- Entity translation keys derived from the 0.3 data keys (`A`, `AphA`, `Conn`, `WHRtg`, ...) are renamed to lowercase names so hassfest validates the translations; unique ids and existing entity ids are unaffected.
- A storage mode change writes the rate that rises first, so a transition such as Charge from Grid to Block Charging no longer leaves both rates at zero for an instant (refused by the firmware with exception 3, upstream #126).

- The register map is discovered at runtime via SunSpec model walking through the `modbus-connection` library (models 1, 101/103, 120, 121, 122, 123, 124, 160, 201-204) instead of a fixed, hand-written register list. Storage entities are present if and only if model 124 is in the chain; meter phase count is derived from the meter model id.
- The Web API is polled on its own interval instead of once per Modbus poll, so a slow or unreachable Web API no longer stalls the Modbus poll or blocks the Modbus entities.
- A firmware update that shifts the inverter's SunSpec model chain now reloads the config entry automatically.
- Grid charge power now scales by the charge maximum and grid discharge power by the discharge maximum. 0.3 wrote each of them against the opposite register's maximum while displaying it with this one, so a written watt value and the value shown back differed whenever the two maxima did.
- The storage energy rating sensor no longer claims the measurement state class.
- The battery API mode now follows `HYB_EM_MODE` alone; a `manual` SoC mode no longer hides the mode as unknown.

### Added

- New option: "Web API update interval (seconds)" (default 60).
- Diagnostics download now includes the raw SunSpec register map, with serial numbers redacted.

### Removed

- The hand-written pymodbus client and its pymodbus version check.
- Per-value plausibility bounds; SunSpec sentinel values and scale factors are now decoded by `modbus-connection`.
