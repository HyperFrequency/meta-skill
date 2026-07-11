# Worked Protocol Templates

Runnable starting points. Each is a complete file — set `robotType`/`apiLevel`,
swap labware and pipette load names for your deck, then `opentrons_simulate` it.
On a Flex, remember to add a trash bin (see `labware-and-pipettes.md`).

## Basic transfer

```python
from opentrons import protocol_api

metadata = {"protocolName": "Basic Transfer", "author": "Name <email@example.com>",
            "description": "Minimal single-transfer skeleton"}
requirements = {"robotType": "Flex", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "D1")
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "D2", label="Source")
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "D3", label="Destination")
    pipette = protocol.load_instrument("p1000_single_flex", "left", tip_racks=[tips])

    protocol.comment("Starting transfer...")
    pipette.transfer(50, source_plate["A1"], dest_plate["B1"], new_tip="always")
    protocol.comment("Done.")
```

## Serial dilution across plate rows

Adds diluent to columns 2–12, seeds column 1 with stock, then walks a 1:2 dilution
across each row, mixing after every step.

```python
from opentrons import protocol_api

metadata = {"protocolName": "Serial Dilution", "author": "Name <email@example.com>",
            "description": "1:2 serial dilution across each row"}
requirements = {"robotType": "Flex", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "D1")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "D2", label="Reservoir")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "D3", label="Dilution")
    p1000 = protocol.load_instrument("p1000_single_flex", "left", tip_racks=[tips])

    diluent = protocol.define_liquid(name="Diluent", description="Buffer", display_color="#B0E0E6")
    stock = protocol.define_liquid(name="Stock", description="Concentrated", display_color="#FF6347")
    reservoir["A1"].load_liquid(liquid=diluent, volume=15000)
    reservoir["A2"].load_liquid(liquid=stock, volume=5000)

    transfer_volume = 100  # µL
    num_dilutions = 11

    # 1) Diluent into columns 2-12 of every row
    for row in plate.rows()[:8]:
        p1000.transfer(transfer_volume, reservoir["A1"], row[1:], new_tip="once")

    # 2) Stock into column 1
    p1000.transfer(transfer_volume * 2, reservoir["A2"],
                  [row[0] for row in plate.rows()[:8]], new_tip="always")

    # 3) Serial dilution left-to-right, mixing after each move
    for row in plate.rows()[:8]:
        p1000.transfer(transfer_volume, row[:num_dilutions], row[1:num_dilutions + 1],
                      mix_after=(3, 50), new_tip="always")
```

## Plate replication (96 -> 96)

```python
from opentrons import protocol_api

metadata = {"protocolName": "Plate Replication", "author": "Name <email@example.com>",
            "description": "Copy every well from source to destination"}
requirements = {"robotType": "Flex", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C1")
    source = protocol.load_labware("corning_96_wellplate_360ul_flat", "D1")
    dest = protocol.load_labware("corning_96_wellplate_360ul_flat", "D2")
    p1000 = protocol.load_instrument("p1000_single_flex", "left", tip_racks=[tips])

    p1000.transfer(100, source.wells(), dest.wells(), new_tip="always")
```

Faster with an 8-channel pipette: load `p1000_multi_flex` and transfer
`source.columns()` to `dest.columns()`, or column-by-column via `source["A1"]`.

## PCR setup with the Thermocycler

Distributes master mix, adds template DNA per well, then runs a full cycling
program. Note the two pipettes are given clearly named variables matching the
instrument they load.

```python
from opentrons import protocol_api

metadata = {"protocolName": "PCR Setup", "author": "Name <email@example.com>",
            "description": "Master mix + template into a PCR plate, then cycle"}
requirements = {"robotType": "Flex", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tc = protocol.load_module("thermocyclerModuleV2")
    pcr_plate = tc.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")

    small_tips = protocol.load_labware("opentrons_flex_96_tiprack_50ul", "C1")
    large_tips = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "C2")
    reagents = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "D1", label="Reagents")

    p50 = protocol.load_instrument("p50_single_flex", "left", tip_racks=[small_tips])
    p1000 = protocol.load_instrument("p1000_single_flex", "right", tip_racks=[large_tips])

    master_mix = protocol.define_liquid(name="Master Mix", description="2x", display_color="#FFB6C1")
    template = protocol.define_liquid(name="Template DNA", description="Samples", display_color="#90EE90")
    reagents["A1"].load_liquid(liquid=master_mix, volume=1000)
    for i in range(8):
        reagents.wells()[i + 1].load_liquid(liquid=template, volume=50)

    num_samples = 8
    reaction_volume = 25  # µL per well

    tc.open_lid()

    # Master mix -> plate (one tip; disposal volume guards against shortfall)
    p1000.distribute(20, reagents["A1"], pcr_plate.wells()[:num_samples],
                    new_tip="once", disposal_volume=10)

    # Template DNA -> each well (fresh tip, mix after)
    for i in range(num_samples):
        p50.transfer(5, reagents.wells()[i + 1], pcr_plate.wells()[i],
                     mix_after=(3, 10), new_tip="always")

    # Cycle
    tc.close_lid()
    tc.set_lid_temperature(105)
    tc.set_block_temperature(95, hold_time_seconds=180, block_max_volume=reaction_volume)

    profile = [
        {"temperature": 95, "hold_time_seconds": 15},  # denature
        {"temperature": 60, "hold_time_seconds": 30},  # anneal
        {"temperature": 72, "hold_time_seconds": 30},  # extend
    ]
    tc.execute_profile(steps=profile, repetitions=35, block_max_volume=reaction_volume)

    tc.set_block_temperature(72, hold_time_minutes=5, block_max_volume=reaction_volume)
    tc.set_block_temperature(4, block_max_volume=reaction_volume)  # hold for storage
    tc.deactivate_lid()
    tc.open_lid()
    protocol.comment("PCR complete.")
```

## Tuning technique

- **Viscous or volatile liquids:** lower `pipette.flow_rate.aspirate/dispense`, add
  `pipette.air_gap(vol)` after aspirating, and `touch_tip` to shed droplets.
- **Precise dispensing into a meniscus:** target `well.bottom(z=...)` or
  `well.top(z=...)` instead of the default clearance.
- **Reagent economy:** `distribute(..., new_tip="once", disposal_volume=N)` for one
  reagent to many wells; `consolidate(...)` to pool many wells into one.
- **Manual steps:** `protocol.pause("Load fresh tips, then resume")` to hand control
  to the operator mid-run; `protocol.delay(minutes=...)` for incubations.
