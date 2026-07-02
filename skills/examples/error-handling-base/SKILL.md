---
id: error-handling-base
name: error-handling-base
version: 0.1.0
description: >-
  Language-agnostic foundation of error-handling rules, pitfalls, and a review
  checklist (explicit handling, actionable messages, no leaked internals, log
  before re-throw). Use WHEN establishing baseline error-handling conventions,
  reviewing error paths for any codebase, or as the shared base that
  language-specific error-handling skills extend. Do NOT use WHEN a
  language-specific variant exists (reach for that skill instead — e.g. a
  Python/Go/Rust error-handling skill), WHEN you need runtime
  debugging/stack-trace tracing (use a debugging skill), or WHEN routing to
  unrelated skills — this is a pattern reference, not a dispatcher.
tags: [error-handling, foundation, example]
---

# Error Handling Base

> **Core insight:** Good error handling is about communication - to users, developers, and monitoring systems.

## Rules

- Always handle errors explicitly - never ignore them
- Use meaningful error messages that describe what went wrong
- Include context in error messages (what was being attempted)
- Log errors at appropriate levels (error vs warning vs info)
- Distinguish between recoverable and unrecoverable errors

**Recoverable vs. unrecoverable** is the classification everything else hangs on.
*Recoverable* means the caller has a real alternative — retry, fall back, skip,
degrade — so handle it at the first layer that owns that fallback. *Unrecoverable*
means a violated invariant or corrupted state where continuing hides the bug, so
fail fast and loudly instead of catching it into a fake value. If you can't say
what the caller would *do* with a caught error besides re-log it, let it propagate.

**Logging level is a signal-to-noise contract** with whoever is on call, picked by
who must act and how urgently: `ERROR` = a failure needing attention (or a
recoverable one that exhausted retries); `WARN` = recovered/degraded (retry that
succeeded, fallback engaged, deprecation); `INFO` = normal lifecycle, never for
errors; `DEBUG`/`TRACE` = reproduction detail, off in prod. Log **once**, at the
boundary that handles the error — logging *and* re-throwing produces duplicate
traces and inflates ERROR counts.

**Actionable and "no leaked internals" are not in tension** — they serve different
audiences. Logs/operators get the full cause chain, identifiers, and stack frames;
end users and API clients get a stable, sanitized message plus a correlation id and
*nothing* about paths, SQL, or stack frames. Join the two by id.

See [`references/patterns.md`](references/patterns.md) for the deeper treatment:
error boundaries (raise low, handle high), cause-preserving translation at module
edges, catch-narrow-not-broad, and deterministic cleanup / partial-failure
(`finally`/`defer`/RAII, atomic rollback, retryable vs. terminal). Language-specific
variants extend these patterns onto their own primitives (exceptions, `Result`,
error values, panics).

## Pitfalls

- Swallowing exceptions without logging
- Using generic error messages like "An error occurred"
- Exposing internal implementation details in user-facing errors
- Catching broad exception types when specific ones are needed

## Examples

```
// Bad: Generic error
throw new Error("Error");

// Good: Descriptive error with context
throw new Error(`Failed to parse config file '${filename}': ${parseError.message}`);
```

## Checklist

- [ ] All error paths are handled explicitly
- [ ] Error messages are actionable and descriptive
- [ ] Sensitive information is not leaked in errors
- [ ] Errors are logged before being re-thrown or converted
