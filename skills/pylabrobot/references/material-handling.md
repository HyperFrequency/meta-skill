# Material Handling

PyLabRobot drives environmental and mechanical devices — heater-shakers,
incubators, centrifuges, and pumps — so a protocol can incubate, spin, and pump
without leaving Python. Each device is a frontend + backend with the usual
`setup()` / operate / `stop()` lifecycle, and every action is awaited. Import
paths and method names differ across releases and vendors; confirm against the
docs for your version.

## Heater-shakers

### Hamilton HeaterShaker

```python
from pylabrobot.heating_shaking import HeaterShaker
from pylabrobot.heating_shaking.hamilton import HamiltonHeaterShakerBackend

hs = HeaterShaker(name="hs1", backend=HamiltonHeaterShakerBackend(),
                  size_x=156.0, size_y=156.0, size_z=18.0)
await hs.setup()
```

**Temperature, shaking, plate locking**

```python
await hs.set_temperature(37)        # Celsius
await hs.get_temperature()
await hs.set_temperature(None)      # heating off

await hs.set_shake_rate(300)        # RPM
await hs.set_shake_rate(0)          # stop

await hs.lock_plate()               # clamp before shaking
await hs.unlock_plate()
```

**Incubate-with-shaking pattern**

```python
import asyncio
hs.assign_child_resource(plate, location=(0, 0, 0))
await hs.lock_plate()
await hs.set_temperature(37)
await hs.set_shake_rate(300)
await asyncio.sleep(600)            # 10 min
await hs.set_shake_rate(0)
await hs.set_temperature(None)
await hs.unlock_plate()
```

### Inheco ThermoShake

Same frontend, different backend
(`pylabrobot.heating_shaking.inheco.InhecoThermoShakeBackend`); the temperature,
shake, and lock operations mirror the Hamilton unit.

## Incubators and temperature controllers

Simple temperature control (e.g. Inheco) uses `TemperatureController`:

```python
from pylabrobot.temperature_control import TemperatureController
from pylabrobot.temperature_control.inheco import InhecoBackend

inc = TemperatureController(name="incubator", backend=InhecoBackend(),
                           size_x=156.0, size_y=156.0, size_z=50.0)
await inc.setup()
await inc.set_temperature(37)
await inc.get_temperature()
await inc.set_temperature(None)
```

Automated storage incubators (e.g. Thermo Fisher Cytomat) use an `Incubator`
frontend and expose plate store/retrieve plus environmental setpoints. The exact
method surface (store/retrieve, CO2 control) is device- and version-specific:

```python
from pylabrobot.incubation import Incubator
from pylabrobot.incubation.cytomat_backend import CytomatBackend

inc = Incubator(name="cytomat", backend=CytomatBackend())
await inc.setup()
# storage + environmental methods vary; check the backend docs.
```

## Centrifuges

### Agilent VSpin

```python
from pylabrobot.centrifuge import Centrifuge
from pylabrobot.centrifuge.vspin import VSpinBackend

cf = Centrifuge(name="vspin", backend=VSpinBackend())
await cf.setup()
```

**Door and bucket safety** — always open/unlock before any manual plate handling:

```python
await cf.open_door(); await cf.close_door()
await cf.lock_door(); await cf.unlock_door()
await cf.move_bucket_to_loading()
await cf.move_bucket_to_home()
```

**Spin**

```python
await cf.spin(speed=2000, duration=300)   # RPM, seconds
await cf.stop_spin()
```

Sequence for a run: open → bucket-to-loading → (load) → bucket-to-home → close →
lock → spin → unlock → open → bucket-to-loading → (unload). Method names vary by
version.

## Pumps

### Cole-Parmer Masterflex (peristaltic)

```python
from pylabrobot.pumps import Pump
from pylabrobot.pumps.cole_parmer import ColeParmerMasterflexBackend

pump = Pump(name="masterflex", backend=ColeParmerMasterflexBackend())
await pump.setup()

await pump.run_for_duration(duration=10, speed=50)   # seconds, % of max
await pump.start(speed=50); await pump.stop()         # continuous
```

**Volume-based pumping requires calibration** — the pump only knows time and
speed, so calibrate against a measured volume before trusting `pump_volume`:

```python
await pump.run_for_duration(duration=60, speed=50)
measured_mL = 25.3                                    # weigh or measure
pump.calibrate(duration=60, speed=50, volume=measured_mL)
await pump.pump_volume(volume=10, speed=50)           # mL, after calibration
```

### Agrowtek pump array

For many parallel channels, `PumpArray` runs individual or grouped pumps:

```python
from pylabrobot.pumps import PumpArray
from pylabrobot.pumps.agrowtek import AgrowtekBackend

pa = PumpArray(name="agrowtek", backend=AgrowtekBackend(), num_pumps=8)
await pa.setup()
await pa.run_pump(pump_number=1, duration=10, speed=50)
await pa.run_pumps(pump_numbers=[1, 2, 3], duration=10, speed=50)
```

## Multi-device protocols

Material handling is usually sequential (prepare → pump → incubate → spin →
harvest). Set up every device, guard the run, and tear all of them down:

```python
await lh.setup(); await hs.setup(); await cf.setup(); await pump.setup()
try:
    await lh.pick_up_tips(tip_rack["A1:H1"])
    await lh.transfer(samples["A1:H12"], plate["A1:H12"], vols=100)
    await lh.drop_tips()

    await pump.pump_volume(volume=50, speed=50)

    await hs.lock_plate(); await hs.set_temperature(37); await hs.set_shake_rate(300)
    await asyncio.sleep(600)
    await hs.set_shake_rate(0); await hs.set_temperature(None); await hs.unlock_plate()

    await cf.spin(speed=2000, duration=180)
finally:
    await lh.stop(); await hs.stop(); await cf.stop(); await pump.stop()
```

## Safety and timing

- Unlock/open doors and unlock plates **before** any manual or robotic handling.
- Allow real equilibration time for heating/cooling; set temperatures early.
- Calibrate pumps and temperature controllers on the manufacturer's schedule.
- Handle device errors in `try/finally` so nothing is left spinning or clamped.

## References

- Material handling: <https://docs.pylabrobot.org/user_guide/01_material-handling/>
- Supported machines: <https://docs.pylabrobot.org/user_guide/machines.html>
- API: <https://docs.pylabrobot.org/api/>
