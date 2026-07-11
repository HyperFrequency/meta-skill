# Liquid Handling

The `pylabrobot.liquid_handling` module exposes `LiquidHandler`, the frontend for
every pipetting operation. It talks to hardware through a backend, so the same
protocol code runs on a Hamilton STAR, an Opentrons OT-2, or the simulator.

## Setup and teardown

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import STAR
from pylabrobot.resources import STARLetDeck

lh = LiquidHandler(backend=STAR(), deck=STARLetDeck())
await lh.setup()   # required before any operation
# ... protocol ...
await lh.stop()    # required to release the device
```

Always call `setup()` before operating and `stop()` when done, ideally in a
`try/finally` block so the connection is released on error.

## The primitives

Four coroutines cover most protocols and are stable across releases.

### Tip management

```python
await lh.pick_up_tips(tip_rack["A1"])       # single tip
await lh.pick_up_tips(tip_rack["A1:H1"])    # a column of 8 (multi-channel)
await lh.drop_tips()                         # drop at current/default location
await lh.drop_tips(waste)                    # drop at a specific resource
await lh.return_tips()                       # return to the originating rack
```

The number of tips picked up must match the number of channels you then use to
aspirate/dispense. Enable tip tracking (see below) so PyLabRobot refuses to pick
up an absent tip or use a channel that has none.

### Aspirate and dispense

`vols` accepts a scalar (same volume on every channel) or a list (per-channel
volume). Volumes are in microlitres.

```python
await lh.aspirate(plate["A1"], vols=100)                 # 100 µL, one channel
await lh.aspirate(plate["A1:H1"], vols=100)              # 100 µL x 8 channels
await lh.aspirate(plate["A1:A3"], vols=[100, 150, 200])  # per-well volumes

await lh.dispense(plate["A2"], vols=100)
```

Common optional parameters (support varies by backend): `flow_rate` (µL/s),
`liquid_height` (mm above the well bottom to aim the tip), and
`blow_out_air_volume` (µL of air for a blow-out). Consult the backend's docs for
the full set — not every backend honours every parameter.

### Mixing

Mixing is repeated aspirate/dispense in the same well:

```python
await lh.pick_up_tips(tip_rack["A1"])
for _ in range(5):
    await lh.aspirate(plate["A1"], vols=80)
    await lh.dispense(plate["A1"], vols=80)
await lh.drop_tips()
```

## Higher-level helpers

PyLabRobot ships convenience methods that batch the primitives (a combined
transfer, plate stamping across an 8- or 96-channel head, and similar). Their
names and signatures have changed across versions, so treat the pattern below as
illustrative and verify against your installed release:

```python
# Combines aspirate + dispense; keeps the same tips.
await lh.pick_up_tips(tip_rack["A1:H1"])
await lh.transfer(source_plate["A1:H12"], dest_plate["A1:H12"], vols=100)
await lh.drop_tips()
```

If a helper is missing or its arguments differ, fall back to explicit
aspirate/dispense loops — those are always available.

## Worked patterns

### Serial dilution (2-fold along a row)

```python
await lh.pick_up_tips(tip_rack["A1"])
# Pre-fill diluent into A2..A8, then carry 50 µL down the row, mixing each step.
await lh.aspirate(buffer["A1"], vols=50 * 7)
for well in ["A2", "A3", "A4", "A5", "A6", "A7", "A8"]:
    await lh.dispense(plate[well], vols=50)
await lh.drop_tips()

await lh.pick_up_tips(tip_rack["A2"])
for i in range(7):
    await lh.aspirate(plate[f"A{i+1}"], vols=50)
    await lh.dispense(plate[f"A{i+2}"], vols=50)
    await lh.aspirate(plate[f"A{i+2}"], vols=50)  # mix
    await lh.dispense(plate[f"A{i+2}"], vols=50)
await lh.drop_tips()
```

### Plate replication (column by column, 8-channel)

```python
for col in range(1, 13):
    await lh.pick_up_tips(tip_rack[f"A{col}:H{col}"])
    await lh.aspirate(source_plate[f"A{col}:H{col}"], vols=100)
    await lh.dispense(dest_plate[f"A{col}:H{col}"], vols=100)
    await lh.drop_tips()
```

## Tracking and liquid classes

- **Tip tracking** (`set_tip_tracking(True)`) records which rack positions hold a
  tip and rejects invalid picks. **Volume tracking** (`set_volume_tracking(True)`)
  keeps a running volume per well. Enable both *before* creating resources.
- **Liquid classes** parameterize aspiration/dispense behaviour (flow rates,
  blow-out, retract distances) for a given liquid so viscous or volatile reagents
  pipette accurately. The catalog of built-in classes and the constructor fields
  differ by version; see the resources reference and the official docs.

Volume tracking in practice:

```python
plate["A1"].tracker.set_liquids([(None, 200)])   # (liquid_type, µL)
await lh.aspirate(plate["A1"], vols=100)
plate["A1"].tracker.get_volume()                  # -> 100
```

## Error handling

Wrap the run so tips are dropped and the device is released even on failure:

```python
try:
    await lh.setup()
    await lh.pick_up_tips(tip_rack["A1"])
    await lh.transfer(source["A1"], dest["A1"], vols=100)
    await lh.drop_tips()
except Exception as err:
    print(f"liquid handling failed: {err}")
    try:
        await lh.drop_tips()   # best-effort recovery
    except Exception:
        pass
finally:
    await lh.stop()
```

## Backend differences that affect protocols

- **Hamilton STAR/STARlet** — full support, USB connection, CO-RE tips, rail-based
  deck positioning; no vendor software required.
- **Opentrons OT-2** — driven over the network (`host=` IP); 8-channel and
  single-channel pipettes; simpler, coordinate-based deck.
- **Tecan EVO** — work in progress; verify current capability before relying on
  it.

## References

- Basic guide: <https://docs.pylabrobot.org/user_guide/basic.html>
- API: <https://docs.pylabrobot.org/api/pylabrobot.liquid_handling.html>
- Examples: <https://github.com/PyLabRobot/pylabrobot/tree/main/examples>
