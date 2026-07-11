# Opentrons Protocol API v2 — Method & Property Reference

Signatures reflect the general PAPIv2 surface. Pin `apiLevel` in your protocol and
confirm exact parameters against the Opentrons docs for that level — some
signatures and defaults shift between API versions.

## ProtocolContext (the `protocol` argument to `run`)

### Loading things onto the deck

| Method | Purpose |
|--------|---------|
| `load_instrument(instrument_name, mount, tip_racks=None, replace=False)` | Load a pipette on `"left"` or `"right"`; returns an `InstrumentContext` |
| `load_labware(load_name, location, label=None, namespace=None, version=None)` | Load labware in a deck slot; returns a `Labware` |
| `load_adapter(load_name, location, namespace=None, version=None)` | Load an adapter; then call `adapter.load_labware(...)` |
| `load_labware_from_definition(definition, location, label=None)` | Load custom labware from a parsed JSON definition |
| `load_module(module_name, location=None, configuration=None)` | Load a hardware module; returns the module's context |
| `load_trash_bin(location)` | Flex only — declare a trash bin (required from API 2.16+) |
| `load_waste_chute()` | Flex only — declare the waste chute for disposal |

### Liquids and execution control

| Method | Purpose |
|--------|---------|
| `define_liquid(name, description=None, display_color=None)` | Define a liquid type; returns a `Liquid` for `well.load_liquid(...)` |
| `pause(msg=None)` | Halt until the operator resumes in the app |
| `resume()` | Resume after a pause |
| `delay(seconds=0, minutes=0, msg=None)` | Wait a fixed time (incubation, settling) |
| `comment(msg)` | Emit a line to the run log |
| `home()` | Home all axes |
| `set_rail_lights(on)` | Toggle deck lights (Flex) |

### Useful properties

`deck`, `loaded_labwares`, `loaded_instruments`, `loaded_modules`, `params`
(runtime parameters), `bundled_data`, `fixed_trash` (OT-2), and `is_simulating()`
(bool — guard robot-only side effects).

## InstrumentContext (a pipette)

### Tips

| Method | Purpose |
|--------|---------|
| `pick_up_tip(location=None, presses=None, increment=None)` | Pick up a tip (auto-advances through `tip_racks` if `location` omitted) |
| `drop_tip(location=None, home_after=True)` | Drop a tip (defaults to trash) |
| `return_tip(home_after=True)` | Return the tip to its original rack slot |
| `reset_tipracks()` | Reset tip-tracking so racks are treated as full again |

### Liquid handling — atomic

| Method | Purpose |
|--------|---------|
| `aspirate(volume=None, location=None, rate=1.0)` | Draw liquid in |
| `dispense(volume=None, location=None, rate=1.0, push_out=None)` | Expel liquid |
| `blow_out(location=None)` | Push out residual liquid + air |
| `mix(repetitions=1, volume=None, location=None, rate=1.0)` | Aspirate/dispense in place |
| `air_gap(volume=None, height=None)` | Trap an air gap below the liquid to prevent dripping |
| `touch_tip(location=None, radius=1.0, v_offset=-1.0, speed=60.0)` | Wick droplets off the tip on the well wall |
| `move_to(location, force_direct=False, minimum_z_height=None, speed=None)` | Move the tip to an explicit location |

### Liquid handling — complex

| Method | Purpose |
|--------|---------|
| `transfer(volume, source, dest, **kwargs)` | One-to-one (or zipped list) moves |
| `distribute(volume, source, dest, **kwargs)` | One source to many destinations |
| `consolidate(volume, source, dest, **kwargs)` | Many sources into one destination |

Shared keyword arguments:

- `new_tip` — `"always"` (default), `"once"`, or `"never"`
- `mix_before` / `mix_after` — `(repetitions, volume)` tuple
- `touch_tip` — `True` to touch tip after each aspirate/dispense
- `blow_out` — `True` to blow out after dispense; pair with `blowout_location`
- `disposal_volume` — extra aspirated volume held back (distribute; prevents shortfall)
- `carryover` — `True` (default) splits volumes larger than the tip across passes
- `trash` — `True` to trash tips vs. return them

### Pipette properties

`channels`, `min_volume`, `max_volume`, `current_volume`, `has_tip`, `name`,
`model`, `mount`, `tip_racks`, `starting_tip`, `default_speed`, and
`flow_rate` (a `FlowRates` object). Set flow rates in µL/s:

```python
pipette.flow_rate.aspirate = 150
pipette.flow_rate.dispense = 300
pipette.flow_rate.blow_out = 400
```

## Labware and Well

**Well access on a `Labware`:** `wells()` (flat list), `wells_by_name()` (dict),
`rows()` / `columns()` (list of lists), `rows_by_name()` / `columns_by_name()`.
Index a single well by name: `plate["A1"]`.

**Locations on a `Well`:**

| Method | Meaning |
|--------|---------|
| `well.top(z=0)` | Point at the top of the well; `z` offsets in mm (negative = below rim) |
| `well.bottom(z=0)` | Point at the bottom; `z` raises above the floor |
| `well.center()` | Geometric center |

**Liquid tracking on a `Well`:** `load_liquid(liquid, volume)` marks a well as
holding a defined liquid (µL); `load_empty()` marks it empty. Useful well
properties: `max_volume`, `depth`, `diameter`, `length`, `width`, `has_tip`.

## Module contexts

### Temperature Module (Gen2)

`set_temperature(celsius)` sets the target and blocks until reached;
`deactivate()` turns it off. Properties: `temperature`, `target`, `status`,
`labware`. Load labware with `temp_module.load_labware(name)`.

### Magnetic Module (Gen2, OT-2 only)

`engage(height_from_base=None, offset=None, height=None)` raises the magnets;
`disengage()` lowers them. Property `status` is `"engaged"`/`"disengaged"`.

### Heater-Shaker Module

| Method | Purpose |
|--------|---------|
| `set_and_wait_for_temperature(celsius)` | Heat and block until reached |
| `set_target_temperature(celsius)` / `wait_for_temperature()` | Non-blocking set + explicit wait |
| `deactivate_heater()` | Stop heating |
| `set_and_wait_for_shake_speed(rpm)` | Shake and block until at speed |
| `deactivate_shaker()` | Stop shaking |
| `open_labware_latch()` / `close_labware_latch()` | Latch control (close before shaking) |

Properties: `temperature`, `target_temperature`, `current_speed`,
`target_speed`, `labware_latch_status`, `labware`.

### Thermocycler Module

| Method | Purpose |
|--------|---------|
| `open_lid()` / `close_lid()` | Lid position |
| `set_lid_temperature(celsius)` | Heat the lid (typ. 105 °C) |
| `deactivate_lid()` | Stop lid heating |
| `set_block_temperature(temperature, hold_time_seconds=0, hold_time_minutes=0, ramp_rate=None, block_max_volume=None)` | Hold the block at one temperature |
| `execute_profile(steps, repetitions, block_max_volume=None)` | Run a cycling program |
| `deactivate_block()` | Stop the block |

A profile step is a dict: `{"temperature": 95, "hold_time_seconds": 30}`.
Properties include `block_temperature`, `lid_temperature`, `lid_position`, `status`.

### Absorbance Plate Reader Module (Flex)

`initialize(mode, wavelengths)` where `mode` is `"single"` or `"multi"`; `read(export_filename=None)`
returns a dict keyed by wavelength; `open_lid()` / `close_lid()`.

## Common exceptions

`OutOfTipsError`, `LabwareNotLoadedError`, `InstrumentNotLoadedError`,
`InvalidContainerError`, `InvalidVolumeError`.

## API-level compatibility (orientation only)

Higher levels are supersets. Notable milestones: Flex support and partial-tip
pickup arrived in the 2.15–2.16 range; the absorbance plate reader around 2.18;
2.19 is a widely used recent level. **Always confirm the feature set for your
pinned level in the current Opentrons docs** rather than trusting this table.
