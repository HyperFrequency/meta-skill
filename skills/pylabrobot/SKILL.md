---
name: pylabrobot
version: 0.1.0
description: >-
  Hardware-agnostic pure-Python SDK for lab automation. PyLabRobot drives liquid
  handlers, plate readers, heater-shakers, incubators, centrifuges, pumps, and
  scales through one async frontend plus swappable device backends, so the same
  protocol runs on Hamilton STAR/STARlet/Vantage, Opentrons OT-2, Tecan EVO, or a
  no-hardware simulator. Use when writing, simulating, or executing multi-vendor
  automation protocols, laying out a robot deck with typed labware, tracking tips
  and liquid volumes, or coordinating a liquid handler with analytical and
  material-handling instruments. Do NOT use for Opentrons-only protocols where the
  vendor Protocol API is simpler (see `opentrons-integration`), for sample/ELN
  metadata management (`benchling-integration`), or for analyzing assay data after
  a run (use data-analysis skills) — this skill controls physical hardware and its
  simulation, not experiment design or downstream analytics.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (PyLabRobot)"
---

# PyLabRobot

## Overview

PyLabRobot (`pylabrobot`) is a hardware-agnostic, pure-Python SDK for automated
laboratories. It splits every device into a **frontend** (a stable, high-level
Python object like `LiquidHandler` or `PlateReader`) and a **backend** (the
vendor-specific driver that speaks to real hardware). Because the protocol code
only ever touches the frontend, you can develop against a simulator and later
swap in a Hamilton, Opentrons, or Tecan backend without rewriting the protocol.

Three ideas carry almost everything:

- **Frontend/backend split** — write once, run on any supported robot or in
  simulation by changing one constructor argument.
- **Resource tree** — the deck, carriers, plates, wells, and tips form a single
  parent/child tree (an arborescence) with millimetre coordinates and per-item
  state. Everything is addressable (`plate["A1:H1"]`).
- **Async everywhere** — every hardware action is a coroutine. You `await`
  `setup()`, `pick_up_tips()`, `aspirate()`, `read_absorbance()`, and so on, and
  you run the protocol inside an event loop.

Use this SKILL.md as a router. Load the reference file for the subsystem you are
working in.

## When to Use This Skill

- Programming liquid-handling robots (Hamilton STAR/STARlet/Vantage, Opentrons
  OT-2, Tecan EVO) for pipetting, transfers, serial dilutions, or plate stamping.
- Building a deck layout from typed labware (plates, tip racks, troughs, tubes,
  carriers) and tracking tip presence and liquid volumes.
- Driving **multiple vendors or device classes** from one protocol — e.g. a
  liquid handler plus a CLARIOstar plate reader plus a heater-shaker.
- Controlling analytical instruments (plate readers, scales) or material-handling
  gear (heater-shakers, incubators, centrifuges, pumps).
- Simulating and visualizing a protocol in a browser before committing hardware
  time, or running protocol logic in CI with no hardware attached.

## When NOT to Use This Skill

- **Opentrons-only protocols** that will only ever run on an OT-2/Flex — the
  vendor Protocol API is more mature for that single platform; prefer
  `opentrons-integration`.
- **Sample, plasmid, or run metadata** and ELN/LIMS bookkeeping — use
  `benchling-integration` (or a protocols repository skill), not the hardware SDK.
- **Analyzing the numbers a run produced** (dose-response fits, plate-map
  normalization, statistics) — hand the returned arrays to data-analysis skills.
- **Designing the experiment or wet-lab method** itself — PyLabRobot executes a
  procedure you have already decided on; it is not a protocol-design assistant.

## Capability Map

Each subsystem has a dedicated reference with concrete imports, parameters, and
worked protocols. Load the one you need:

| Subsystem | Load when you are… | Reference |
|-----------|--------------------|-----------|
| Liquid handling | pipetting, transferring, diluting, mixing, tip management | [`references/liquid-handling.md`](references/liquid-handling.md) |
| Resources & deck | defining labware, laying out the deck, coordinates, state, serialization, custom labware | [`references/resources.md`](references/resources.md) |
| Hardware backends | connecting to a specific robot, switching platforms, connection troubleshooting | [`references/hardware-backends.md`](references/hardware-backends.md) |
| Analytical equipment | plate readers (CLARIOstar), scales, liquid-handler ↔ reader integration | [`references/analytical-equipment.md`](references/analytical-equipment.md) |
| Material handling | heater-shakers, incubators, centrifuges, pumps, temperature control | [`references/material-handling.md`](references/material-handling.md) |
| Visualization & simulation | browser visualizer, ChatterBox simulator, CI testing, deck editor | [`references/visualization.md`](references/visualization.md) |

## Quick Start

Install with `pip install pylabrobot` (add extras like `pylabrobot[visualizer]`
as needed). Everything runs inside an async context:

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import STAR
from pylabrobot.resources import STARLetDeck

lh = LiquidHandler(backend=STAR(), deck=STARLetDeck())
await lh.setup()          # open the connection / initialize hardware
try:
    await lh.pick_up_tips(tip_rack["A1:H1"])   # one 8-tip column
    await lh.aspirate(plate["A1:H1"], vols=100)  # 100 µL per channel
    await lh.dispense(plate["A2:H2"], vols=100)
    await lh.drop_tips()
finally:
    await lh.stop()       # always release the hardware
```

`aspirate` / `dispense` / `pick_up_tips` / `drop_tips` are the stable primitives.
Higher-level helpers (e.g. a combined transfer, plate stamping) are covered in
[`references/liquid-handling.md`](references/liquid-handling.md); confirm their
exact signatures against your installed version, as the SDK's convenience API
changes between releases.

## Cross-Cutting Essentials

- **Simulate first.** Develop against the ChatterBox simulation backend plus the
  browser visualizer, then change only the backend to go to hardware. See
  [`references/visualization.md`](references/visualization.md).
- **Enable tracking before creating resources.** Call `set_tip_tracking(True)`
  and `set_volume_tracking(True)` *before* instantiating labware so tip presence
  and volumes are enforced and visualized. Tracking set after creation may not
  apply to existing resources.
- **Always pair `setup()`/`stop()`.** Wrap protocols in `try/finally` so the
  connection is released and tips are dropped even on error.
- **Set temperatures early.** Heating and cooling are slow; issue
  `set_temperature(...)` at the start of a protocol, not just before you need it.
- **Persist layouts and state as JSON.** Save the deck (`deck.save(...)`) and its
  state for reproducible, version-controllable protocols.
- **One connection per device.** Only one process may hold a hardware backend at
  a time; close other software (vendor apps) that might hold the port.
- **Pin your version.** Import paths (e.g. simulation and machine backends) and
  helper method names move between releases — pin `pylabrobot==<version>` and
  check <https://docs.pylabrobot.org> when an import fails.

## Version and Platform Notes

PyLabRobot runs on Windows, macOS, Linux, and Raspberry Pi. Backend maturity
varies: Hamilton STAR/STARlet is the most complete, Vantage is mostly supported,
Opentrons OT-2 works over its HTTP API, and Tecan EVO is a work in progress.
Check the current support matrix at
<https://docs.pylabrobot.org/user_guide/machines.html> before relying on a
specific device or feature.

## Further Reading

- Docs: <https://docs.pylabrobot.org>
- Source: <https://github.com/PyLabRobot/pylabrobot>
- Community: <https://discuss.pylabrobot.org>
