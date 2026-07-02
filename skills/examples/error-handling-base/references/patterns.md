# Error Handling — Deeper Patterns

This file backs the one-line rules in `SKILL.md` with the reasoning a
language-specific variant (Python/Go/Rust/TS) is expected to build on. The base
stays language-agnostic; variants map these patterns onto their own primitives
(exceptions, `Result`/`Either`, error values, panics).

## Recoverable vs. unrecoverable errors

The single most important classification. It decides whether code should *handle*
or *propagate/abort*.

- **Recoverable** — the caller has a meaningful alternative: retry, fall back to a
  default, skip the item, degrade gracefully, or surface a clear message and let
  the user correct input. Examples: a network timeout, a missing optional config
  key, a parse failure on one record in a batch, an optimistic-lock conflict.
  Handle these close to where a sensible recovery exists — usually *not* at the
  point they're raised, but at the first caller that owns a fallback.

- **Unrecoverable** — a violated invariant or corrupted state where continuing
  would produce wrong results or hide the bug: failed assertions, exhausted
  memory, a "this branch is impossible" case, a config the program cannot run
  without at startup. Fail fast and loudly. Don't paper over these with a
  `catch`/`recover` that returns a fake value — that converts a crash you can
  debug into silent data corruption you can't.

Mapping by language: exceptions vs. `panic`/`abort` (most languages), `Result<T,E>`
for recoverable + `panic!` for unrecoverable (Rust), returned `error` value vs.
`panic` (Go). The boundary is the design decision; the keyword is incidental.

**Rule of thumb:** if you can't articulate what the caller would *do* with a
caught error besides re-log it, it probably shouldn't be caught there — let it
propagate to a layer that can.

## Error boundaries

Decide *where* errors are handled, not just *that* they are.

- **Raise low, handle high.** Detect and signal errors at the deepest point that
  has the facts; handle them at the shallowest point that has the context and a
  recovery strategy. Catching one line below the throw usually means you're
  guessing.
- **One boundary per concern.** A request handler, a job worker, a CLI `main`, and
  a UI event handler are natural top-level boundaries: each catches what bubbles
  up, logs once with full context, and converts it to the right response
  (HTTP 500 + correlation id, non-zero exit code, user-facing toast). Avoid
  catching the same error at every layer in between.
- **Translate at module edges.** When an error crosses an abstraction boundary,
  wrap it in a domain-meaningful type and *preserve the cause* (exception
  chaining / `%w` wrapping / `.source`). Never discard the original — the chain is
  what makes a 3 a.m. stack trace solvable. The anti-pattern is catching a
  low-level error and re-throwing a brand-new one with no link back.

## Logging-level rationale

Levels are a signal-to-noise contract with whoever is on call. Pick by *who needs
to act and how urgently*, not by how the code "feels".

- **ERROR** — something failed that needs human attention or breaks a user's
  request; an unrecoverable error, or a recoverable one that exhausted its
  retries. Should be rare enough that an alert on ERROR volume is meaningful.
- **WARN** — a recovered or degraded condition: a retry that eventually
  succeeded, a fallback that kicked in, a deprecated path, approaching a quota.
  No action needed right now, but a rising trend is a leading indicator.
- **INFO** — normal lifecycle milestones (startup, shutdown, request completed).
  Not for errors.
- **DEBUG/TRACE** — diagnostic detail (payloads, intermediate state) for
  reproduction; off in production by default.

Cross-cutting rules:

- **Log once, at the boundary that handles it.** Logging an error *and* re-throwing
  it produces duplicate, interleaved stack traces and inflates ERROR counts. Either
  handle-and-log, or wrap-and-propagate (adding context) — not both.
- **Don't log-and-swallow.** Catching, logging at INFO/DEBUG, and returning as if
  nothing happened is the most common way real failures disappear. If it was worth
  catching, it was worth either recovering or re-raising.
- **Severity must match reality.** An expected, handled condition logged at ERROR
  trains responders to ignore ERROR; a genuine failure logged at DEBUG hides it.

## Actionable messages and the security boundary

A good error message answers three questions: *what* operation failed, *on what
input/resource*, and *why* (the underlying cause). `"Failed to parse config file
'/etc/app.yml': unexpected token at line 12"` lets someone fix it; `"An error
occurred"` starts a debugging session.

But there are **two audiences with opposite needs**:

- **Operators/logs** want maximum detail: stack traces, identifiers, the failing
  value, the cause chain.
- **End users / API clients** want a stable, safe message plus a correlation id —
  and *nothing* about internals. Leaking file paths, SQL, stack frames, library
  versions, or secret-adjacent values is both a poor UX and a recon gift to an
  attacker.

The pattern: log the rich detail internally, return a sanitized message + an id
externally, and let support join the two by id. This is why "no leaked internals"
and "actionable messages" aren't in tension — they apply to different audiences.

## Catch narrow, not broad

Catching the broadest type (`except Exception`, `catch (Throwable)`, bare
`recover()`) sweeps up errors you never intended to handle — including
programmer-error bugs and unrecoverable conditions that should have crashed.
Catch the *specific* type you know how to recover from; let everything else
propagate. A broad catch is acceptable only at a top-level boundary whose explicit
job is "log anything unexpected and convert it to a safe response" — and even
there it should re-raise truly fatal conditions where the language distinguishes
them.

## Cleanup and partial failure

Error handling isn't only about the message — it's about leaving the system in a
consistent state when an operation aborts midway.

- **Release resources deterministically** on every path, success or failure:
  `finally` / `defer` / RAII / context managers / `using`. Don't rely on the
  happy path to close files, sockets, locks, or transactions.
- **Make partial failures atomic where it matters.** If step 3 of 5 fails, either
  roll back steps 1–2 or record enough state to resume; don't leave half-written
  data. For non-transactional side effects, design idempotent retries.
- **Distinguish "retryable" from "terminal" before retrying.** Blindly retrying a
  validation error (400-class) just burns time; retrying a transient timeout
  (with backoff and a cap) is correct. Encode this in the error type so callers
  can branch on it.
