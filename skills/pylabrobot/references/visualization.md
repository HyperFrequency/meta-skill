# Visualization and Simulation

PyLabRobot lets you develop and validate a protocol with no hardware attached:
the **simulation backend** executes and checks the protocol logic, and the
**browser visualizer** renders the deck, tips, and liquid levels in real time.
The recommended workflow is to build in simulation, watch it in the visualizer,
then switch only the backend to run on a real robot.

## The visualizer

A local web server that shows a live 3D view of the deck and updates as
operations run. It works with both simulated and physical robots.

```python
from pylabrobot.visualizer import Visualizer

vis = Visualizer()
await vis.start()   # serves at http://localhost:1234 and opens a browser
# ... run protocol ...
await vis.stop()
```

Connect it to a liquid handler before running operations:

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends.simulation import ChatterboxBackend
from pylabrobot.resources import STARLetDeck, set_tip_tracking, set_volume_tracking

set_tip_tracking(True)      # enable BEFORE creating resources
set_volume_tracking(True)

vis = Visualizer()
await vis.start()

lh = LiquidHandler(backend=ChatterboxBackend(num_channels=8), deck=STARLetDeck())
lh.visualizer = vis          # wire the handler to the visualizer
await lh.setup()

# operations now animate live
await lh.pick_up_tips(tip_rack["A1:H1"])
await lh.aspirate(plate["A1:H1"], vols=100)
await lh.dispense(plate["A2:H2"], vols=100)
await lh.drop_tips()
```

For the visualizer to show contents, tracking must be on and initial liquids set:

```python
for well in source_plate.children:
    well.tracker.set_liquids([("sample", 200)])   # (liquid_type, µL)
```

Tip presence animates automatically as you pick up and return tips.

## The simulation backend (ChatterBox)

The chatterbox/simulation backend runs every liquid-handling operation without
hardware, tracking tips and volumes and **validating** actions — it will raise on
an impossible operation (aspirating an empty well, overfilling, exceeding tip
capacity). Use it to catch logic errors before they cost hardware time.

```python
lh = LiquidHandler(backend=ChatterboxBackend(num_channels=8), deck=STARLetDeck())
await lh.setup()
await lh.pick_up_tips(tip_rack["A1"])
await lh.transfer(plate["A1"], plate["A2"], vols=100)
await lh.drop_tips()
assert plate["A2"].tracker.get_volume() == 100
```

The simulator's class name/import has moved across versions (e.g.
`ChatterboxBackend` vs `LiquidHandlerChatterboxBackend`); if the import fails,
inspect `pylabrobot.liquid_handling.backends` for your release.

## Deck layout editor

The visualizer includes a graphical deck editor: drag-and-drop labware onto the
deck, set initial liquids and tip presence, and export the layout as JSON. Load
that JSON in a protocol instead of assigning every resource in code:

```python
from pylabrobot.resources import Deck
deck = Deck.load_from_json_file("my_deck_layout.json")
lh = LiquidHandler(backend=backend, deck=deck)
await lh.setup()
source = deck.get_resource("source")   # resources already placed
```

## Automated testing (CI)

Because the simulator needs no hardware, run protocol tests in CI:

```python
import pytest
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends.simulation import ChatterboxBackend
from pylabrobot.resources import STARLetDeck

@pytest.mark.asyncio
async def test_transfer():
    lh = LiquidHandler(backend=ChatterboxBackend(), deck=STARLetDeck())
    await lh.setup()
    try:
        lh.deck.assign_child_resource(tip_rack, rails=1)
        lh.deck.assign_child_resource(plate, rails=10)
        plate["A1"].tracker.set_liquids([(None, 200)])

        await lh.pick_up_tips(tip_rack["A1"])
        await lh.transfer(plate["A1"], plate["A2"], vols=100)
        await lh.drop_tips()

        assert plate["A1"].tracker.get_volume() == 100
        assert plate["A2"].tracker.get_volume() == 100
    finally:
        await lh.stop()
```

Assert on tracker volumes to lock in expected behaviour, and drive edge cases
(empty-well aspiration, overfill, tip-capacity overruns) to confirm the simulator
rejects them.

## Simulation-or-hardware switch

Gate the backend on an environment variable so one file serves both modes:

```python
import os
if os.getenv("USE_HARDWARE", "false").lower() == "true":
    from pylabrobot.liquid_handling.backends import STAR
    backend, use_vis = STAR(), False
else:
    from pylabrobot.liquid_handling.backends.simulation import ChatterboxBackend
    backend, use_vis = ChatterboxBackend(), True

lh = LiquidHandler(backend=backend, deck=STARLetDeck())
if use_vis:
    vis = Visualizer(); await vis.start(); lh.visualizer = vis
await lh.setup()
# identical protocol body for both modes
```

## Troubleshooting

- **Visualizer not updating** — set `lh.visualizer = vis` before operations,
  enable tracking, confirm `vis.start()` ran, and refresh the browser tab.
- **Tracking not working** — call `set_tip_tracking`/`set_volume_tracking`
  *before* creating resources; tracking enabled afterward may not attach to
  existing labware.
- **Simulation raises unexpectedly** — that is the point: it enforces physical
  validity (no aspirating empty wells, no overfilling). Fix the protocol or set
  correct initial states rather than suppressing the error.

## References

- Using the visualizer: <https://docs.pylabrobot.org/user_guide/using-the-visualizer.html>
- API: <https://docs.pylabrobot.org/api/pylabrobot.visualizer.html>
- Examples: <https://github.com/PyLabRobot/pylabrobot/tree/main/examples>
