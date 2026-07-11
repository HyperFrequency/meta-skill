# SimPy Monitoring and Data Collection

A simulation is only as useful as the numbers you pull out of it. Decide up front
**what** to record (wait times, queue length, utilization, levels), **when** to
record it (on each change, at fixed intervals, or on specific events), and **where**
to keep it (in-memory lists, then CSV/DataFrame for analysis).

Keep monitoring code separate from model logic, and confirm it does not alter the
simulation's behavior.

---

## 1. Record inside processes

The simplest approach: append timestamped records from within a process.

```python
import simpy

def customer(env, name, service_time, log):
    arrival = env.now
    log.append(('arrival', name, arrival))
    yield env.timeout(service_time)
    log.append(('departure', name, env.now))
    log.append(('wait', name, env.now - arrival))

env = simpy.Environment()
log = []
env.process(customer(env, 'C1', 5, log))
env.process(customer(env, 'C2', 3, log))
env.run()
for row in log:
    print(row)
```

## 2. Sample system state at intervals

A dedicated monitor process snapshots shared state on a fixed cadence — good for
time-series of queue length and utilization.

```python
def monitor(env, state, log, interval):
    while True:
        log.append((env.now, state['queue'], state['util']))
        yield env.timeout(interval)
```

For a `Resource`, sample its live attributes directly:

```python
def resource_sampler(env, resource, log, interval):
    while True:
        util = resource.count / resource.capacity
        log.append((env.now, len(resource.queue), util))
        yield env.timeout(interval)
```

Interval sampling gives **time-average** utilization; per-event logging (below)
gives exact transition points. Choose based on whether you need averages or the
full trace.

## 3. Instrument a resource by subclassing

Override `request`/`release` to log on every acquisition and release. This is the
cleanest reusable pattern — the model uses it like a normal `Resource`.

```python
import simpy

class MonitoredResource(simpy.Resource):
    def __init__(self, env, capacity):
        super().__init__(env, capacity)
        self.log = []                       # (event, time, queue_len, util)

    def _snap(self, kind):
        self.log.append((kind, self._env.now,
                         len(self.queue), self.count / self.capacity))

    def request(self, *a, **kw):
        req = super().request(*a, **kw)
        self._snap('request')
        return req

    def release(self, *a, **kw):
        res = super().release(*a, **kw)
        self._snap('release')
        return res

    def average_utilization(self):
        utils = [u for *_, u in self.log]
        return sum(utils) / len(utils) if utils else 0.0
```

Use it exactly like `simpy.Resource(env, capacity=2)`; call
`resource.average_utilization()` after `env.run()`.

The same override pattern works for a `Container` — record `(env.now, self.level)`
in overridden `put`/`get` to reconstruct a level history.

## 4. Collect summary statistics

Accumulate into a small stats object and compute averages at the end. Prefer
storing raw observations and reducing afterward (lazy evaluation) over maintaining
running aggregates you might get wrong.

```python
class QueueStats:
    def __init__(self):
        self.waits = []
        self.queue_lengths = []
    def on_arrival(self, queue_len):
        self.queue_lengths.append(queue_len)
    def on_service(self, wait):
        self.waits.append(wait)
    def mean_wait(self):
        return sum(self.waits) / len(self.waits) if self.waits else 0.0

def customer(env, resource, stats):
    arrival = env.now
    stats.on_arrival(len(resource.queue))
    with resource.request() as req:
        yield req
        stats.on_service(env.now - arrival)
        yield env.timeout(2)
```

## 5. Warm-up and replication

Two statistical habits that matter more than any logging trick:

- **Warm-up**: early observations reflect an empty, unrepresentative system.
  Discard records before a warm-up time (e.g., ignore `env.now < warmup`) when
  computing steady-state metrics.
- **Replication**: one run is a single random sample. Wrap the build-and-run in a
  function, loop over seeds, and average the summary metrics with a confidence
  interval. Reproduce any single run by fixing `random.seed()`.

```python
import random

def run_once(seed, sim_time):
    random.seed(seed)
    env = simpy.Environment()
    stats = QueueStats()
    resource = simpy.Resource(env, capacity=2)
    # ... start arrival generator wired to stats ...
    env.run(until=sim_time)
    return stats.mean_wait()

means = [run_once(s, 1000) for s in range(20)]
print('mean wait:', sum(means) / len(means))
```

## 6. Export and analyze

Dump records to CSV, then analyze with the `polars`, `statistical-analysis`,
`matplotlib`, or `seaborn` skills.

```python
import csv

def export_csv(rows, path, header):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
```

## Guidelines

1. Minimize overhead — log only what a metric needs; heavy logging slows runs.
2. Timestamp every record with `env.now`.
3. For long runs, aggregate or periodically flush to disk instead of holding
   everything in memory.
4. Verify monitoring is passive: results must match with logging on and off.
5. Reduce raw observations to statistics after the run, not during.
6. Compute utilization as `count / capacity`; sample it over time for a time-average.
