# Hardware Backends

A backend is the vendor-specific driver behind a frontend. `LiquidHandler`
provides the API; the backend talks to the machine. Because protocol code only
calls the frontend, you change robots by swapping the backend (and matching deck)
and leave the protocol untouched.

```python
# identical protocol body for every backend
await lh.pick_up_tips(tip_rack["A1"])
await lh.aspirate(plate["A1"], vols=100)
await lh.dispense(plate["A2"], vols=100)
await lh.drop_tips()
```

Backends subclass `LiquidHandlerBackend` and implement at least `setup()`,
`stop()`, and the device command methods. Import paths for backends shift between
releases — if an import fails, check the version's docs.

## Supported liquid handlers

### Hamilton STAR / STARlet — full support

```python
from pylabrobot.liquid_handling.backends import STAR
from pylabrobot.resources import STARLetDeck, STARDeck

lh = LiquidHandler(backend=STAR(), deck=STARLetDeck())  # STARDeck for full STAR
await lh.setup()
```

- USB connection, direct firmware commands, no Hamilton software needed.
- CO-RE tips; optional 96-channel head; rail/carrier positioning.
- Runs on Windows, macOS, Linux, Raspberry Pi (may need USB permissions on
  macOS/Linux).

### Opentrons OT-2 — supported over HTTP

```python
from pylabrobot.liquid_handling.backends import OpentronsBackend
from pylabrobot.resources import OTDeck

lh = LiquidHandler(backend=OpentronsBackend(host="192.168.1.100"), deck=OTDeck())
await lh.setup()
```

- Network connection to the robot's IP; default API port is 31950.
- 8-channel and single-channel pipettes; coordinate-based deck.
- Uses the older Opentrons HTTP API; some STAR features are unavailable. For
  Opentrons-only work, the vendor Protocol API (`opentrons-integration`) may be a
  better fit.

### Hamilton Vantage — mostly supported

```python
from pylabrobot.liquid_handling.backends import Vantage
from pylabrobot.resources import VantageDeck

lh = LiquidHandler(backend=Vantage(), deck=VantageDeck())
```

Similar to STAR; some advanced features may be limited.

### Tecan EVO — work in progress

Basic commands may exist; verify current capability in the docs before relying on
it.

## Simulation backend (ChatterBox)

The chatterbox/simulation backend runs the full protocol logic with no hardware:
it validates operations, tracks tips and volumes, and feeds the browser
visualizer. Use it for development, teaching, and CI.

```python
from pylabrobot.liquid_handling.backends.simulation import ChatterboxBackend
from pylabrobot.resources import STARLetDeck, set_tip_tracking, set_volume_tracking

set_tip_tracking(True)
set_volume_tracking(True)

lh = LiquidHandler(backend=ChatterboxBackend(num_channels=8), deck=STARLetDeck())
await lh.setup()
# ... protocol ...
plate["A1"].tracker.get_volume()   # inspect simulated state
await lh.stop()
```

The exact class/import for the simulator has changed across versions (names like
`ChatterboxBackend` / `LiquidHandlerChatterboxBackend`). If the import fails,
check `pylabrobot.liquid_handling.backends` for your release.

## Writing backend-agnostic protocols

Select the backend + deck from a single switch so the same protocol targets
simulation or hardware:

```python
def make_lh(robot: str):
    if robot == "star":
        from pylabrobot.liquid_handling.backends import STAR
        from pylabrobot.resources import STARLetDeck
        return LiquidHandler(backend=STAR(), deck=STARLetDeck())
    if robot == "opentrons":
        from pylabrobot.liquid_handling.backends import OpentronsBackend
        from pylabrobot.resources import OTDeck
        return LiquidHandler(backend=OpentronsBackend(host="192.168.1.100"), deck=OTDeck())
    from pylabrobot.liquid_handling.backends.simulation import ChatterboxBackend
    from pylabrobot.resources import STARLetDeck
    return LiquidHandler(backend=ChatterboxBackend(), deck=STARLetDeck())
```

A clean development arc: **develop** on ChatterBox → **inspect** in the visualizer
→ **validate** in simulation with the real deck layout → **deploy** by switching
only the backend.

## Connection troubleshooting

**Hamilton STAR**
- USB cable connected; no other software holding the device.
- Firmware current; on macOS/Linux, ensure USB device permissions.

**Opentrons OT-2**
- Correct IP; robot powered on and reachable (`ping`).
- The Opentrons app is not holding the API.

**General**
- Only one process may own a device at a time.
- `await lh.setup()` is the connection test — read its error message.
- Always `await lh.stop()` to release the hardware.

## References

- Backends: <https://docs.pylabrobot.org/user_guide/backends.html>
- Supported machines: <https://docs.pylabrobot.org/user_guide/machines.html>
- API: <https://docs.pylabrobot.org/api/pylabrobot.liquid_handling.backends.html>
