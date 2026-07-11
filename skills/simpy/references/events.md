# SimPy Events

Everything a process waits on is an **event**. The Environment holds an ordered
queue of scheduled events; each `yield` in a process registers the process to be
resumed when the yielded event is processed. Understanding the event lifecycle
lets you build coordination beyond timeouts and resource requests.

## Event lifecycle

An event moves through three states:

1. **untriggered** — a plain object, not yet in the queue.
2. **triggered** — scheduled; `event.triggered` is `True`. It carries an outcome
   (a value on success, an exception on failure).
3. **processed** — dequeued and its callbacks fired; `event.processed` is `True`.
   `event.value` now holds the result.

```python
import simpy
env = simpy.Environment()

evt = env.event()
print(evt.triggered, evt.processed)   # False False
evt.succeed(value='result')
print(evt.triggered, evt.processed)   # True  False
env.run()
print(evt.triggered, evt.processed)   # True  True
print(evt.value)                      # 'result'
```

## Core event types

### `timeout` — advance time

The most common event. `env.timeout(delay, value=None)` fires `delay` time units
later, optionally carrying a value.

```python
def proc(env):
    yield env.timeout(5)
    result = yield env.timeout(3, value='done')
    print(result, 'at', env.now)      # done at 8
```

### Process as event — wait for another process

`env.process(gen())` returns a `Process`, which *is* an event. Yield it to wait
for that process to finish; its return value becomes the event value.

```python
def worker(env, d):
    yield env.timeout(d)
    return f'worked {d}'

def boss(env):
    result = yield env.process(worker(env, 5))
    print(result)                     # 'worked 5'
```

### `event()` — a manually triggered signal

`env.event()` creates a bare event you trigger yourself — the basis of custom
coordination.

```python
def waiter(env, evt):
    val = yield evt
    print('got', val, 'at', env.now)

def firer(env, evt):
    yield env.timeout(5)
    evt.succeed(value='go')

env = simpy.Environment()
evt = env.event()
env.process(waiter(env, evt))
env.process(firer(env, evt))
env.run()
```

## Composite (condition) events

### `AllOf` / `&` — wait for all

Fires when every child event has triggered. Returns a `ConditionValue`, a
dict-like mapping each child event to its value.

```python
def proc(env):
    a = env.timeout(3, value='A')
    b = env.timeout(5, value='B')
    results = yield a & b             # or simpy.AllOf(env, [a, b])
    print('all done at', env.now)     # at 5
    print(results[a], results[b])     # A B
```

Use for: barrier synchronization, waiting on several resources or subtasks.

### `AnyOf` / `|` — wait for the first

Fires as soon as one child triggers. The returned `ConditionValue` contains only
the child(ren) that had already fired.

```python
def proc(env):
    fast = env.timeout(2, value='fast')
    slow = env.timeout(10, value='slow')
    results = yield fast | slow       # or simpy.AnyOf(env, [fast, slow])
    print(list(results.values()))     # ['fast']
```

Use for: races, first-to-respond, and **timeouts** (see below).

## Triggering events

- **`event.succeed(value=None)`** — mark success, optionally carrying a value.
- **`event.fail(exception)`** — mark failure; the waiting process sees the
  exception raised at its `yield`, so wrap it in `try/except`.
- **`event.trigger(other_event)`** — copy another event's already-decided outcome
  (value or exception) onto this one.

```python
def proc(env):
    evt = env.event()
    evt.fail(ValueError('boom'))
    try:
        yield evt
    except ValueError as e:
        print('caught', e)
```

An event may be triggered **only once**. To signal repeatedly, create a fresh
event after each trigger.

## Callbacks

Every event has a `callbacks` list of one-arg functions run (with the event) when
it is processed. Yielding an event from a process appends that process's resume
method automatically; you can also add your own.

```python
def log(event):
    print('fired with', event.value)

def proc(env):
    evt = env.timeout(5, value='x')
    evt.callbacks.append(log)
    yield evt
```

## Shared events (broadcast)

Many processes can yield the **same** event and all resume together when it fires.

```python
def listener(env, name, sig):
    val = yield sig
    print(name, 'woke with', val, 'at', env.now)

def broadcaster(env, sig):
    yield env.timeout(5)
    sig.succeed(value='go')

env = simpy.Environment()
sig = env.event()
for i in range(3):
    env.process(listener(env, f'L{i}', sig))
env.process(broadcaster(env, sig))
env.run()
```

## Timeout-with-race idiom

Combine a work event and a timeout with `|` to bound how long you wait:

```python
def proc(env):
    work = env.timeout(10, value='work')
    deadline = env.timeout(5, value='timeout')
    result = yield work | deadline
    if work in result:
        print('completed:', result[work])
    else:
        print('timed out')
```

## Guidelines

1. Always `yield` events; a process resumes only at a `yield`.
2. Trigger each event at most once; re-create for repeated signals.
3. Wrap failing events in `try/except`.
4. Use `&`/`AllOf` for barriers, `|`/`AnyOf` for races and deadlines.
5. Pass results through `succeed(value=...)` and read them from `event.value`.
