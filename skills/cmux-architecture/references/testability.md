# Testability

This reference expands the testability rules for `Packages/` code.

Every public type added to `Packages/` must be testable from a test target without launching the app target, without booting AppKit, and without depending on the user's filesystem or `UserDefaults.standard`. If a design is hard to test, it is wrong — reach for the constructor parameter list, not the test bench.

## No global state in package code

Every public type that needs `UserDefaults`, `FileManager`, an on-disk path, an environment variable, or a clock takes it via initializer parameter. Tests pass a `UserDefaults(suiteName:)` scoped to the test, a temp directory URL, a fixed `Date`, etc.

## No reliance on `.shared` / `.standard`

A public type that hardcodes `UserDefaults.standard` or `FileManager.default` inside its implementation cannot be tested without polluting the developer's actual settings. Inject these at the seam.

## Test through injected seams, never a static test hook

A `nonisolated(unsafe) static var fooForTesting` (or any global mutable "override" a test swaps in) is global state by another name: it leaks across tests, forces `nonisolated(unsafe)`, and usually needs a lock. Replace it with a protocol seam injected through `init`:

```swift
init(commandRunner: any CommandRunning = CommandRunner())
```

The test passes a conforming fake. When you extract such a type into a package, deleting the static hook (and the lock it required) is part of the extraction, not a follow-up.

## Return values, not side effects

A function that mutates global `UserDefaults` and returns `Void` is harder to test than one that returns the changed value and lets the caller persist. Prefer pure transformations plus a thin imperative layer.

## Surface observation as `AsyncStream`

Tests can iterate `AsyncStream` deterministically and assert the sequence of yielded values. Avoid `NotificationCenter`-only patterns where the test has to spin a runloop.

## Document the test pattern

Document the test pattern alongside any non-trivial public surface. The package's `README.md` and any DocC catalog should show how to instantiate the type with test-friendly dependencies.
