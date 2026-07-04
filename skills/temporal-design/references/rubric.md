# Review rubric

## 1. Temporal fit

Determine whether the use case is appropriate for Temporal.

### Good fit indicators

- long-running, multi-step business process
- need for durable execution
- retries and failure recovery matter
- coordination across services matters
- human-in-the-loop or asynchronous progression exists
- waiting, timers, external callbacks, or approvals are required

### Poor fit indicators

- extreme low-latency requirements where milliseconds matter
- simple synchronous read-only operations
- using Temporal as a data plane instead of a control plane
- pushing large data blobs through workflows unnecessarily

### Flag the design if Temporal is used primarily for:

- direct query serving
- high-frequency micro-latency trading or similarly latency-critical paths
- bulk data transport instead of orchestration

### Questions to ask

- What business process is being orchestrated?
- Where does Temporal fit in the architecture?
- What starts the workflow?
- How often does it run?
- How long does it run?
- Is Temporal being used only where durable orchestration is needed?

## 2. Workflow review

Check whether workflow definitions follow Temporal execution constraints and best practices.

### Determinism

Workflows must be deterministic.

Flag:

- non-deterministic branching
- reliance on wall clock, random values, or mutable external state in workflow code
- use of run IDs for logic
- code changes that would break replay without versioning

Ask:

- Does the design acknowledge workflow replay?
- Are replay tests or replayer usage included?
- Is there a versioning plan for workflow evolution?

### Event history awareness

Workflows must account for event history growth.

Concrete platform thresholds to flag against (measure the design against these numbers, not vague "warning levels"):

- Event History hard limit: **51,200 events OR 50 MB** per execution. Exceeding either terminates the workflow ("history size/count exceeds limit"). Treat a design that can plausibly reach this as `fail` (hard).
- Event History warning: logged at **10,240 events OR 10 MB**. A design that routinely crosses this without a Continue-As-New trigger is `needs_revision` (warn).
- Pending-operation cap: **2,000 each** per execution for Activities, Child Workflows, Signals, and Cancel requests (server dynamic config `NumPending*LimitError`). Hitting any of these fails and retries the Workflow Task. Treat designs that can exceed any of these as `fail` (hard).

Flag:

- unbounded loops without Continue-As-New strategy
- signal, activity, child-workflow, or update volume that can approach the 2,000 pending cap or the 10,240-event / 10 MB warning in one execution
- repeated large payloads in history
- no partitioning strategy for long-running or high-volume workflows

Recommend:

- trigger Continue-As-New well before the 10,240-event / 10 MB warning level, not at the 51,200 / 50 MB hard limit
- partition work with child workflows where justified
- keep workflow state compact

### Workflow ID usage

Verify:

- workflow IDs are meaningful business identifiers where appropriate
- uniqueness constraints are intentionally used as idempotency protection
- Workflow ID **Reuse Policy** is explicitly considered for *closed* workflows (whether a closed ID may be reused)
- Workflow ID **Conflict Policy** is explicitly chosen for *running* workflows — one of `FAIL`, `USE_EXISTING`, or `TERMINATE_EXISTING` — when a start may collide with an already-running execution

Flag:

- frequent reuse of the same workflow ID
- logic based on run ID
- reuse policy vs conflict policy confused, or left to defaults where a collision is plausible

### Timeouts

Assume default workflow timeouts are usually correct unless the design justifies changes.

Review baseline: the default **Workflow Task timeout is 10 seconds**, and Workflow Execution / Run timeouts are unset (unbounded) by default. Treat any deviation as an intentional choice that should be justified.

Flag:

- workflow execution or run timeouts set without clear reason
- workflow timeouts used instead of explicit timers for business deadlines
- workflow task timeout implications ignored when histories are large or converters are expensive

Recommend:

- use timers inside workflows to model business timeouts
- tune the (10s default) workflow task timeout only when justified — for example when large histories or expensive converters push a single workflow task past 10s

### Failure semantics

Verify the design understands:

- non-Temporal failures fail workflow tasks and are retried
- workflow failures should not be used for transient operational issues
- workflow retry policies are generally not recommended

Flag:

- workflow retries added without strong justification
- assumptions that workflow exceptions behave like activity retries

## 3. Child workflow review

### Default rule

When in doubt, prefer an activity over a child workflow.

### Valid reasons to use child workflows

- partition large workloads to control event history growth
- isolate ownership boundaries
- route execution by task queue, trust boundary, or workload type
- model durable sub-processes with their own lifecycle

### Weak reasons

- organizing code structure
- reducing cost
- replacing normal language modularity

### Flag:

- child workflows used only for code organization
- too many child workflows started by one parent (see hard/soft limits below)
- Parent Close Policy not chosen deliberately — confirm the design picked one of `TERMINATE`, `ABANDON`, or `REQUEST_CANCEL` on purpose for each child, rather than defaulting blindly
- assumptions that parent and child share local state

### Guidance

- **2,000 pending child executions per parent is the hard limit** — exceeding it fails (and retries) the Workflow Task. Treat a design that can reach this as a `fail` (hard failure boundary).
- **More than ~1,000 child workflows from one parent is a soft design smell**, well before the hard limit — revisit the fan-out shape, batch via intermediate parents, or partition.
- starting hundreds may already create latency concerns
- parent-child state sharing must happen through signals or explicit communication

### Questions to ask

- Why is this a child workflow instead of an activity?
- How many children can one parent start?
- Does the parent need the child result?
- What happens to children if the parent closes?

## 4. Activity review

### Core principle

Activities must be idempotent and treated as at-least-once.

### Idempotency

Flag:

- side-effecting activities without idempotency protection
- reliance on "this only runs once" assumptions
- lack of idempotency keys where external actions occur

### Granularity

Evaluate whether activities are too broad or too granular.

Guidance:

- bundling multiple operations is acceptable if timeout and retry boundaries are intentional
- too much bundling reduces observability and makes retries too coarse
- too much fragmentation increases event history and orchestration complexity

### Long-running activities

Verify:

- long-running activities heartbeat
- heartbeat timeout is short enough for timely failure detection
- heartbeat payload contains resumable progress where useful

Baseline: the SDK throttles heartbeats to roughly **80% of the heartbeat timeout** (frequent `RecordHeartbeat` calls are batched and not all reach the server), so set the heartbeat timeout with that throttling in mind.

### Payload size

Concrete platform thresholds to flag against:

- Single request/payload hard limit: **2 MB**. Self-hosted logs a warning at **256 KB** ("Blob size exceeds limit"). Treat a payload that can exceed 2 MB as `fail` (hard); one routinely over 256 KB as `needs_revision` (warn).
- Each gRPC message and each Event-History transaction hard limit: **4 MB**. Note a single Workflow Task can breach 4 MB by scheduling many small-payload commands at once, even when no individual payload is large.

Flag:

- large inputs or outputs that risk the 2 MB payload / 4 MB transaction limits
- designs that pass blobs instead of references
- repeated large payload serialization in workflow history

Recommend:

- pass references instead of full payloads
- move data-heavy handling into activities
- compress payloads through a converter where appropriate

### Polling

Evaluate whether polling is designed efficiently.

Guidance:

- frequent polling should usually happen inside one activity loop
- infrequent polling can often use activity retries
- signals or async activity completion may be better than polling

### Timeouts

Verify:

- each activity has intentionally chosen timeout settings
- Start-To-Close is usually set
- Schedule-To-Close is used intentionally
- Schedule-To-Start is usually unset unless needed for host-specific routing or queue-unavailability detection

Flag:

- identical timeout policies applied blindly to all activities
- server-side timeouts shorter than normal upstream completion time
- duplicate-action risk from retries ignored

### Retry policy

Review baseline — the default Activity RetryPolicy is:

- initial interval **1s**
- backoff coefficient **2.0**
- maximum interval **100x the initial interval** (i.e. 100s by default)
- maximum attempts **unlimited** (`0`)
- `nonRetryableErrorTypes` empty

Judge the design's retry policy as an *intentional deviation* from these defaults, not in a vacuum.

Flag:

- unlimited retries on activities that call non-idempotent external systems without idempotency keys
- no `nonRetryableErrorTypes` for errors that can never succeed on retry (e.g. validation / 4xx)
- retry intervals or maximum attempts that conflict with the activity's Start-To-Close or the workflow's business deadline

### Local activities

Prefer regular activities unless there is a specific need for:

- very high throughput
- very short-lived work
- large fan-out of short tasks

Flag local activities that:

- run longer than a few seconds
- are used without understanding tradeoffs
- require worker-side rate limiting or routing they cannot support well

### Cancellation

Verify cancellable activities heartbeat, or otherwise use supported semantics correctly.

## 5. Signal review

Signals are appropriate when workflow state must change during execution.

### Required understanding

Signals are:

- recorded in event history
- delivered with the next workflow task
- ordered per workflow execution
- subject to replay and determinism requirements

### Flag:

- signal handlers that perform heavy logic
- signal handlers invoking activities directly without strong reason
- non-idempotent signal handlers
- signal rates too high for one workflow execution
- signal volume that risks history growth or blocks Continue-As-New

### Best practice

Signal handlers should usually:

- update workflow state only
- avoid expensive computation
- let main workflow logic react afterward

### Signal-with-Start

Verify whether the design uses **Signal-with-Start** when it needs to deliver a signal to a workflow that may not exist yet — this atomically starts the workflow (if absent) and delivers the signal, avoiding a start/signal race. Flag designs that hand-roll "check existence, then start, then signal" logic that has a race window.

### Questions to ask

- What sends the signal?
- How often can it happen?
- Can duplicates occur?
- Is Continue-As-New required?
- Could the signal rate prevent it?

## 6. Query review

Queries are best for reading workflow state.

### Rules

- queries are synchronous
- queries must be read-only
- queries are available for running and completed workflows, but require a worker on the task queue

### Flag:

- queries that mutate workflow state
- external stores used for live workflow state when queries would be simpler
- assumptions that query data is always available without workers running

## 7. Update review

Updates are appropriate when callers need validated, synchronous workflow state changes.

### Rules

- update handlers must be deterministic
- update handlers must be idempotent
- validation is recommended
- validators must not mutate workflow state
- rejected updates via validation are not written to history

### Flag:

- update handlers that mutate state non-deterministically
- missing validation for business-critical mutations
- designs that ignore latency or handler contention

### Guidance

Calling activities from update handlers is generally acceptable when justified and carefully designed.

If low latency matters, ask whether early-return patterns are needed.

### Update-with-Start

**Update-with-Start** is GA (2025) and is the recommended pattern for atomic idempotent start and read-after-write: it starts the workflow if it does not exist and applies the update in a single call. Verify the design uses it for "start-or-update" / read-after-write flows instead of separate start + update calls that race or require existence checks. Pair it with the Workflow ID Conflict Policy (see section 2) to control collision behavior.

## 8. Worker and task queue review

Check topology and routing for correctness, availability, and intent.

### Best practices

- run at least two workers for high availability
- all workers on the same task queue must register identical workflows and activities that may be dispatched there

### Unique task queues are justified for:

- rate limiting
- routing to special hardware such as GPUs
- worker-local filesystem or privileged environment access
- workload isolation or differentiated priority

### Flag:

- arbitrary task queue splits that add complexity without routing value
- inconsistent registrations on one queue
- assumptions of strict FIFO ordering
- intentional backlog growth without understanding Temporal's consumption semantics

### Rate limiting checks

Inspect whether:

- worker-side concurrency and rate limits are intentional
- server-side task queue activity limits are configured consistently

Note: server-side rate limiting is configured differently on Cloud (namespace settings via UI/tcld) vs self-hosted (dynamic config). Verify the design targets the correct mechanism.

### Questions to ask

- Why are there multiple task queues?
- Are special hardware or trust-boundary requirements involved?
- Is ordering assumed?
- Is backlog growth acceptable?

## 9. Timers, schedules, and cron

### Timers

Verify:

- timers are used for relative delays inside a workflow
- timer durations are at least one second when reliability matters

### Schedules

Use schedules when:

- a whole workflow execution must start at a calendar time
- execution is recurring
- a scheduled launch is more appropriate than an internal timer

Use timers instead when:

- the delay is relative to workflow state
- the delay belongs inside an already running workflow
- schedule action-per-second limits would be exceeded

### Flag:

- schedules used for single delayed starts when a normal workflow plus timer would be simpler
- overlap policy not considered
- jitter not considered when many schedules fire together
- risky backfill strategies

### Cron

Generally recommend schedules instead of cron workflows.

Flag:

- cron used where schedules are better supported
- cron combined with unsafe Continue-As-New assumptions

## 10. Side effects

Use side effects carefully.

### Guidance

- if the side effect can fail, prefer an activity
- side effects are not general-purpose integration hooks

### Flag:

- side effects used for failure-prone work
- side effects treated like normal external integration steps

## 11. Data converter and payload codec review

Check whether serialization, compression, and encryption choices are safe and operationally sound.

### Best practices

- compression is generally recommended
- encryption may justify a custom converter or codec
- key rotation must be considered if encryption is used
- search attributes are not protected by custom converters or codecs

Note: both Cloud and self-hosted support codec servers for decoding payloads in the UI and CLI. Cloud encrypts data at rest automatically with AES-256-GCM — custom encryption via a Payload Codec is for zero-trust requirements. Self-hosted has no automatic encryption at rest — you must implement a custom Payload Codec if encryption is needed.

### Cross-language datetime/duration warning

Flag designs that:

- assume datetimes or durations serialize consistently across languages
- mix languages without a common converter format

### Latency

Verify whether converter or codec latency:

- contributes to workflow task execution time
- risks workflow task timeout under large histories or high throughput

## 12. Visibility review

### Search attributes

Verify search attributes are used only for operational visibility, not business logic.

Note: both Cloud and self-hosted support custom search attributes, but per-namespace limits differ. Temporal Cloud allows, per namespace: **40 Keyword; 20 each of Bool, Datetime, Double, and Int; 5 KeywordList; 5 Text** — note KeywordList and Text are **5 each, not 20**. There is also a **total search-attribute size cap of 40 KB** per workflow. Self-hosted with SQL (v1.20+) allows fewer per namespace (e.g., ~10 Keyword, 3 of most others), but these defaults shift across server versions — re-verify against the current self-hosted defaults page for the target version. Self-hosted with Elasticsearch has no per-namespace limits but is subject to Elasticsearch mapping limits. Verify limits against the target deployment.

Flag:

- sensitive data in search attributes
- search attributes used to drive workflow decisions
- large duplicate state stored there
- total search-attribute payload approaching the 40 KB per-workflow cap
- assumptions of immediate consistency

### Memos and visibility APIs

Note:

- memos are eventually consistent
- visibility APIs are eventually consistent
- control flow must not depend on immediate freshness

## 13. Versioning and replay-safety review

Check whether workflow evolution is safe for replay and in-flight executions.

### Best practices

- Worker Versioning is **GA across SDKs** via Worker Deployments + Build IDs. It is no longer limited to short-running workflows: **Upgrade on Continue-as-New** lets long-running, pinned-version workflows adopt a new version at each Continue-As-New boundary without patching. (The earlier "prefer worker versioning only for short-running workflows" guidance is outdated.)
- Distinguish current **Worker-Deployment-based versioning** (the GA path) from the now-**legacy Build-ID-based worker versioning** — recommend the Worker Deployment model for new designs.
- use workflow `patch()` / `GetVersion` APIs when in-flight executions must replay safely across an incompatible code change
- do not let patches accumulate forever
- remove version markers only after in-flight execution and retention concerns are handled

### patch() / GetVersion vs Worker Versioning — decision rule

- Use **`patch()` / `GetVersion`** for inline, incremental changes to a single workflow's logic that must stay replay-compatible with executions already in flight.
- Use **Worker Versioning (Worker Deployments)** to pin whole workflow versions to worker builds and roll out new code as a deployment — especially with Upgrade on Continue-as-New for long-running workflows — when you want to avoid threading patch markers through the code.

### Flag:

- workflow logic changing without replay-safe versioning
- patches with no retirement plan
- long-running workflows ignoring patch retention needs
- reliance on legacy Build-ID worker versioning for new designs without considering Worker Deployments
- absent replay-based testing (see below)

### Testing and replay safety

Replay-safety testing is a production-readiness review item, not optional. Confirm the design's test strategy names a concrete flow:

- **`WorkflowReplayer` / replay-from-history**: replay captured Event Histories against the current workflow code to catch nondeterministic changes before they ship.
- **Time-skipping test server**: exercise timers, schedules, and long waits in unit tests without real-time delays.
- **CI replay gate**: run replay tests in CI against captured production histories so incompatible changes fail the build rather than breaking in-flight executions.

## 14. Continue-As-New and long-running workflows

Check whether long-lived workflows remain healthy over time.

### Best practices

- use Continue-As-New before history becomes too large
- pass forward enough state to resume safely
- recalculate and re-establish timers after Continue-As-New
- ensure pending activities and handlers are resolved before Continue-As-New

### Flag:

- timers assumed to carry over automatically
- child workflow behavior on parent close misunderstood
- signal or update handlers possibly still running during Continue-As-New
- missing state handoff design

## 15. Sessions and worker-specific routing

### Sessions

Sessions are only available in Go.

Note:

- if a worker process dies, session-related activities may retry together
- sessions should be clearly justified

### Worker-specific task queues

Approve these when used for:

- local files
- privileged environments
- specialized hardware
- sticky locality requirements

## 16. Storage optimization review

Check whether long-running workflows control storage growth and event-history cost.

### Best practices

- keep payloads small
- use references for large objects
- use Continue-As-New strategically
- avoid unnecessary history growth through over-fragmentation or excessive messaging

Note: Cloud retention is configurable from 1-90 days (default 30) via UI or tcld. Self-hosted retention is set when creating or updating a namespace via CLI or SDK. Verify the retention period is appropriate for the workflow's expected duration and audit requirements.

## 17. Saga / compensation review

Multi-step workflows that mutate external systems need a rollback strategy for partial failure.

### Verify

- the design defines **compensating activities** that undo each already-completed step when a later step fails
- compensation runs in **reverse order** of the forward steps (unwind most-recent-first)
- compensations are **idempotent** (they may themselves be retried)
- cleanup is **error-driven**: a failure mid-sequence triggers compensation of the steps that did complete, not a silent abort

### Good fit

- distributed transactions across services where a two-phase commit is not available
- any workflow that performs several externally-visible mutations that must be all-or-nothing

### Flag

- multi-step external mutations with **no compensation strategy** at all
- compensation that assumes a step "could not have partially completed"
- compensations that are not idempotent
- compensation ordering that does not unwind completed steps in reverse

## 18. Nexus and cross-namespace / cross-service contracts

Nexus is **GA** (OSS and Temporal Cloud) and is the recommended pattern for cross-namespace and cross-team/cross-service interaction via typed service contracts. It supersedes ad-hoc "activity-mediated client calls" for crossing namespace or service boundaries.

### SDK constraint

Nexus is currently available in the **Go and Java SDKs** (other SDKs coming). Key this advice to the SDK in use — if the design targets Python/TypeScript/.NET today, Nexus may not yet be an option and a documented interim approach is acceptable.

### Good fit

- one team/namespace exposing a durable operation to another team/namespace behind a stable contract
- cross-service orchestration where you want loose coupling and an explicit API boundary rather than sharing client credentials and calling another namespace directly

### Flag (anti-patterns)

- ad-hoc activity-mediated client calls used to cross a namespace/service boundary where a Nexus contract would be cleaner and is available in the target SDK
- treating Nexus as a low-latency RPC replacement for in-process logic
- assuming Nexus is available in an SDK that does not yet support it

## 19. SDK-specific design constraints

Several design constraints are language/SDK-specific. When reviewing real code, apply the advice keyed to the SDK in use rather than a flattened generic rule.

- **Worker Sessions**: Go SDK only.
- **Nexus**: Go and Java SDKs only (as above).
- **Async / parallel idioms** differ per SDK — Go selectors + futures, TypeScript `Promise.all`, Java `Async` / `Promise`, Python `asyncio`. Judge parallelism against the idiomatic pattern for that SDK.
- **Determinism foot-guns** differ per language — for example Go map iteration order is randomized and must not drive workflow logic; each SDK has its own non-deterministic-API surface (system clock, random, threading) to audit.

When the SDK is unknown, mark SDK-specific checks `inconclusive` and ask which SDK the implementation targets.
