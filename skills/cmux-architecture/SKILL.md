---
name: cmux-architecture
version: 0.1.0
description: "cmux package architecture, refactor layering, dependency inversion, file organization, DocC documentation, package design discipline, testability, and Swift 6 concurrency rules. Use before adding or meaningfully rewriting Swift files, Swift packages, coordinators, services, repositories, or public package APIs. Not for: general Swift coding patterns or UI implementation details—consult domain-specific skills for those."
---

# cmux Architecture

This is the design contract for migrating cmux from a single app target into Swift Packages under `Packages/`. It is a router: the enforceable core of each rule is below; worked examples and per-topic depth live in `references/`. Read the matching reference before extracting a package, reshaping concurrency, or designing a public API.

Scope: every new file in `Packages/`, every new file in the app target, and every meaningful rewrite of an existing Swift file. Existing app-target code keeps its old primitives until rewritten — do not retrofit blindly. The packages already under `Packages/` predate this policy and are not design references.

## Package architecture

Every new package must satisfy three rules:

- **Ergonomic.** Public API matches what callers naturally write. Default to `internal`; expose `public` only for what downstream consumers actually use.
- **No dependency cycles.** Packages form a strict DAG; a package may depend only on packages strictly lower in the graph. Share a type by lifting it to a common lower package or defining a protocol seam in the consumer. Re-check acyclicity on every new edge.
- **Clear but not overly narrow responsibilities.** A package owns one full domain (settings, appearance, workspace, terminal, browser, command palette), not a slice. Prefer one `CmuxAppearance` (settings + theming + colors + glass + snapshots) over `CmuxAppearanceMath` + `CmuxAppearanceTheme` + `CmuxAppearanceSettings`. Fragmenting a domain into `…Formatting` + `…Logic` + `…State` is folder structure, not module structure. A boundary exists only because more than one consumer needs the contents or a build/test seam must exist.

When in doubt, **extract leaf-first**: pull the package with no internal dependencies. Consumers in the app target stay put and only update imports.

**Wiring a new local package.** `cmux.xcodeproj` lists package dependencies explicitly (not a synchronized-folder project). Adding `Packages/CmuxFoo` means mirroring an existing package's `project.pbxproj` entries — one `XCLocalSwiftPackageReference`, one `XCSwiftPackageProductDependency`, and a `PBXBuildFile` in the Frameworks phase of **every** target that imports it. App-target packages link into **both** `cmux` and `cmux-unit` (so tests can import and inject them); copy a recent leaf like `CmuxSocketControl`, then run the cmux repo's pbxproj normalize/check step. A package the app builds against but `cmux-unit` does not link compiles the app yet fails the test target.

→ `references/package-boundaries.md` for the dependency graph, leaf-first extraction, composition root, executable boundary, and pbxproj wiring.

## Refactor architecture: layers and roles

**Layered, downward-only DAG** (dependencies point only down):

1. **Core** (`CmuxCore`) — pure `Sendable` values, IDs, DTOs, errors, protocol seams. No AppKit/SwiftUI/I/O. The lift target for shared types.
2. **Services / infrastructure** — `actor`s implementing core protocols against the outside world (PTY, filesystem, sockets, web API, auth). One package per capability.
3. **Domain / state** — `@MainActor @Observable` models + Coordinators, one package per feature domain. `CmuxSettings` is the exemplar.
4. **UI** — SwiftUI/AppKit views, one UI package per domain package, depending only on its domain package + Core, never a Service directly. `CmuxSettingsUI` is the exemplar.
5. **Executable** (`cmuxApp` / `AppDelegate`) — a thin composition shim, no business logic.

**Classify every extracted entity by role:** a **Coordinator** is a `@MainActor @Observable` orchestrator sequencing a user flow (no I/O); a **Service** is an `actor` performing one outside-world capability (`async`/`await` + `AsyncStream`, no UI state); a **Repository** is an `actor` mediating one persistence source of truth behind CRUD-shaped async methods returning value types.

**Dependency inversion.** Lower packages publish protocols; concretes conform; higher layers depend on `any Protocol`. Injection is constructor (`init`) injection only — no global container, no singleton, no `static let shared`. The executable app target is the single composition root. SwiftUI `Environment` may carry already-constructed `@Observable` models down a view tree but is never the source of truth for service wiring.

**State + SwiftUI wiring.** Domain state lives in `@MainActor @Observable` models (never `ObservableObject`/`@Published`). Decompose a god model into child `@Observable` sub-models owned by their domain packages, composed by held reference, with cross-domain reads behind read-only protocols. In views use `@State` (owned), `@Bindable`/plain `let` (passed-in), or `@Environment(M.self)` + `.environment(...)` (injected) — never `@StateObject`/`@ObservedObject`/`@EnvironmentObject`/`.environmentObject(_:)`.

**Executable-target boundary (invert, never work around):** `@main` `cmuxApp` and `AppDelegate` stay in the executable target (intended end state, not debt). A lower package cannot extend a higher-owned type, so `AppDelegate+*` / `cmuxApp+*` / `Workspace+*` extensions do not move down — extract the behavior into a Coordinator/Service/Repository, own an instance, and reduce the extension to a one-line forward. Stored properties cannot cross module boundaries — decompose god-model state into child `@Observable` sub-models.

→ `references/package-boundaries.md` for role definitions, dependency inversion, and state-wiring depth.

## File organization and documentation

One major type per file. Each `struct`/`class`/`enum`/`actor`/`protocol` that is part of a public API (or has a meaningful body) lives in its own file named after the type. Small private trivial helpers may stay with their parent; conformance extensions go in `TypeName+Conformance.swift`; type-erased `AnyFoo` lives next to `Foo`. God files (`ContentView.swift`, `Workspace.swift`, `TabManager.swift`, `cmuxApp.swift`) are the pattern this rule exists to stop — split one file per type even if it triples the count.

Every `public` symbol in a new `Packages/` package gets a Swift-DocC `///` comment at the time of writing — docs are part of the API surface. One-sentence summary first line ending in a period, optional discussion paragraph, `- Parameter`/`- Returns`/`- Throws` callouts, double-backtick symbol references. Update the doc in the same edit that changes behavior. App-target code is not retroactively required to be documented.

→ `references/file-api-discipline.md` for one-type-per-file, extension files, DocC coverage, and design smells.

## Package design discipline

Catch these at the design step, not at code review:

- **No shared-singleton accessors.** `static let standard`/`shared`/`default` holding runtime state is a singleton — construct at startup and inject. `static let` is fine for declarations (identifiers, schema, enum cases).
- **No namespace-enums.** `enum Foo { static func bar() }` is a fake namespace with no DI or test seam. Prefer a value-typed struct (constructor-passed) or a file-private helper.
- **No parallel hand-maintained registries.** Derive a list that mirrors declared items via `Mirror` reflection or a macro — two sources of truth drift silently.
- **Prefer compile-time invariants to runtime traps.** `guard … else { assertionFailure(); return default }` for a "programmer error" wants a type-system encoding instead.
- **No free functions.** Scope functionality to an owning entity. Top-level `func` (any visibility) is banned except a `@convention(c)` C trampoline with justification.
- **Nested types count for one-major-type-per-file.** A `private final class` with a meaningful body moves to its own file.

→ `references/file-api-discipline.md` for design-smell detail.

## Testability

Every public type added to `Packages/` must be testable from a test target without launching the app, booting AppKit, or touching the user's filesystem / `UserDefaults.standard`. If a design is hard to test, it is wrong — reach for the constructor parameter list, not the test bench.

- Inject `UserDefaults`, `FileManager`, paths, env vars, and clocks via `init`; never hardcode `.standard`/`.default`.
- Replace any static test hook (`nonisolated(unsafe) static var fooForTesting`) with a protocol seam injected through `init` — e.g. `init(commandRunner: any CommandRunning = CommandRunner())` — and pass a fake.
- Prefer returning changed values over mutating global state; surface observation as `AsyncStream` so tests iterate deterministically.

→ `references/testability.md` for the full seam catalogue.

## Modern Swift concurrency

All new package code and app-target files use Swift 6 primitives: `actor`, `async`/`await`, `AsyncStream`/`AsyncSequence`, `@Observable`, `@MainActor`. Mutable shared state → `actor`; SwiftUI-facing state → `@Observable @MainActor`; new observable surfaces → `AsyncStream`. Do not introduce a single-method `actor` that only guards a flag — that is a lock with extra suspension; use the lock carve-out.

**Forbidden in new code** (no exception without a written PR justification): locks (`NSLock`, `OSAllocatedUnfairLock`, `Synchronization.Mutex`, `DispatchSemaphore`-as-lock); KVO via `NSObject` `observeValue`/`addObserver(_:forKeyPath:)`; `DispatchQueue.sync` as a serial lock; Combine for change propagation (`@Published`, `ObservableObject`, `PassthroughSubject`/`CurrentValueSubject`, `AnyCancellable`); new completion-handler APIs (`(Result<T,Error>)->Void`); `DispatchQueue.main.async` (annotate `@MainActor`); `DispatchQueue.asyncAfter`; and sleep (`Task.sleep`/`Clock.sleep`) used to poll, settle, or race.

**Acceptable with a one-line justification on the declaration**, hidden behind an `AsyncStream`/`actor`: `DispatchSource.makeFileSystemObjectSource` (file watching); `DispatchSource.makeReadSource`/`makeWriteSource` (low-level socket I/O); a bounded, cancellable, injected-clock `Clock.sleep`/`Task.sleep` for a genuine delay/deadline (min display duration, auto-dismiss, timeout — never to poll/settle/race); `DispatchSource.makeTimerSource` (one-shot) only when a deadline must fire outside any async context; a lock for a synchronous one-shot resume guard where several non-async callbacks race to resume one `withCheckedContinuation`; `NSKeyValueObservation` token when wrapping a KVO-only Foundation/AppKit type.

`@unchecked Sendable` and `nonisolated(unsafe)` each require a safety-argument comment; prefer `nonisolated(unsafe) let` on the single non-Sendable property over marking a whole actor/struct unchecked.

→ `references/concurrency-carveouts.md` for actor-vs-lock guidance, every carve-out with examples, and the reviewer checklist.

## Detailed references

- `references/package-boundaries.md` — package extraction, dependency graph, roles, composition root, executable boundary, pbxproj wiring.
- `references/concurrency-carveouts.md` — actors, locks, DispatchSource, sleep, `@unchecked Sendable`, `nonisolated(unsafe)`, reviewer checklist.
- `references/file-api-discipline.md` — one-type-per-file, DocC, public API, design smells.
- `references/testability.md` — injectable seams and the test-pattern requirements for public package types.
