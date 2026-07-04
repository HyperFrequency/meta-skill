# Condenser policies

Every compaction policy the bake-off scores sits behind **one trait** so the
runner treats them interchangeably. The independent variable of the whole eval
is *which `Condenser` is installed*; nothing else about the recorded session
changes.

## The `Condenser` trait

A condenser is a pure-ish transform over a conversation plus a trigger predicate.
It never performs task work — it only decides *when* to compact and *how* to
rewrite the history into fewer tokens while a set of protected (keyed) entries
pass through untouched.

```
trait Condenser {
    /// Cheap, deterministic: given the current context and a token count,
    /// decide whether compaction should fire this turn.
    fn should_compact(&self, ctx: &Context, token_count: usize) -> bool;

    /// Rewrite the context into a smaller one. MUST preserve every entry whose
    /// key is in `protected_keys` verbatim (the keyed-entry survival contract).
    /// Returns the new context plus a CompactionRecord (what was dropped,
    /// what was summarized, token deltas) for scoring.
    fn compact(&self, ctx: &Context, protected_keys: &KeySet)
        -> (Context, CompactionRecord);

    fn id(&self) -> &str;          // stable policy id, goes into _llm_scores
    fn version(&self) -> &str;     // policy version, pinned per run
}
```

`should_compact` and `compact` are the two seams the four policies below fill.
`CompactionRecord` is what the scorer reads (see `metrics-and-gates.md`): dropped
message indices, produced summary text, pre/post token counts, and the set of
keyed entries it claims to have preserved (verified independently, never
trusted).

The trigger side generalizes forge-code's `Compact` config, whose
`should_compact(context, token_count)` fires on any of several thresholds
(verified in `crates/forge_domain/src/compact/compact_config.rs`):

- `token_threshold: Option<usize>` — compact when the context reaches N tokens.
- `turn_threshold: Option<usize>` — compact every N assistant turns.
- `message_threshold: Option<usize>` — compact at N messages.
- `on_turn_end: Option<bool>` — evaluate the trigger at end-of-turn.

Pin the trigger config per run; a policy's trigger is part of its identity, so
"keep-first at token_threshold=60k" and "keep-first at token_threshold=120k" are
two distinct policies in the bake-off, each with its own `_llm_scores` rows.

## Policy 1 — `none` (control)

No compaction. `should_compact` always returns false; `compact` is never called.
This arm is mandatory: it establishes the **solve-rate ceiling** and the
**quadratic context-growth curve** that every other policy is measured against.
Without it you cannot tell whether a policy's solve-rate is "as good as no
compaction" or merely "as good as some other lossy policy."

## Policy 2 — keep-first + LLM-summarize (OpenHands recipe)

The workhorse. Keep the first `keep_first` turns verbatim (they carry the task
statement and the irreplaceable early context), and when the message count
exceeds `max_size`, LLM-summarize the *truncated middle span* into a compact
block, leaving the tail recent turns intact.

Reference parameters from the OpenHands methodology cited in the class-7 spec:
`keep_first = 4`, `max_size = 80`. Treat these as the starting point, not gospel
— they are themselves tunable and each setting is a distinct policy.

Two properties make this the default recommendation of `ce-context-compression`
(anchored iterative summarization):

- **Summarize only the newly-truncated span** and merge into the running
  summary, rather than regenerating the whole summary each trigger. Regeneration
  accumulates drift; incremental merge does not.
- **Mandatory structured sections** in the summary (session intent, files
  modified, decisions, open risks, next steps) force preservation of exactly the
  artifact trail whose loss the tokens-per-task metric punishes.

The summary itself is a scored artifact — the **information-loss judge** grades
it (see `metrics-and-gates.md`). A summary that reads well but silently drops a
modified-file reference will pass a shallow probe and fail this judge.

## Policy 3 — provider-native (lightspeed `CompactionPolicyInput`)

Delegate compaction to the provider's own context-management machinery instead
of doing it in-harness. Verified shape from lightspeed
(`crates/api/src/sessions.rs`) — a tagged enum set on the session's
`ContextConfigInput { compaction }` and patchable via `ContextConfigPatchInput`:

```
enum CompactionPolicyInput {          // serde tag = "mode"
    Disabled,
    ProviderTriggered {
        compact_threshold_tokens: Option<u32>,   // provider compacts at this budget
    },
    ProviderStandalone {
        compact_threshold_tokens: Option<u32>,
        target_tokens: Option<u32>,              // compact down toward this size
    },
}
```

- **`ProviderTriggered`** — the provider compacts inline during generation once
  the context crosses `compact_threshold_tokens` (e.g. OpenAI `/responses`
  context management).
- **`ProviderStandalone`** — an explicit compaction call that condenses toward
  `target_tokens`, decoupled from a generation turn.

For the bake-off, wrap whichever variant behind the same `Condenser` trait. The
runtime types that carry the outcome — `ContextCompactionRequest`,
`ContextCompactionResult`, `ContextCompactionStatus`,
`ContextCompactionTrigger` (in lightspeed's `llm-runtime`) — populate the
`CompactionRecord` the scorer reads. Because the provider does the work, the
harness cannot see the dropped tokens directly; rely on the provider's reported
deltas plus an independent keyed-entry survival probe (below).

Caveat worth flagging in any provider-native run: provider compaction is a black
box across model/version bumps. Pin the provider model id in the run manifest;
treat a provider version change as a corpus-invalidating event and re-baseline.

## Policy 4 — token-prune (LLMLingua-2, P2 candidate)

Token-classification prompt compression: a small classifier scores each token's
salience and drops the low-salience ones, compressing the prompt without an LLM
summarization pass. Runs locally as an ONNX model via `ort`/`candle` (satisfies
the no-external-service constraint). Source: LLMLingua-2
(https://github.com/microsoft/LLMLingua).

This is explicitly **P2 / optional**. Include it in the bake-off only once the
three P1 policies are wired and the corpus is stable. Its risk profile is
distinct: token-level pruning can shatter tool-call JSON and code blocks, so its
`compact` must be structure-aware (never prune inside a tool schema or a fenced
code region) — a failure mode `ce-context-compression`'s gotchas call out
directly.

## Composing a policy from the Evict/Retain algebra

forge-code's `CompactionStrategy` (verified in
`crates/forge_domain/src/compact/strategy.rs`) is a small algebra for expressing
*how much* to compact, independent of the summarize/prune mechanism:

```
enum CompactionStrategy {
    Evict(f64),     // evict this fraction of the compactible span
    Retain(usize),  // always preserve the last N messages
    Min(Box<CompactionStrategy>, Box<CompactionStrategy>),  // the smaller budget
    Max(Box<CompactionStrategy>, Box<CompactionStrategy>),  // the larger budget
}
```

Constructors: `evict(percentage)`, `retain(preserve_last_n)`, and the combinators
`min`/`max`. `to_fixed(context)` resolves the strategy to a concrete message
count, and `eviction_range(context)` returns the `(start, end)` span to compact.
Two behaviors matter for correctness and are worth reproducing:

- **System messages are skipped** — the eviction budget is computed over
  non-system messages only; the system prompt is never a compaction target.
- **The span starts at the first assistant message** and preserves the last N
  (`find_sequence_preserving_last_n`); if `retain >= len`, there is nothing to
  compact and `compact` is a no-op.

Use `Min`/`Max` to combine a percentage floor with an absolute retention window,
e.g. "evict 40% but always keep the last 8 messages":
`evict(0.4).max(retain(8))`. This algebra parameterizes policies 2–4; it is
*not* itself a policy.

## Registering a policy for the bake-off

A policy enters the run manifest as `{id, version, condenser_config, trigger,
strategy}`. The manifest is pinned and hashed per run so results stay
interpretable. Adding a policy is a manifest edit plus a `Condenser` impl — never
a change to the scorer or the corpus, which are held disjoint from the policies
under test (the class-7 anti-gaming rule).
