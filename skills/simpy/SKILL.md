---
name: simpy
version: 0.1.0
description: >-
  Process-based discrete-event simulation (DES) in Python with SimPy. Use to
  model systems where entities (customers, jobs, packets, vehicles) flow through
  time and compete for limited shared resources — queues, servers, machines,
  containers, stores — to study waiting times, utilization, throughput, and
  capacity planning across manufacturing, service operations, logistics,
  networks, and healthcare. Processes are Python generators that yield events
  (timeouts, resource requests, custom events, AllOf/AnyOf conditions, process
  interrupts); the Environment advances simulation time event-by-event, skipping
  idle intervals. NOT for continuous / ODE systems integrated on a fixed time
  step (use a numerical solver such as SciPy), large spatial agent-based models
  (use Mesa), pure mathematical optimization, RL training environments, or
  independent processes that never share resources or interact.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT"
---

# SimPy — Discrete-Event Simulation

## Overview

SimPy is a process-based discrete-event simulation (DES) framework built on plain
Python generators. You describe each actor as a generator function (a "process")
that `yield`s **events**; the **Environment** keeps an ordered event queue and
jumps its clock directly from one event to the next, so idle time between events
costs nothing. This makes it ideal for asking *how long do things wait?* and *how
busy is the bottleneck?* in systems where discrete things arrive, queue, get
served, and leave.

Three primitives cover almost everything:

- **Environment** — owns simulation time (`env.now`) and runs the event loop.
- **Process** — a generator started with `env.process(gen())`; pauses on each `yield`.
- **Event** — what a process yields to be resumed later (a timeout, a resource
  grant, a signal, or another process finishing).

## When to Use This Skill

Reach for SimPy when the task involves:

- **Queues and waiting lines** — measure wait time, queue length, service level.
- **Resource contention** — entities compete for a limited pool of servers,
  machines, staff, bandwidth, or vehicles.
- **Throughput / capacity planning** — find how many resources meet a target.
- **Process flows with stochastic timing** — arrivals and service times drawn
  from distributions (Poisson arrivals, exponential service, etc.).
- **Preemption and priorities** — urgent jobs jump the queue or interrupt others.
- **Producer/consumer and buffering** — bounded buffers, inventory, pipelines.
- **What-if experiments** — sweep parameters, compare configurations via replicated runs.
- **Real-time / hardware-in-the-loop** — pace the sim to wall-clock time.

Typical domains: manufacturing lines, call centers and retail checkout, hospital
patient flow, logistics and transport, network packet handling, computer-system
scheduling.

## When NOT to Use This Skill

- **Continuous dynamics / ODEs** integrated on a fixed time step (temperature,
  fluid flow, population models) — use a numerical ODE solver (SciPy
  `solve_ivp`). SimPy has no built-in integrator.
- **Large spatial agent-based models** (grids, movement, local neighbor rules
  over thousands of agents) — use Mesa; SimPy has no spatial layer.
- **Pure mathematical optimization** (find the optimal schedule/allocation
  directly) — use an LP/MILP or metaheuristic solver; SimPy evaluates a scenario,
  it does not optimize one.
- **Reinforcement-learning training environments** — use the `pufferlib` or
  `stable-baselines3` skills; SimPy is not a Gym env.
- **Independent processes with no interaction or shared resources** — if nothing
  contends, a plain loop or vectorized draw is simpler and faster.
- **Analytic queueing results** for a textbook M/M/1-style system — closed-form
  formulas are exact and instant; simulate only when the system breaks those
  assumptions.

## Core Model

Two minimal shapes cover most starts. First, timed processes:

```python
import simpy

def clock(env, name, tick):
    while True:
        print(f'{name} tick at {env.now}')
        yield env.timeout(tick)   # advance simulation time by `tick`

env = simpy.Environment()
env.process(clock(env, 'fast', 1))
env.process(clock(env, 'slow', 2))
env.run(until=4)                  # stop at simulation time 4
```

Second, entities competing for a resource — the DES workhorse:

```python
import simpy, random

def customer(env, name, server):
    arrival = env.now
    with server.request() as req:          # queue for a server
        yield req                          # resumes when granted
        wait = env.now - arrival
        print(f'{name} waited {wait:.1f}, served at {env.now}')
        yield env.timeout(random.expovariate(1/3))  # service time

def arrivals(env, server):
    i = 0
    while True:
        yield env.timeout(random.expovariate(1/2))  # inter-arrival gap
        i += 1
        env.process(customer(env, f'C{i}', server))

random.seed(42)
env = simpy.Environment()
server = simpy.Resource(env, capacity=2)
env.process(arrivals(env, server))
env.run(until=30)
```

Key rules: a process **must** `yield` an event to pause; `env.now` is the current
time; `env.run()` with no `until` runs until the event queue empties; `until` may
be a time *or* an event to stop on.

## Shared Resources — at a glance

Pick the resource type by what is being contended. Full API, properties, and
worked examples: `references/resources.md`.

| Type | Contends over | Grant/consume |
|------|---------------|---------------|
| `Resource` | N interchangeable slots (servers, machines) | `request()` / `release()` |
| `PriorityResource` | slots, served by priority (lower = first) | `request(priority=p)` |
| `PreemptiveResource` | slots; high priority can evict a holder | `request(priority=p, preempt=True)` |
| `Container` | a continuous/bulk quantity (fuel, water) | `put(amount)` / `get(amount)` |
| `Store` | discrete Python objects, FIFO | `put(item)` / `get()` |
| `FilterStore` | objects retrieved by predicate | `get(filter=fn)` |
| `PriorityStore` | objects retrieved in priority order | `put(PriorityItem(...))` / `get()` |

Always acquire a `Resource` via `with resource.request() as req: yield req` so it
is released automatically, even on exceptions.

## Events, Coordination, and Interrupts

Beyond timeouts and resource requests, processes coordinate through custom
events and by waiting on each other:

- **Custom event**: `evt = env.event()`; a process `yield evt` blocks until
  another calls `evt.succeed(value=...)` or `evt.fail(exc)`.
- **A process is itself an event**: `yield some_process` waits for it to finish
  and returns its value.
- **Wait for all / any**: `yield a & b` (AllOf) or `yield a | b` (AnyOf); the
  `|` idiom implements timeouts and races.
- **Interrupts**: `proc.interrupt(cause=...)` throws `simpy.Interrupt` into a
  waiting process — model breakdowns, cancellations, and preemption.

Event lifecycle, `succeed`/`fail`/`trigger`, callbacks, and shared-event
broadcasting: `references/events.md`. Signaling patterns, barriers, handshakes,
resumable interrupts, and preemption handling: `references/process-interaction.md`.

## Building a Simulation — workflow

1. **Map the system.** List entities (what flows), resources (the constraints),
   activities (arrival → service → departure), and the metrics you will report.
2. **Model stochastics.** Choose distributions for inter-arrival and service
   times (`random.expovariate`, `random.uniform`, etc.). Call `random.seed()` for
   reproducibility.
3. **Write generator processes** for arrivals and for each entity's lifecycle;
   request resources with context managers.
4. **Instrument** wait times, queue lengths, and utilization as the run proceeds
   (not just at the end) — see `references/monitoring.md`.
5. **Run and replicate.** A single run is one random path; average metrics over
   many seeds and discard an initial warm-up period before trusting steady-state
   numbers.
6. **Analyze.** Summarize and plot with the `statistical-analysis`, `matplotlib`,
   `seaborn`, or `polars` skills; validate a simple case against a closed-form
   queueing result.

## Monitoring and Real-Time

- **Data collection** — append `(time, value)` records from inside processes,
  subclass a resource to log on every `request`/`release`, compute utilization as
  `count / capacity`, and export to CSV for downstream analysis. Techniques and
  reusable monitor classes: `references/monitoring.md`.
- **Real-time pacing** — swap in `simpy.rt.RealtimeEnvironment(factor=..., strict=...)`
  to tie simulation time to wall-clock time for demos or hardware-in-the-loop.
  `factor` seconds of real time per sim unit; `strict=True` errors if a step
  overruns its budget. Details and limitations: `references/real-time.md`.

## Common Pitfalls

- **Forgetting `yield`** — a process with no `yield` runs to completion instantly
  and never advances time; calling a resource op without `yield` never blocks.
- **Reusing a triggered event** — an `env.event()` fires once. For repeated
  signaling, create a fresh event after each trigger.
- **Leaking resources** — always use `with ... request()`; a missed `release`
  starves the queue.
- **Unhandled interrupts** — wrap interruptible waits in `try/except simpy.Interrupt`.
- **Inconsistent time units** — pick one unit (seconds, minutes) and keep every
  delay in it.
- **Deadlock** — if every process is blocked, `env.run()` returns early with the
  queue non-empty; ensure at least one process can always make progress.
- **Trusting one run** — stochastic output has variance; replicate and average.

## Reference Files

- `references/resources.md` — every resource type, properties, and examples.
- `references/events.md` — the event system, triggering, callbacks, composites.
- `references/process-interaction.md` — signaling, barriers, interrupts, preemption.
- `references/monitoring.md` — data collection, resource instrumentation, export.
- `references/real-time.md` — `RealtimeEnvironment`, `factor`, strict mode, HIL.
