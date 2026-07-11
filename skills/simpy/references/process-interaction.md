# SimPy Process Interaction

Real models need processes that coordinate: wait for a signal, run in sequence or
parallel, and break out of a wait when something urgent happens. SimPy offers
three mechanisms:

1. **Shared events** — passivate a process until another signals it.
2. **Waiting on processes** — a process is an event, so yield it to await it.
3. **Interrupts** — force a waiting process to abort its current wait.

---

## 1. Shared-event signaling

A process blocks on `yield some_event`; another calls `some_event.succeed()` to
release it. This is passivation/reactivation.

```python
import simpy

def controller(env, signal):
    yield env.timeout(5)
    print('signal at', env.now)
    signal.succeed()

def worker(env, signal):
    print('waiting at', env.now)
    yield signal
    print('released at', env.now)
    yield env.timeout(3)

env = simpy.Environment()
signal = env.event()
env.process(controller(env, signal))
env.process(worker(env, signal))
env.run()
```

### Broadcast to many waiters

One event, many listeners — all resume together. (An event fires once, so create
a new one for the next round of signaling.)

```python
def broadcaster(env, sig):
    yield env.timeout(5)
    sig.succeed(value='go')

def listener(env, name, sig):
    msg = yield sig
    print(name, 'got', msg, 'at', env.now)

env = simpy.Environment()
sig = env.event()
for i in range(3):
    env.process(listener(env, f'L{i}', sig))
env.process(broadcaster(env, sig))
env.run()
```

### Barrier (rendezvous)

Hold N processes until all arrive, then release them at once.

```python
class Barrier:
    def __init__(self, env, n):
        self.n = n
        self.count = 0
        self.event = env.event()
    def wait(self):
        self.count += 1
        if self.count >= self.n:
            self.event.succeed()
        return self.event

def worker(env, barrier, name, t):
    yield env.timeout(t)
    print(name, 'at barrier', env.now)
    yield barrier.wait()
    print(name, 'released', env.now)

env = simpy.Environment()
b = Barrier(env, 3)
for name, t in [('A', 3), ('B', 5), ('C', 7)]:
    env.process(worker(env, b, name, t))
env.run()
```

---

## 2. Waiting on other processes

Because `env.process(...)` returns a `Process` (an event), you can compose
workflows.

### Sequential

```python
def task(env, name, d):
    yield env.timeout(d)
    return f'{name} result'

def coordinator(env):
    r1 = yield env.process(task(env, 'T1', 5))
    r2 = yield env.process(task(env, 'T2', 3))   # starts only after T1
    print(r1, r2, 'at', env.now)
```

### Parallel (fork-join)

Start all first, then join with `&`. Read each result from `proc.value`.

```python
def coordinator(env):
    t1 = env.process(task(env, 'T1', 5))
    t2 = env.process(task(env, 'T2', 3))
    t3 = env.process(task(env, 'T3', 4))
    yield t1 & t2 & t3
    print('all done at', env.now, [t1.value, t2.value, t3.value])
```

### First-to-complete (race)

```python
def load_balancer(env):
    s1 = env.process(task(env, 'S1', 5))
    s2 = env.process(task(env, 'S2', 3))
    result = yield s1 | s2
    winner = list(result.values())[0]
    print('first:', winner, 'at', env.now)
```

---

## 3. Interrupts

`proc.interrupt(cause=None)` throws a `simpy.Interrupt` into `proc` at whatever
event it is currently waiting on. Catch it with `try/except simpy.Interrupt`; the
`interrupt.cause` carries whatever you passed.

### Basic interrupt

```python
def worker(env):
    try:
        print('long task at', env.now)
        yield env.timeout(10)
        print('finished at', env.now)
    except simpy.Interrupt as i:
        print('interrupted at', env.now, '-', i.cause)

def interrupter(env, target):
    yield env.timeout(5)
    target.interrupt(cause='higher priority task')

env = simpy.Environment()
w = env.process(worker(env))
env.process(interrupter(env, w))
env.run()
```

### Resumable work (track remaining)

After an interrupt, compute how much work is left and re-enter the wait.

```python
def worker(env):
    work_left = 10
    while work_left > 0:
        try:
            start = env.now
            yield env.timeout(work_left)
            work_left = 0
        except simpy.Interrupt:
            work_left -= env.now - start
            print('interrupted,', work_left, 'left at', env.now)
```

### Cause-driven behavior

Branch on `interrupt.cause` to model different disruptions (maintenance vs.
emergency, cancel vs. reprioritize).

```python
def machine(env, name):
    while True:
        try:
            yield env.timeout(5)          # normal operation cycle
        except simpy.Interrupt as i:
            if i.cause == 'maintenance':
                yield env.timeout(2)      # repair, then resume loop
            elif i.cause == 'emergency':
                break                     # shut down
```

### Preemptive resources use interrupts

With `simpy.PreemptiveResource`, a preempted holder receives an `Interrupt` whose
`cause` is a `Preempted` namedtuple (`.by`, `.usage_since`, `.resource`). Wrap the
`yield req` / hold in `try/except`; see `resources.md`.

---

## Choosing a mechanism

- **Signal / broadcast / barrier** → shared events.
- **Sequential or parallel sub-workflows** → yield processes with `&` / `|`.
- **Breakdowns, cancellations, deadlines, preemption** → interrupts.

## Guidelines

1. Always guard interruptible code with `try/except simpy.Interrupt`.
2. Keep a reference to any process you may need to interrupt.
3. Events fire once — recreate them for repeated handshakes/signals.
4. Track progress (elapsed vs. remaining) to resume cleanly after an interrupt.
5. Ensure at least one process can always advance, or the run deadlocks and
   `env.run()` returns with a non-empty queue.
