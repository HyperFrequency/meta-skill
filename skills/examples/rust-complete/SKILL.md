---
id: rust-complete
name: rust-complete
version: 0.1.0
description: >-
  Comprehensive Rust development skill combining idiomatic error handling
  (anyhow/thiserror), testing, and tracing-based logging patterns, composed
  from standalone skills via the 'includes' feature. Use WHEN writing or
  reviewing production Rust and you want error-handling, test, and logging
  conventions applied together, or as a reference for the 'includes'
  composition mechanism. Do NOT use for non-Rust languages, for embedded
  no_std work where anyhow/tracing are unavailable, for build/cargo workspace
  configuration, or when you only need one concern (prefer the standalone
  rust-error-handling, testing-patterns, or logging-patterns skills).
tags: [rust, complete, example]
includes:
  - skill: rust-error-handling
    into: rules
  - skill: testing-patterns
    into: checklist
  - skill: logging-patterns
    into: rules
    prefix: "[Logging] "
---

# Complete Rust Development

A comprehensive Rust development skill that combines error handling, testing,
and logging patterns through composition.

This skill demonstrates the `includes` feature:
- Error handling rules from `rust-error-handling` are merged into Rules
- Testing checklist from `testing-patterns` is merged into Checklist
- Logging rules from `logging-patterns` are merged into Rules with a prefix

## Rules

- Follow Rust idioms and conventions
- Use `clippy` for linting: `cargo clippy -- -D warnings`
- Format code with `rustfmt`: `cargo fmt`
- Keep unsafe blocks minimal and well-documented

### Error handling (concrete)

- **Library vs. application split:** define a typed error enum with
  `thiserror` for code that other crates depend on (callers can `match` on
  variants), and reserve `anyhow::Error` for binaries/top-level glue where the
  caller only logs or exits. Do not export `anyhow::Error` from a library's
  public API — it erases the variant information downstream code needs.
- **Add context at every fallible boundary** with `.context(...)` (static
  message) or `.with_context(|| ...)` (when formatting the message allocates,
  so the cost is only paid on the error path). Context accumulates into a
  cause chain that prints as `Caused by:` lines, turning an opaque
  `No such file or directory` into `failed to load config: Caused by: ...`.
- **Never `.unwrap()`/`.expect()` on recoverable errors** in non-test code.
  `unwrap()` is acceptable only when a `None`/`Err` is a genuine invariant
  violation (a bug), and then prefer `.expect("reason invariant holds")` so the
  panic message documents the assumption.
- **Propagate, don't stringify:** return `Err(e)?` / `?` rather than
  `format!("{e}")`. Converting errors to strings early destroys the typed
  chain and source `Backtrace`.

### Logging / tracing (concrete)

- **Initialize a subscriber exactly once** at process start (`main`), driven by
  `RUST_LOG` via `EnvFilter` so verbosity is configurable without recompiling:
  `tracing_subscriber::fmt().with_env_filter(EnvFilter::from_default_env()).init();`.
- **Prefer structured fields over interpolation:** `info!(user_id, %request_id,
  "request handled")` keeps fields machine-parseable; `%` uses `Display`, `?`
  uses `Debug`. Avoid `info!("handled {request_id}")` — it bakes the value into
  the message and breaks downstream filtering/aggregation.
- **Use `#[instrument]` to create a span** around a function so every event
  inside it inherits the function's arguments as span context. Add
  `skip(large_arg)` to avoid logging big or sensitive payloads, and
  `err` (i.e. `#[instrument(err)]`) to auto-record the returned `Err` at
  `ERROR` level.
- **Pick levels deliberately:** `error!` = the operation failed and a human
  should know; `warn!` = degraded but recovered; `info!` = lifecycle
  milestones; `debug!`/`trace!` = developer detail gated off in production.

### Testing (concrete)

- **Unit tests** live in a `#[cfg(test)] mod tests` block beside the code so
  they can exercise private items; **integration tests** live under `tests/`
  and see only the public API — keep both.
- **Assert on error semantics, not just `is_err()`:** match the typed variant
  (`assert!(matches!(err, MyError::NotFound { .. }))`) or check the rendered
  chain (`assert!(err.to_string().contains("failed to parse")`) so a test
  failing for the *wrong* reason is caught.
- **Async tests** need a runtime: `#[tokio::test]` (or `#[tokio::test(flavor =
  "multi_thread")]` for code that spawns). **Property tests** (`proptest!`)
  cover input ranges a few hand-picked cases miss.

## Examples

```rust
// Idiomatic Rust with proper error handling, logging, and tests
use anyhow::{Context, Result};
use tracing::{info, instrument};

#[instrument]
pub fn process_data(input: &str) -> Result<Output> {
    info!("processing data");

    let parsed = parse_input(input)
        .context("failed to parse input")?;

    let result = transform(parsed)
        .context("transformation failed")?;

    info!(output_size = result.len(), "processing complete");
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process_data_happy_path() {
        let input = "valid input";
        let result = process_data(input);
        assert!(result.is_ok());
    }

    #[test]
    fn test_process_data_invalid_input() {
        let input = "";
        let result = process_data(input);
        assert!(result.is_err());
    }
}
```

### Worked example: typed library errors with `thiserror`

A library returns a typed enum so callers can branch on the failure. The
`#[from]` attribute generates `From` impls, letting `?` convert a `std::io` or
`serde_json` error into the right variant automatically, while `#[source]`
preserves the underlying cause for the `Caused by:` chain.

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("config file not found at {path}")]
    NotFound { path: String },

    #[error("failed to read config")]
    Io(#[from] std::io::Error),       // `?` on an io::Error lands here

    #[error("invalid config syntax")]
    Parse(#[from] serde_json::Error), // `?` on a parse error lands here
}

pub fn load_config(path: &str) -> Result<Config, ConfigError> {
    if !std::path::Path::new(path).exists() {
        return Err(ConfigError::NotFound { path: path.to_owned() });
    }
    let raw = std::fs::read_to_string(path)?;   // io::Error -> ConfigError::Io
    let cfg = serde_json::from_str(&raw)?;      // json::Error -> ConfigError::Parse
    Ok(cfg)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_file_is_not_found_variant() {
        let err = load_config("/does/not/exist.json").unwrap_err();
        // Assert the *variant*, not merely that it errored.
        assert!(matches!(err, ConfigError::NotFound { .. }));
        assert!(err.to_string().contains("not found"));
    }
}
```

### Worked example: spans, structured fields, and an async test

`#[instrument(skip(db), err)]` opens a span carrying `user_id`, omits the
connection handle from the log, and auto-records any returned `Err` at error
level. The test drives it on a Tokio runtime and asserts the error chain text.

```rust
use anyhow::{Context, Result};
use tracing::{info, instrument};

#[instrument(skip(db), err)]
async fn fetch_user(db: &Db, user_id: u64) -> Result<User> {
    let row = db
        .query_one("SELECT * FROM users WHERE id = $1", &[&user_id])
        .await
        .with_context(|| format!("query failed for user_id={user_id}"))?;
    info!(found = true, "user loaded");
    Ok(User::from_row(row))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn missing_user_surfaces_context() {
        let db = Db::in_memory();             // empty store
        let err = fetch_user(&db, 42).await.unwrap_err();
        // The added context is visible at the top of the chain.
        assert!(err.to_string().contains("query failed for user_id=42"));
    }
}
```

Wire up the subscriber once in `main` so the spans/events above are emitted:

```rust
use tracing_subscriber::EnvFilter;

fn main() {
    // Honors RUST_LOG, e.g. RUST_LOG=info,my_crate=debug
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();
    // ... run the app ...
}
```

## Checklist

- [ ] Code passes `cargo clippy -- -D warnings`
- [ ] Code is formatted with `cargo fmt`
- [ ] No `unsafe` blocks (or they are justified and documented)
- [ ] Dependencies are minimal and audited
- [ ] Public library APIs return typed (`thiserror`) errors; `anyhow` is
      confined to binaries / top-level glue
- [ ] Every fallible call adds `.context(...)`; no `.unwrap()`/`.expect()` on
      recoverable paths outside tests
- [ ] Error-path tests assert the variant or message, not just `is_err()`
- [ ] A `tracing` subscriber is initialized once with `EnvFilter`, and logs use
      structured fields rather than string interpolation
