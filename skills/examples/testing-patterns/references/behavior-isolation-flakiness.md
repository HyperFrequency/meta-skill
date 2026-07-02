# Deep dive: behavior testing, test isolation, and flakiness

This reference expands the three patterns that bite hardest in real suites. The
top-level `SKILL.md` carries the rules and short examples; this file carries the
longer worked examples and the diagnostic procedures you delegate to when a
review surfaces one of these problems.

---

## 1. Behavior vs. implementation

**Why it matters:** a test coupled to *how* code works (private methods, call
order, internal data structures) breaks every time you refactor — even when the
observable behavior is unchanged. That trains the team to "fix the test to match
the code," which silently destroys the test's value as a safety net. Tests
coupled to *what* the code does (inputs → outputs, observable side effects)
survive refactors and only fail when behavior actually regresses.

### Bad — asserts on implementation

```python
def test_discount_calls_internal_helper(mocker):
    cart = Cart(items=[Item(price=100)])
    spy = mocker.spy(cart, "_apply_percentage")   # private method
    cart.total_with_discount(0.1)
    spy.assert_called_once_with(0.1)              # tests the HOW
```

If you rename `_apply_percentage` or inline it, the test fails despite the
discount math being correct.

### Good — asserts on observable behavior

```python
def test_discount_reduces_total():
    cart = Cart(items=[Item(price=100)])
    assert cart.total_with_discount(0.1) == 90    # tests the WHAT
```

**Rule of thumb:** mock at the *boundary* (network, clock, filesystem,
third-party API), not at internal seams of your own unit. If you find yourself
mocking a private method of the class under test, that is a signal to assert on
its output instead.

---

## 2. Isolating test data

**Why it matters:** shared mutable state is the root cause of order-dependent
suites. When test A mutates a module-level fixture and test B reads it, the suite
passes in one order and fails in another — and the failure points at B even
though A is the culprit. Isolation makes each test reconstruct exactly the state
it needs, so a failure localizes to the test that actually broke.

### Bad — module-level shared fixture

```python
USERS = []  # shared across the module

def test_create_user():
    USERS.append(User("alice"))
    assert len(USERS) == 1   # passes first, fails on re-run / reorder

def test_list_users_empty():
    assert USERS == []       # depends on test_create_user not running first
```

### Good — fresh state per test

```python
def make_user_store():
    return UserStore()       # factory: every test gets a clean instance

def test_create_user():
    store = make_user_store()
    store.create("alice")
    assert store.count() == 1

def test_list_users_empty():
    store = make_user_store()
    assert store.list() == []
```

**Techniques:** per-test factories/fixtures; transaction-rollback or truncate
between DB tests; unique namespaces (temp dirs, random table prefixes) when tests
must touch real shared resources in parallel. Never rely on tests cleaning up
after each other in a particular order.

---

## 3. Detecting and fixing flakiness

**Why it matters:** a test that fails intermittently is worse than no test —
teams learn to hit "re-run" and stop trusting red builds, so real regressions
slip through. Flakiness is almost always non-determinism leaking into the test.

### Detection

- Run the suite repeatedly: `pytest --count=50` (pytest-repeat) or a shell loop
  `for i in $(seq 50); do pytest path::test || break; done`.
- Randomize order to expose hidden coupling: `pytest -p randomly`
  (pytest-randomly) or Jest's default randomized order.
- Run in parallel (`pytest -n auto`) to surface shared-resource contention.

### Common causes → fixes

| Cause | Symptom | Fix |
|---|---|---|
| Real wall-clock / `now()` | Fails near midnight, month boundaries | Inject a fixed clock / freeze time |
| Unseeded randomness | Fails ~1 in N runs | Seed the RNG in setup |
| `sleep(n)` then assert | Fails on slow CI | Poll for the condition with a timeout, don't sleep a fixed amount |
| Order dependence | Fails only in some orders | Isolate state (section 2) |
| Unordered collections | Fails on dict/set iteration order | Assert on sorted/normalized output |
| Network / external API | Fails when offline or rate-limited | Stub the boundary; keep a separate, quarantined integration tier |

### Bad — sleep-then-assert race

```python
def test_job_completes():
    start_job()
    time.sleep(2)                     # hope it's done
    assert job_status() == "done"     # flaky on a loaded CI box
```

### Good — poll with a timeout

```python
def test_job_completes():
    start_job()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if job_status() == "done":
            return
        time.sleep(0.05)
    raise AssertionError("job did not complete within 5s")
```

When you cannot remove the non-determinism (true third-party integration), move
the test into a clearly separated, non-blocking integration tier rather than
letting it gate every commit.
