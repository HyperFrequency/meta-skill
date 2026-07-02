---
id: logging-patterns
name: logging-patterns
version: 0.1.0
description: >-
  Foundational logging conventions for observable applications: structured
  key-value logging, correlation/request IDs, level discipline, and
  sensitive-data redaction. Use when writing or reviewing logging in
  application code, standardizing log output across a service, or composing
  a larger skill that needs a logging baseline. This is a reusable building
  block meant to be pulled into composite skills via the 'includes' feature,
  so it exposes only the shared rules, pitfalls, and a reference example
  rather than runnable steps. Do NOT use it as a standalone task runner, for
  setting up a logging backend or transport (Loki, ELK, OpenTelemetry
  collector config), for metrics/tracing pipeline design, or for
  language/framework-specific logger setup beyond the illustrative snippet.
tags: [logging, observability, example]
---

# Logging Patterns

Foundational logging practices for observable applications.

## Rules

- Use structured logging (key-value pairs, not interpolated strings)
- Include request/correlation IDs in all log entries
- Log at appropriate levels (DEBUG, INFO, WARN, ERROR)
- Include enough context to debug issues without the code
- Don't log sensitive information (passwords, tokens, PII)

## Pitfalls

- Logging sensitive data (passwords, API keys, PII)
- Inconsistent log levels across the codebase
- Missing correlation IDs in distributed systems
- Logging at wrong levels (DEBUG in prod, ERROR for non-errors)

## Examples

```rust
// Structured logging with tracing
use tracing::{info, error, instrument};

#[instrument(skip(password))]
fn authenticate(user_id: &str, password: &str) -> Result<Token> {
    info!(user_id, "authentication attempt");

    match verify_credentials(user_id, password) {
        Ok(token) => {
            info!(user_id, "authentication successful");
            Ok(token)
        }
        Err(e) => {
            error!(user_id, error = %e, "authentication failed");
            Err(e)
        }
    }
}
```
