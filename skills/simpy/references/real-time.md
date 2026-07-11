# SimPy Real-Time Simulation

By default a SimPy `Environment` runs *as fast as the CPU allows* — it jumps from
event to event with no delay. A **real-time** environment instead paces the run so
that simulation time tracks wall-clock time. Use it for:

- **Hardware-in-the-loop (HIL)** testing against real sensors/actuators,
- **Human-paced** demos and interactive scenarios,
- **System integration** where the sim must run at true speed.

For analysis and parameter sweeps, keep the standard `Environment` (instant runs);
switch to real-time only when wall-clock pacing is the point.

## `RealtimeEnvironment`

Swap the environment class; the model code (processes, resources, events) is
unchanged.

```python
import simpy.rt

def ticker(env):
    while True:
        print('tick at', env.now)
        yield env.timeout(1)

env = simpy.rt.RealtimeEnvironment(factor=1.0)
env.process(ticker(env))
env.run(until=5)          # takes ~5 real seconds
```

Constructor:

```python
simpy.rt.RealtimeEnvironment(
    initial_time=0,   # starting simulation time
    factor=1.0,       # real seconds per one simulation time unit
    strict=True,      # error if a step overruns its real-time budget
)
```

## The `factor` parameter

`factor` is **real seconds per simulation time unit**. A `yield env.timeout(d)`
pauses for about `d * factor` real seconds.

| `factor` | Meaning |
|----------|---------|
| `1.0` | 1 sim unit = 1 second (human pace, 1:1) |
| `0.1` | 1 sim unit = 0.1 s (10× faster than clock) |
| `0.01`| 1 sim unit = 0.01 s (100× faster; fast hardware) |
| `60`  | 1 sim unit = 1 minute (slow, long-horizon pacing) |

```python
import simpy.rt, time

def timed(env):
    start = time.time()
    yield env.timeout(2)
    print('2 sim units took', round(time.time() - start, 2), 's')

env = simpy.rt.RealtimeEnvironment(factor=0.5)  # 2 units -> ~1 second
env.process(timed(env))
env.run()
```

## Strict mode

`strict` controls what happens when the work done inside a step takes **longer**
than its allotted real-time budget (i.e., your process's own computation between
yields exceeds `delay * factor`).

- **`strict=True`** (default) — raises `RuntimeError` on overrun. Use to *validate*
  that the system keeps up with real time.
- **`strict=False`** — lets the run fall behind without crashing. Use during
  development, or when per-step compute time is unpredictable and lagging is
  acceptable.

```python
import simpy.rt, time

def heavy(env):
    yield env.timeout(1)
    time.sleep(1.5)          # exceeds the 1s budget for the next step

env = simpy.rt.RealtimeEnvironment(factor=1.0, strict=True)
env.process(heavy(env))
try:
    env.run()
except RuntimeError as e:
    print('overran real-time budget:', e)
```

## Hardware-in-the-loop pattern

A control loop that reads a sensor, computes a correction, and writes an actuator
on a fixed real-time cadence. Use `strict=False` so occasional slow I/O does not
abort the loop.

```python
import simpy.rt

def control_loop(env, hw, setpoint):
    while True:
        temp = hw.read_sensor()
        error = setpoint - temp
        hw.write_actuator(error * 0.1)      # simple proportional control
        yield env.timeout(0.5)              # 0.5 s between updates

env = simpy.rt.RealtimeEnvironment(factor=1.0, strict=False)
env.process(control_loop(env, hardware, setpoint=25.0))
env.run(until=5)
```

## Measuring drift

Compare elapsed real time against `env.now * factor` to quantify how well the run
holds its schedule — useful for HIL validation.

```python
import simpy.rt, time

def probe(env, start, factor):
    for _ in range(5):
        yield env.timeout(1)
        real = time.time() - start
        expected = env.now * factor
        print(f'sim={env.now} real={real:.2f}s drift={real-expected:+.3f}s')

start = time.time()
env = simpy.rt.RealtimeEnvironment(factor=1.0, strict=False)
env.process(probe(env, start, 1.0))
env.run()
```

## Guidelines

1. **Develop fast, validate real.** Build and debug with a standard
   `Environment`; switch to `RealtimeEnvironment` only to test timing behavior.
2. **Pick `factor` from constraints** — human interaction `1.0`, fast hardware
   `0.01`, long-horizon pacing `60`.
3. **Keep per-step compute under budget.** Work between yields must finish within
   `delay * factor` real seconds or strict mode will raise.
4. **Wrap strict runs** in `try/except RuntimeError` to handle overruns gracefully.
5. Use `strict=False` when timing guarantees are not critical.

## Limitations

- **Overhead** — real-time pacing is unsuited to very high-frequency events.
- **Single-threaded** — all processes share one time base; no true concurrency.
- **Precision** — bounded by Python's timer resolution and OS scheduling; timing
  accuracy varies by platform.
- **No mixed modes** — an environment is either real-time or not; to run fast and
  real-time work together, split them into separate simulations.
