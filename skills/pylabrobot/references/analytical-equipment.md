# Analytical Equipment

Beyond liquid handling, PyLabRobot drives measurement instruments — plate readers
and scales — so a single protocol can prepare samples and read them. Each
instrument follows the same frontend/backend pattern and the same
`setup()` / operate / `stop()` lifecycle.

## Plate readers

### BMG CLARIOstar (and CLARIOstar Plus)

A microplate reader for absorbance, luminescence, and fluorescence.

**Physical**: IEC power, USB-B to the computer (secured with screws on the
device end), optional RS-232 for stacker units. Communication is a serial link
over FTDI/USB; cross-platform.

```python
from pylabrobot.plate_reading import PlateReader
from pylabrobot.plate_reading.clario_star_backend import CLARIOstarBackend

pr = PlateReader(name="CLARIOstar", backend=CLARIOstarBackend())
await pr.setup()
# ... read ...
await pr.stop()
```

**Tray and temperature**

```python
await pr.open()            # extend the loading tray
# (load a plate, manually or with a robot arm)
await pr.close()

await pr.set_temperature(37)   # Celsius; slow to reach, set early
```

**Reads** — method availability and exact parameters depend on the backend
version; confirm against the docs:

```python
data = await pr.read_absorbance(wavelength=450)                 # nm
data = await pr.read_luminescence()
data = await pr.read_fluorescence(excitation_wavelength=485,
                                  emission_wavelength=535)
```

**Data shape**: reads return array data, typically an 8x12 grid for a 96-well
plate. Wrap it for analysis:

```python
import pandas as pd
df = pd.DataFrame(data, index=list("ABCDEFGH"), columns=range(1, 13))
```

Some CLARIOstar features (spectral scanning, injectors, per-well patterns,
detailed parameter configuration) may be under development — verify support
before designing an assay around them.

### Integrating a reader with a liquid handler

The two devices are independent objects; you set up both, prepare on the handler,
move the plate (by robot arm or a prompted manual step), and read:

```python
lh = LiquidHandler(backend=STAR(), deck=STARLetDeck())
pr = PlateReader(name="CLARIOstar", backend=CLARIOstarBackend())
await lh.setup(); await pr.setup()
await pr.set_temperature(37)   # start heating up front

try:
    await lh.pick_up_tips(tip_rack["A1:H1"])
    await lh.transfer(reagent_plate["A1:H12"], assay_plate["A1:H12"], vols=100)
    await lh.drop_tips()

    input("Move assay plate to the reader, then press Enter...")
    await pr.open(); input("Plate loaded? Enter..."); await pr.close()
    data = await pr.read_absorbance(wavelength=450)
finally:
    await lh.stop(); await pr.stop()
```

### Kinetic reads

Loop reads on an interval and timestamp each frame:

```python
import asyncio, time
frames = []
await pr.set_temperature(37); await pr.close()
for i in range(20):                       # 20 reads
    frames.append({"i": i, "t": time.time(),
                   "data": await pr.read_absorbance(wavelength=450)})
    if i < 19:
        await asyncio.sleep(30)           # every 30 s
```

## Scales

### Mettler Toledo

```python
from pylabrobot.scales import Scale
from pylabrobot.scales.mettler_toledo_backend import MettlerToledoBackend

scale = Scale(name="analytical_scale", backend=MettlerToledoBackend())
await scale.setup()

await scale.tare()
grams = await scale.get_weight()    # grams
```

**Gravimetric volume check** — weigh a dispense to validate delivered volume
(for water, 1 g ≈ 1 mL; use the reagent's density otherwise):

```python
await scale.tare()
await lh.dispense(container, vols=1000)   # 1 mL
grams = await scale.get_weight()
microlitres = grams * 1000                # water approximation
```

## Multi-device workflows

Set up every device at the start, coordinate operations, and tear all of them
down in a `finally`:

```python
await lh.setup(); await pr.setup(); await scale.setup()
try:
    await scale.tare()
    reagent_g = await scale.get_weight()

    await lh.pick_up_tips(tip_rack["A1:H1"])
    await lh.transfer(source["A1:H12"], dest["A1:H12"], vols=100)
    await lh.drop_tips()

    await pr.open(); await pr.close()
    absorbance = await pr.read_absorbance(wavelength=450)
finally:
    await lh.stop(); await pr.stop(); await scale.stop()
```

## Practical notes

- Set reader/incubator temperatures early — equilibration is slow.
- Seat the plate fully before `close()`.
- Save raw arrays with metadata (timestamp, wavelength, temperature) for
  reproducibility; hand the numbers to data-analysis skills for fitting and
  normalization — PyLabRobot acquires, it does not analyze.
- Flow cytometers and additional spectrophotometers may have partial or
  in-development support; check the machines page.

## References

- Analytical guide: <https://docs.pylabrobot.org/user_guide/02_analytical/>
- CLARIOstar: <https://docs.pylabrobot.org/user_guide/02_analytical/plate-reading/bmg-clariostar.html>
- API: <https://docs.pylabrobot.org/api/pylabrobot.plate_reading.html>
