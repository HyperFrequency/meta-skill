# SimPy Shared Resources

Shared resources are the congestion points of a model — the things entities queue
for. SimPy groups them into three families:

- **Resources** — a fixed number of interchangeable *slots* (servers, machines).
- **Containers** — a single continuous or bulk *quantity* (fuel, water, cash).
- **Stores** — a collection of discrete *Python objects* (parts, messages, jobs).

All resource operations return **events**. You `yield` the event to block until
the request is satisfied.

---

## 1. Resources (slot-based)

### `Resource` — the basic semaphore

`simpy.Resource(env, capacity=1)` grants up to `capacity` concurrent holders;
extra requesters queue in FIFO order.

```python
import simpy

def worker(env, name, machine):
    with machine.request() as req:      # enqueue
        yield req                       # granted when a slot frees
        print(f'{name} running at {env.now}')
        yield env.timeout(5)            # hold the slot
    # slot released here automatically

env = simpy.Environment()
machine = simpy.Resource(env, capacity=2)
for i in range(3):
    env.process(worker(env, f'W{i}', machine))
env.run()
```

Useful attributes (read-only, handy for monitoring):

- `capacity` — total slots.
- `count` — slots currently in use.
- `queue` — list of pending (not-yet-granted) requests.
- `users` — list of active requests currently holding a slot.

**Always** use the `with resource.request() as req:` context-manager form. It
releases the slot even if the process raises or is interrupted. If you call
`resource.request()` without a context manager you must call
`resource.release(req)` yourself.

### `PriorityResource` — served by priority

`simpy.PriorityResource(env, capacity=1)`. Pass `request(priority=p)`; **lower
numbers are served first**. Priority only reorders the *waiting* queue; it never
evicts an entity that already holds a slot.

```python
env = simpy.Environment()
res = simpy.PriorityResource(env, capacity=1)

def job(env, name, priority):
    with res.request(priority=priority) as req:
        yield req
        print(f'{name} (prio {priority}) at {env.now}')
        yield env.timeout(5)

env.process(job(env, 'routine', priority=10))
env.process(job(env, 'urgent',  priority=1))   # jumps ahead in the queue
env.run()
```

Use for: triage queues, VIP lanes, priority job scheduling.

### `PreemptiveResource` — high priority evicts a holder

`simpy.PreemptiveResource(env, capacity=1)`. A higher-priority request with
`preempt=True` (the default) evicts the lowest-priority current holder, which
receives a `simpy.Interrupt`. The preempted process must handle it.

```python
env = simpy.Environment()
res = simpy.PreemptiveResource(env, capacity=1)

def user(env, name, priority, duration):
    with res.request(priority=priority) as req:
        try:
            yield req
            print(f'{name} acquired at {env.now}')
            yield env.timeout(duration)
            print(f'{name} finished at {env.now}')
        except simpy.Interrupt as interrupt:
            # interrupt.cause is a Preempted namedtuple:
            # .by (the preempting process), .usage_since, .resource
            print(f'{name} PREEMPTED at {env.now} by {interrupt.cause.by}')

env.process(user(env, 'low',  priority=10, duration=10))
env.process(user(env, 'high', priority=1,  duration=5))   # arrives, preempts low
env.run()
```

Use for: CPU scheduling, emergency override, network packet prioritization. Pass
`preempt=False` to get priority ordering without eviction.

---

## 2. Container (bulk quantity)

`simpy.Container(env, capacity=float('inf'), init=0)` models one shared amount of
a homogeneous substance. `put(amount)` blocks while the container would overflow;
`get(amount)` blocks until enough is present.

```python
env = simpy.Environment()
tank = simpy.Container(env, capacity=100, init=50)

def pump(env, tank):
    while True:
        yield env.timeout(5)
        yield tank.put(20)
        print(f'pumped, level={tank.level} at {env.now}')

def draw(env, tank):
    while True:
        yield env.timeout(7)
        yield tank.get(15)
        print(f'drew, level={tank.level} at {env.now}')

env.process(pump(env, tank))
env.process(draw(env, tank))
env.run(until=40)
```

- `level` — current amount.
- `capacity` — max amount (default unbounded).

Use for: fuel tanks, silos, water reservoirs, battery charge, buffer stock,
cash-on-hand.

---

## 3. Stores (discrete objects)

### `Store` — generic FIFO

`simpy.Store(env, capacity=float('inf'))`. `put(item)` blocks when full; `get()`
blocks when empty and returns the oldest item.

```python
env = simpy.Environment()
store = simpy.Store(env, capacity=2)

def producer(env, store):
    for i in range(5):
        yield env.timeout(2)
        yield store.put(f'item{i}')
        print(f'produced item{i} at {env.now}')

def consumer(env, store):
    while True:
        yield env.timeout(3)
        item = yield store.get()
        print(f'consumed {item} at {env.now}')

env.process(producer(env, store))
env.process(consumer(env, store))
env.run()
```

- `items` — list of stored objects.
- `capacity` — max item count (default unbounded).

### `FilterStore` — retrieve by predicate

`simpy.FilterStore(env, capacity=...)`. `get(filter=fn)` returns the oldest item
for which `fn(item)` is truthy, blocking until such an item exists.

```python
env = simpy.Environment()
store = simpy.FilterStore(env, capacity=10)

def producer(env, store):
    for color in ['red', 'blue', 'green', 'red']:
        yield env.timeout(1)
        yield store.put({'color': color, 't': env.now})

def picker(env, store, color):
    while True:
        item = yield store.get(lambda x: x['color'] == color)
        print(f'{color} picker took item from t={item["t"]} at {env.now}')

env.process(producer(env, store))
env.process(picker(env, store, 'red'))
env.run(until=8)
```

Use for: SKU picking, skill-matched job queues, routing by destination. Note the
predicate scan is **O(n)** per `get`; keep such stores small.

### `PriorityStore` — lowest-priority-first retrieval

`simpy.PriorityStore(env, capacity=...)` returns items in priority order. Stored
items must be orderable; wrap payloads in `simpy.PriorityItem(priority, item)` (a
namedtuple whose comparison uses `priority` only) or supply your own class with
`__lt__`.

```python
import simpy
from simpy import PriorityItem

env = simpy.Environment()
store = simpy.PriorityStore(env)

def producer(env, store):
    for prio, name in [(10, 'low'), (1, 'high'), (5, 'mid')]:
        yield env.timeout(1)
        yield store.put(PriorityItem(priority=prio, item=name))

def consumer(env, store):
    while True:
        yield env.timeout(5)
        entry = yield store.get()
        print(f'got {entry.item} (prio {entry.priority}) at {env.now}')

env.process(producer(env, store))
env.process(consumer(env, store))
env.run()
```

Use for: task schedulers, print queues, message prioritization.

---

## Choosing a resource type

| Scenario | Type |
|----------|------|
| Limited interchangeable servers/machines | `Resource` |
| Same, but served by priority | `PriorityResource` |
| Same, but urgent work evicts a holder | `PreemptiveResource` |
| Fuel, water, cash, bulk stock | `Container` |
| Object queue, FIFO | `Store` |
| Object queue, retrieve specific items | `FilterStore` |
| Object queue, retrieve by priority | `PriorityStore` |

## Practical notes

- Set capacities from real constraints; sweep them for capacity planning.
- `FilterStore`/`PriorityStore` retrieval is O(n) — fine for hundreds, costly for
  millions of items.
- Wrap `PreemptiveResource` usage in `try/except simpy.Interrupt`.
- To measure utilization, sample `resource.count / resource.capacity` over time
  (see `monitoring.md`).
