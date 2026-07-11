# Pipettes, Labware, and Deck Layout

Load names are the exact strings passed to `load_instrument`, `load_labware`, and
`load_adapter`. New definitions are published regularly — if a name is rejected,
check the current Opentrons Labware Library rather than guessing.

## Pipette load names

**Flex:**
- `p50_single_flex`, `p1000_single_flex`
- `p50_multi_flex`, `p1000_multi_flex`
- (a 96-channel Flex pipette also exists)

**OT-2 (Gen2):**
- `p20_single_gen2`, `p300_single_gen2`, `p1000_single_gen2`
- `p20_multi_gen2`, `p300_multi_gen2`

Multi-channel pipettes are 8-channel: addressing the top well of a column
(`plate["A1"]`) moves the whole column. The Flex 96-channel pipette addresses an
entire plate at once and supports partial-tip pickup on newer API levels.

## Deck slots

- **Flex:** a 4×3 grid labeled `A1`–`D3` (rows A–D front-to-back, columns 1–3),
  plus a staging-area column and dedicated trash/waste positions.
- **OT-2:** numbered slots `1`–`11` (slot `12` is the fixed trash).

The Thermocycler Module spans fixed slots and is loaded with
`load_module("thermocyclerModuleV2")` — no `location` argument.

## Trash and waste (Flex vs. OT-2)

- **OT-2** has a fixed trash in slot 12; `drop_tip()` works with no setup.
- **Flex (API 2.16+)** has *no* fixed trash. Declare one before dropping tips:
  ```python
  trash = protocol.load_trash_bin("A3")     # or:
  chute = protocol.load_waste_chute()
  ```
  Omitting this makes the first `drop_tip` fail.

## Labware API names (representative)

### Well plates
- `corning_96_wellplate_360ul_flat`
- `nest_96_wellplate_100ul_pcr_full_skirt`
- `nest_96_wellplate_200ul_flat`
- `biorad_96_wellplate_200ul_pcr`
- `appliedbiosystems_384_wellplate_40ul`

### Reservoirs
- `nest_12_reservoir_15ml`
- `nest_1_reservoir_195ml`
- `usascientific_12_reservoir_22ml`

### Tip racks
- **Flex:** `opentrons_flex_96_tiprack_50ul`, `opentrons_flex_96_tiprack_200ul`,
  `opentrons_flex_96_tiprack_1000ul`
- **OT-2:** `opentrons_96_tiprack_20ul`, `opentrons_96_tiprack_300ul`,
  `opentrons_96_tiprack_1000ul`
- Filter variants exist (e.g. `opentrons_flex_96_filtertiprack_200ul`).

### Tube racks
- `opentrons_24_tuberack_nest_1.5ml_snapcap`
- `opentrons_24_tuberack_nest_1.5ml_screwcap`
- `opentrons_15_tuberack_falcon_15ml_conical`
- `opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical`

### Adapters
- `opentrons_flex_96_tiprack_adapter`
- `opentrons_96_deep_well_adapter`
- `opentrons_aluminum_flat_bottom_plate`

Load labware onto an adapter in two steps:

```python
adapter = protocol.load_adapter("opentrons_flex_96_tiprack_adapter", "B1")
tips = adapter.load_labware("opentrons_flex_96_tiprack_200ul")
```

## Tip-count sizing

Each `transfer(..., new_tip="always")` pair, and each `new_tip="always"` iteration
of a loop, consumes one tip (8 tips per pick-up on an 8-channel). Count the pairs
and provision enough racks up front; use `new_tip="once"` when a single tip can
safely service a whole call (e.g. distributing one reagent), which conserves tips.
