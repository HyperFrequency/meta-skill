# Session corpus & replay

The bake-off is only as trustworthy as the sessions it replays. This file
defines how a recorded session is captured, scrubbed, pinned, split, and
deterministically re-driven under a compaction policy.

## What a recorded session is

A single unit of the corpus is a **`.traj` transcript**: the full ordered event
log of one real agent session, sufficient to replay every turn. It carries:

- The initial task/goal statement and system prompt.
- The ordered turns: each an LLM request (messages + tool schemas), the LLM
  response, and any tool calls with their observations.
- The **keyed context entries** that were managed during the session — skill
  catalog blobs, VFS/snapshot manifests, pinned facts — each with its stable
  `key` (lightspeed's `ContextAppendEntry { key, item }`, verified in
  `crates/api/src/sessions.rs`; re-sending a key with the same content is a
  no-op, so the key doubles as the survival probe handle).
- A **ground-truth completion oracle**: the deterministic check that says
  whether the downstream task actually finished (file state, test pass, exact
  answer). This is what "solve-rate" is measured against — never a judge's
  opinion of whether it *looks* done.

Sources feeding the corpus mirror the loop-3 ingest set: harness OTel spans,
first-party `.traj` artifacts every D13 runner emits, lightspeed/forge-code
session event logs, and parsed on-disk agent session logs.

## Scrub before storage (non-negotiable)

Every session passes a scrubber **before** it is written to the corpus store:
secret scanner → injection quarantine (ACIP) → anonymizer. A recorded session is
raw production data; it may contain credentials, PII, or prompt-injection
payloads. Never commit an unscrubbed transcript, and never read one back into a
model context without confirming it cleared the scrubber. Credentials in a
transcript are treated exactly like credentials anywhere: surfaced by name,
never echoed.

## Pinning and splits

The corpus is a **versioned, pinned dataset**. Every bake-off run records the
`corpus_version` it ran against so a policy's win/loss stays interpretable after
the corpus grows. Two rules keep the gate honest:

- **Held-out split.** A gated slice of the corpus is withheld from policy tuning
  (GAIA-style contamination control). A policy tuned on the visible split is
  gated on the held-out split; if you can only win on the visible split you have
  overfit the policy to the corpus.
- **Difficulty tiers.** Sessions are tagged Easy / Medium / Hard by context
  length and re-fetch pressure (how much the task depends on early context that
  compaction is likely to drop). Hard sessions — long, with critical early
  artifacts — are where lossy policies fail; a policy that only survives Easy is
  not shippable.

Corpus construction and tuning are a *separate step* from the bake-off. The
policies under test can never edit the corpus (the class-7 anti-gaming rule).

## Deterministic replay under a policy

Replaying a session under a `Condenser` is **not** re-running the original
agent free-form. It is a controlled re-drive of the recorded turns with the
condenser spliced into the context-assembly step:

```
for each recorded turn t:
    ctx = assemble_context(history, keyed_entries)
    if condenser.should_compact(ctx, token_count(ctx)):
        (ctx, record) = condenser.compact(ctx, protected_keys)
        emit CompactionRecord(record)               # scored later
    response = drive_turn(ctx, t)                    # see replay modes below
    history = history + [response, observations(t)]
```

**Replay modes** (pick per corpus, pin per run):

- **Fixed-response replay (deterministic core).** The LLM responses are the
  *recorded* ones. This isolates the pure effect of compaction on what
  information reaches each turn — if a policy drops an artifact the recorded turn
  needed, the mismatch is visible without paying for live generation. Best for
  the regression gate: cheap, deterministic, no LLM noise.
- **Live re-drive (behavioral replay).** From the compaction point onward, the
  agent generates fresh responses against the compacted context and may
  **re-fetch** dropped information via tool calls. This is what actually
  exercises tokens-per-task *including re-fetch cost* — the honest metric — and
  what reveals whether the agent recovers from a lossy compaction. Runs with the
  N-trial + variance protocol (n≥3) because live generation is noisy.

The two modes answer different questions; a full bake-off uses fixed-response for
structural/keyed-entry assertions and live re-drive for the tokens-per-task and
solve-rate scores. Both use lightspeed's replay-safety discipline: workflow-time
only, no wall-clock/rand in the replay engine, so a replay is reproducible.

## Probe injection for retention scoring

Knowledge-retention (see `metrics-and-gates.md`) is measured by **probes**: at
recording time (or synthesized after), attach a small set of question/answer
probes whose answers depend on information that lives in the middle of the
session — exactly the span a lossy policy is tempted to drop. After compaction,
pose the probe and check the answer against the recorded oracle.

Probe design rules:

- **Probe the droppable middle, not the preserved edges.** A probe answerable
  from the first or last few turns tests nothing — the U-curve keeps those.
- **Anchor to concrete artifacts** (a file path modified in turn 12, a decision
  made in turn 20), so the probe has a deterministic oracle and is not a
  judge-only soft score.
- **Keep probes out of the context.** Inject them as a separate post-compaction
  turn; never let a probe's text sit in the history it is testing.

Probes make "did the summary actually preserve what mattered" a number, and they
are the raw material the information-loss judge corroborates.

## Corpus growth via trace promotion

The corpus is not static: real production stalls and degraded runs mined by
loop-3 are promoted into new fixtures (LangSmith-style trace→dataset promotion).
When a policy ships and later produces a degraded run in production, that
transcript becomes a new Hard-tier corpus entry — closing the loop so the next
policy must survive the failure the last one caused.
