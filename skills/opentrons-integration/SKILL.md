---
name: opentrons-integration
version: 0.1.0
description: >-
  Write, simulate, and reason about Opentrons Python Protocol API v2 protocols
  for the Flex and OT-2 liquid-handling robots. Use when you need production
  Opentrons protocols with official API compatibility: loading pipettes, labware,
  and deck layouts; basic and complex pipetting (aspirate/dispense, transfer,
  distribute, consolidate, mix, air gap, touch tip); controlling hardware modules
  (temperature, magnetic, heater-shaker, thermocycler, absorbance plate reader);
  liquid tracking; and common patterns like serial dilution, plate replication,
  and PCR setup. Do NOT use for multi-vendor or non-Opentrons instrument control
  (use `pylabrobot`), for capturing results into a LIMS/ELN or registry (use
  `benchling-integration`), or for generic bioinformatics analysis of the data a
  protocol produces (use `biopython`, `anndata`, and related analysis skills).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (Opentrons)"
---

# Opentrons Protocol API Integration

## Overview

Opentrons robots (Flex and OT-2) run automated liquid-handling protocols written
in Python against the **Protocol API v2** (import path `opentrons.protocol_api`).
A protocol is a plain `.py` file: module-level `metadata`/`requirements` dicts
plus a single `run(protocol)` function that issues every command. The robot's app
imports the file, simulates it to build a deck map and command list, then executes
it on hardware.

This skill is a **router**. It gives you the protocol skeleton, a capability map,
and the non-obvious failure modes, then delegates the full method/property tables,
labware and pipette catalogs, and worked templates to `references/`. Reach for it
when the target is specifically Opentrons hardware and you want first-class Protocol
API v2 coverage rather than a vendor-neutral abstraction.

## When to Use This Skill

Trigger when the user wants to:
- Write or debug an Opentrons Protocol API v2 protocol in Python
- Automate pipetting on a **Flex** or **OT-2** (single- or multi-channel)
- Lay out labware, tip racks, adapters, and modules on the deck
- Control hardware modules — temperature, magnetic, heater-shaker, thermocycler,
  or the Flex absorbance plate reader
- Implement complex liquid handling: `transfer`/`distribute`/`consolidate`, mixing,
  air gaps, flow-rate tuning, serial dilution, plate replication, or PCR setup
- Add liquid definitions/tracking for setup validation
- Simulate a protocol before running it on a robot

## When NOT to Use This Skill

- **Non-Opentrons or mixed-vendor automation** — for Hamilton, Tecan, or generic
  multi-vendor instrument control, use `pylabrobot`.
- **Recording results / sample metadata** — writing runs, samples, or measurements
  into a LIMS, ELN, or registry belongs in `benchling-integration`, not the protocol.
- **Analyzing the data a protocol yields** — sequence, imaging, or omics analysis
  goes to `biopython`, `anndata`, `bioimage-analysis`, and similar skills.
- **Generic Python-in-a-notebook orchestration** — the Protocol API is a
  declarative, simulate-then-execute DSL; it is not for arbitrary runtime I/O,
  branching on live measurements, or long-running compute inside `run()`.

## Install and Simulate

```bash
pip install opentrons                 # Protocol API + simulator
opentrons_simulate my_protocol.py     # dry-run, prints the command runlog
```

Always simulate before touching a robot — simulation catches deck collisions,
volume/tip-count errors, and API-version mismatches without wasting reagents.
Programmatic simulation: `from opentrons.simulate import simulate, format_runlog`.

## Protocol Skeleton

```python
from opentrons import protocol_api

metadata = {
    "protocolName": "Example",
    "author": "Name <email@example.com>",
    "description": "What this does",
}

requirements = {"robotType": "Flex", "apiLevel": "2.19"}  # or "OT-2"

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C1")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "D1")
    pipette = protocol.load_instrument("p1000_single_flex", "left", tip_racks=[tips])
    pipette.transfer(100, plate["A1"], plate["B1"], new_tip="always")
```

Pin `apiLevel` in `requirements` (or `metadata` for older protocols) — it fixes the
exact API semantics the robot uses. Every command lives inside `run()`; nothing
executes at import time except the `metadata`/`requirements` declarations.

## Capability Map

| Task | Key calls | Deep reference |
|------|-----------|----------------|
| Load pipettes / labware / modules | `load_instrument`, `load_labware`, `load_adapter`, `load_module` | `references/api-reference.md` |
| Basic liquid handling | `pick_up_tip`, `aspirate`, `dispense`, `blow_out`, `drop_tip` | `references/api-reference.md` |
| Complex liquid handling | `transfer`, `distribute`, `consolidate` (+ `new_tip`, `mix_after`, `touch_tip`, `disposal_volume`) | `references/api-reference.md` |
| Well & location targeting | `wells`, `rows`, `columns`, `well.top/bottom/center` | `references/api-reference.md` |
| Module control | temperature / magnetic / heater-shaker / thermocycler / plate-reader | `references/api-reference.md` |
| Pipette & labware names | Flex/OT-2 pipettes, plates, reservoirs, tip racks, tube racks, adapters | `references/labware-and-pipettes.md` |
| Deck layout & Flex trash | slot conventions, multi-channel, `load_trash_bin` | `references/labware-and-pipettes.md` |
| Worked templates | basic transfer, serial dilution, plate replication, PCR setup | `references/protocol-patterns.md` |

## Core Recipes

**Transfer vs. distribute vs. consolidate** — pick the shape of the movement:

```python
pipette.transfer(100, src["A1"], dst["B1"], new_tip="always")          # 1 -> 1
pipette.distribute(50, res["A1"], [p["A1"], p["A2"], p["A3"]])          # 1 -> many
pipette.consolidate(50, [p["A1"], p["A2"], p["A3"]], res["A1"])         # many -> 1
```

`new_tip` is `"always"` (default, one tip per source→dest), `"once"` (single tip
for the whole call), or `"never"` (you manage tips). Add `mix_after=(reps, vol)`,
`touch_tip=True`, `blow_out=True`, or `disposal_volume=N` as needed.

**Target within a well** to avoid the meniscus or reach the bottom:

```python
pipette.aspirate(100, plate["A1"].bottom(z=2))   # 2 mm above the well floor
pipette.dispense(100, plate["A1"].top(z=-1))     # just below the well rim
```

**Multi-channel** pipettes address a whole column from the top well of that column:

```python
multi = protocol.load_instrument("p1000_multi_flex", "left", tip_racks=[tips])
multi.transfer(100, src["A1"], dst["A1"])        # moves entire column 1 -> column 1
```

**A module in three lines** (thermocycler shown; see the reference for all five):

```python
tc = protocol.load_module("thermocyclerModuleV2")
tc.set_block_temperature(95, hold_time_seconds=30, block_max_volume=25)
tc.execute_profile(steps=[...], repetitions=30, block_max_volume=25)
```

## Failure Modes and Gotchas

- **Flex has no fixed trash.** From API 2.16+, load one explicitly
  (`protocol.load_trash_bin("A3")` or `protocol.load_waste_chute()`) or the first
  `drop_tip` raises. The OT-2 has a fixed trash and needs no such call.
- **Out of tips.** `transfer(..., new_tip="always")` consumes a tip per pair; size
  tip racks to the full run or the protocol aborts mid-way with `OutOfTipsError`.
- **API level changes behavior.** Blow-out volume, tip-pickup, and partial-tip
  semantics differ across `apiLevel`s. Pin it and simulate on that exact level;
  never assume a signature from another version applies. See the compatibility
  notes in `references/api-reference.md`.
- **The magnetic module is OT-2 only.** It does not exist on the Flex; use it only
  in OT-2 protocols and give `engage()` a height in mm from the labware base.
- **Volumes are bounded by the pipette and the well.** A volume below the pipette's
  `min_volume`, above `max_volume`, or above a well's `max_volume` errors. Split
  large transfers (the complex commands auto-carryover) and pick the right pipette.
- **Deck collisions & slot conflicts.** The thermocycler occupies fixed slots
  automatically; overlapping labware or tall-labware clearance issues surface only
  in simulation — run it.
- **`run()` is declarative, not reactive.** You cannot branch on a live reading
  (e.g. plate-reader output) to change later steps within one run; the command list
  is built up front. Use `protocol.pause(msg=...)` for manual intervention points.

## References

- `references/api-reference.md` — full method/property tables for `ProtocolContext`,
  `InstrumentContext` (pipette), `Labware`, `Well`, and every module context
  (temperature, magnetic, heater-shaker, thermocycler, absorbance reader), plus
  common exceptions and API-level compatibility.
- `references/labware-and-pipettes.md` — pipette load names (Flex and OT-2),
  labware API names (plates, reservoirs, tip racks, tube racks, adapters), deck-slot
  conventions, multi-channel notes, and Flex trash/waste handling.
- `references/protocol-patterns.md` — complete, runnable templates: basic transfer,
  serial dilution, plate replication, and PCR setup with the thermocycler, including
  liquid definitions and flow-rate tuning.
