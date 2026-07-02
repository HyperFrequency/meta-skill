---
id: testing-patterns
name: testing-patterns
version: 0.1.0
description: >-
  Foundational, language-agnostic testing patterns, checklists, and pitfalls.
  Use when authoring or reviewing tests and you need shared baseline guidance on
  happy-path/error/edge coverage, test independence, and avoiding flaky or
  implementation-coupled tests, or when composing this into a larger skill via
  the 'includes' feature. Do NOT use for framework-specific setup (pytest,
  Jest, JUnit configuration), test-runner debugging, CI pipeline wiring, or
  generating concrete test code for a specific codebase — reach for the relevant
  language/framework skill or write the tests directly instead.
tags: [testing, example]
---

# Testing Patterns

Foundational testing practices applicable across languages and frameworks.

> **Core insight:** a test suite exists to let you change code with confidence.
> Every rule below protects that one property — a test that survives refactors,
> localizes failures, and never lies (false pass or false fail) is worth ten
> that don't.

## Rules

Each rule below carries the *why* so you can apply judgement, not just compliance.

- **Write tests for happy paths and error cases.** The happy path proves the
  feature works; the error paths are where production incidents actually live,
  and they are the least exercised by manual clicking.
- **Test edge cases and boundary conditions.** Bugs cluster at boundaries —
  empty, one, max, off-by-one, overflow, null. A function correct at `n=5` is
  often wrong at `n=0`.
- **Each test should test one thing.** A single-assertion-focused test names the
  exact behavior that broke; a test with eight assertions tells you only that
  "something in this 40-line test" failed.
- **Tests should be deterministic and repeatable.** A test that passes only
  sometimes trains the team to ignore red builds, which defeats the suite.
- **Use descriptive test names that explain the scenario.** `test_withdraw_more_than_balance_is_rejected`
  is a failure report on its own; `test_withdraw_2` makes you open the body.

## Examples

**Test behavior, not implementation** — assert on observable outputs, not on
internal calls, so the test survives refactoring:

```python
# Bad: couples the test to a private method; breaks on any refactor
def test_discount(mocker):
    spy = mocker.spy(cart, "_apply_percentage")
    cart.total_with_discount(0.1)
    spy.assert_called_once_with(0.1)        # tests HOW it works

# Good: asserts the result; only fails if behavior actually regresses
def test_discount_reduces_total():
    cart = Cart(items=[Item(price=100)])
    assert cart.total_with_discount(0.1) == 90   # tests WHAT it does
```

**Isolate test data** — give every test fresh state so a failure points at the
test that actually broke, not at an innocent neighbor:

```python
# Bad: module-level shared state -> passes or fails depending on order
USERS = []

# Good: a factory rebuilds clean state per test
def test_create_user():
    store = UserStore()      # fresh instance, no leakage
    store.create("alice")
    assert store.count() == 1
```

**Kill flakiness** — replace fixed sleeps and wall-clock reads with polling and
injected time so the test is deterministic on a loaded CI box:

```python
# Bad: races the job; fails intermittently under load
start_job(); time.sleep(2); assert job_status() == "done"

# Good: poll for the condition with a timeout
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    if job_status() == "done":
        break
    time.sleep(0.05)
else:
    raise AssertionError("job did not complete within 5s")
```

For the full worked examples, the boundary-vs-internal mocking rule, isolation
techniques (transaction rollback, unique namespaces), and a
flakiness-cause → fix table, see
[`references/behavior-isolation-flakiness.md`](references/behavior-isolation-flakiness.md).

## Checklist

- [ ] Happy path is covered
- [ ] Error cases are tested
- [ ] Edge cases are identified and tested (empty / one / max / boundary)
- [ ] Tests are independent and can run in any order (verify with a randomizer)
- [ ] Test data is isolated per test (fresh state, no shared mutable fixtures)
- [ ] No flaky tests in the suite (no fixed sleeps, no unseeded RNG, no real clock)
- [ ] Tests assert on behavior/outputs, not private internals

## Pitfalls

- **Testing implementation details instead of behavior** — the test breaks on
  every refactor, so the team "fixes the test to match the code" and the safety
  net rots.
- **Not testing error paths** — the untested `except`/`catch` branch is exactly
  the code that runs during an incident.
- **Shared mutable state between tests** — the root cause of order-dependent
  suites; failures land on the wrong test.
- **Tests that depend on execution order** — green locally, red in parallel or
  after a reorder; see isolation guidance in the reference.

## Related skills

This is a language-agnostic baseline meant to be composed (via `includes`) with
more specific skills, not a substitute for them:

- [`error-handling-base`](../error-handling-base/SKILL.md) — pair with this when
  reviewing the error paths that rule 1 says you must test.
- [`logging-patterns`](../logging-patterns/SKILL.md) — assert on the structured
  log/observable side effects this skill recommends instead of on internals.
- **Framework-specific skills** (pytest, Jest, JUnit) — go there for runner
  configuration, fixtures/mocks API, and concrete test scaffolding; this skill
  deliberately stops at the cross-language principles.
