---
name: strategy-translator
description: >
  Translate and extrapolate trading strategies across code formats (basic Python, vectorbt,
  NautilusTrader Python, NautilusTrader Rust, Pine Script v6, C++) and across human
  formats (spoken/blog/social media, academic papers). Use whenever the user wants to
  port a strategy between frameworks, rewrite a Pine Script idea in vectorbt or Nautilus,
  turn a research paper into runnable code, draft a Twitter/blog explainer of an existing
  strategy, or vice versa. Trigger even when the user does not say "translate" — phrases
  like "port this to Nautilus", "make this work in vectorbt", "give me the Rust version",
  "explain this strategy on Twitter", "what would this look like as a paper", or "I read a
  paper, can you implement it" all qualify. Always invoke this skill before hand-rolling
  any cross-framework strategy port.
version: "2.0.0"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill, Agent
---

# Strategy Translator

## Required tooling — the unified gateway contract

When working with strategy code in any framework, **always** route documentation lookup, AST parsing, and code-graph queries through the unified mcp2cli gateway (see the `neuro-harness` skill in this repo for the full endpoint table). Specifically:

| Task | Use | Why |
| --- | --- | --- |
| Confirm current API surface of a target framework | `docs-dual-lookup` skill (Context7 + Auggie in parallel) | Catches API drift between SDK versions before you write the wrong import. Auggie validates against the actual repo on `develop`; Context7 against curated upstream docs. |
| Parse / query the source strategy | `tree-sitter` skill via `mcp2cli tree-sitter parse|query` | Get reliable AST nodes (function defs, calls, decorators, identifier locations) instead of grepping. Required for Pine v5/v6 because nothing else parses Pine reliably. |
| Locate symbols / cross-references inside an existing strategy codebase | `mcp2cli gitnexus` or the `gitnexus-exploring` skill | Code-graph queries beat naive grep when porting touches many call sites. |
| LSP-style "what is this symbol" lookups | The IDE LSP if available; otherwise tree-sitter via the gateway | True LSP integration is via the editor, not the MCP layer. The gateway exposes tree-sitter as the closest substitute. |

**Do not** hand-roll API recommendations from training data when porting between frameworks. The cost of a wrong import path or a removed method is much higher than the 30 seconds it takes to query the gateway. Treat the docs lookup as part of the translation contract, not an optional check.

If `neuro-harness` is unreachable in this environment (no compose stack running, sandboxed runtime), say so explicitly and degrade to: Context7 directly, then WebFetch on the framework docs site, then training-data recall as last resort — flagging which source each claim came from.

---

This skill turns one representation of a trading strategy into another. There are two
modes, and they have very different rigor requirements:

- **Translate** — between code formats. The semantics of the strategy are fixed; only the
  syntax, idioms, and execution model change. The bar is *behavioral equivalence*: same
  signals, same fills (modulo framework-specific bar timing), same accounting.
- **Extrapolate** — between code and human formats (spoken/blog/social media, academic
  papers). The meaning is preserved but the form is creative. The bar is *faithfulness +
  audience fit*. Extrapolation needs deeper reasoning because you are inferring intent,
  filling in motivation, and choosing what to omit.

The user may ask for either, and the workflow is different. Read the **Mode Selection**
section below before doing anything else.

## Supported formats

Code formats (translate):

| Format | Reference file | Typical use |
|---|---|---|
| Basic Python (pandas/numpy) | `references/python-basic.md` | Research, prototypes, the lingua franca |
| vectorbt | `references/vectorbt.md` | Vectorized backtests, parameter sweeps, fast iteration |
| NautilusTrader (Python) | `references/nautilus-python.md` | Event-driven backtests, paper trading, live |
| NautilusTrader (Rust) | `references/nautilus-rust.md` | High-perf live execution, latency-sensitive paths |
| Pine Script v6 | `references/pinescript-v6.md` | TradingView charts, alerts, visual debugging |
| C++ | `references/cpp.md` | Embedded/HFT engines, exchange-collocated systems |

Human formats (extrapolate):

| Format | Reference file | Typical use |
|---|---|---|
| Spoken / blog / social media | `references/natural-language.md` | Explain to humans, marketing, education |
| Academic document | `references/academic-extrapolation.md` | Whitepapers, lit reviews, formal write-ups |

The canonical worked example — a multi-timeframe EMA cross strategy rendered in **all
six** code formats plus blog and academic versions, with a per-format diff explanation —
lives in `references/mtf-ema-cross-example.md`. Read it once before doing your first
translation; it shows the patterns the rest of the skill assumes.

## Pine Script tooling

When Pine Script v6 is the source or target, use these tools before emitting or
extracting any non-trivial logic:

- **`pine-lsp` (from `folknor/pine-tools`)** — full LSP for Pine v6: completion,
  hover with types, diagnostics, go-to-definition, references, rename, semantic
  tokens, inlay hints. Registered as a custom Serena language adapter; drive it
  through Serena's `find_symbol`, `get_symbols_overview`, and
  `find_referencing_symbols` on any `.pine` file. Use when Pine is the **source**
  to extract the behavioral contract (translate step 2) without hand-parsing.
- **`pine-validate` CLI (same repo)** — one-shot linter. Run after emitting
  Pine v6 as a **target**; non-zero exit means TradingView's compiler would
  reject it — re-emit before returning to the user.
- **`tree-sitter-pine` (from `zelosleone/pinescript-vsc-server-rust`)** — raw
  tree-sitter grammar. Reach for it only when you need a concrete syntax tree
  for programmatic extraction (e.g. enumerating every `ta.*` call with its args
  for a 1:1 vectorbt mapping). Prefer `pine-lsp` for navigation; fall through
  to tree-sitter only when the LSP's semantic view is insufficient.

If the LSP is not available in the current environment, say so in your reply
and fall back to careful manual reading — do **not** silently degrade to regex
pattern-matching and claim the same rigor.

See `references/pinescript-v6.md` for the full catalogue of pitfalls (Wilder
smoothing, biased stdev, look-ahead, crossover state, fill timing) that apply
to every Pine translation.

## Mode selection

Decide first which mode you are in. The same input can mean different things:

- "Port this Pine Script to Nautilus" → **translate** (code ↔ code).
- "Rewrite this for vectorbt so I can sweep parameters" → **translate**.
- "Turn this paper into a vectorbt notebook" → **extrapolate** (academic → code), then
  **translate** if the user wants other formats too.
- "Write a Twitter thread explaining this strategy" → **extrapolate** (code → social).
- "What would this strategy look like as an academic paper" → **extrapolate** (code → academic).

If the request is ambiguous, ask one targeted question. Don't default to the most
elaborate workflow.

## Translate workflow (code ↔ code)

1. **Identify the source and target formats** explicitly. State them back to the user in
   one line so any misread surfaces immediately.
2. **Read the source carefully** and write down — internally or in your reply — the
   strategy's *behavioral contract*: instruments, bar timeframes, indicators (with
   parameters), entry conditions, exit conditions, position sizing, risk rules, and any
   look-ahead or warmup requirements. Translation errors almost always come from skipping
   this step.
3. **Verify current API surface — MANDATORY live lookups.** Library APIs drift; do
   not trust training-data recall. Before emitting any non-trivial framework call,
   run the appropriate lookup and cite the source in the Diff vs source section.
   Translations without citations are flagged by the consortium judge as unverified.

   | Target framework | Required lookup |
   |---|---|
   | vectorbt-pro | Context7 `/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt` (13k snippets) — see `references/vectorbt-pro.md` |
   | vectorbt (vanilla) | Context7 `/polakowo/vectorbt` or `/websites/vectorbt_dev` |
   | nautilus-trader | Context7 via `mcp__context7__resolve-library-id` with `libraryName="nautilus-trader"`; for HF fork, `/deep-tool-wiki` |
   | pandas / numpy / scipy | Context7 (well-indexed, standard fallback) |
   | Pine Script v6 | `pine-lsp` via Serena (symbols + hover) + TradingView docs |
   | C++ standards | Context7 `/websites/en_cppreference_com` for stdlib |

   Additionally, **always consult the neuro-quant-vault** via
   `mcp__neuro-link-recursive__nlr_wiki_search` with the framework name. Vault entries
   under `02-KB-main/` supersede static references when present — they capture
   project-specific conventions the user has curated over time. If the vault returns
   a page at `confidence >= 0.7`, prefer its guidance over generic library docs.

   Use `/docs-dual-lookup` as the umbrella skill for most lookups (runs Context7 +
   Auggie in parallel when both are available). Use `/deep-tool-wiki` specifically
   for HyperFrequency-forked tools (turbovault, pinelsp, nautilus-trader-hyperliquid,
   etc.) which have dedicated DeepWiki pages.
4. **Open the relevant reference files** for the source and target formats. The skill
   ships target-specific files:
   - `references/pinescript-v6.md` — Pine semantics + pitfall catalogue (apply to every
     translation where Pine is source or target).
   - `references/vectorbt-pro.md` — VBT Pro (paid) specifics: NB indicators, `bb.middle`,
     sizing recipes, `adjust=False` defaults. **Read when target is vectorbt-pro.**
   - `references/nautilus.md` — Nautilus Python + Rust: event-driven mental model,
     indicator library, crossover state, fill timing. **Read when target is nautilus.**

   These files cite current Context7 library IDs; use them as a pointer to the live
   source, not as a substitute for it. If the source or target is Pine v6, also see
   **Pine Script tooling** above — use `pine-lsp` via Serena to extract symbols
   before manual parsing, and run `pine-validate` on emitted Pine before returning it.
5. **Emit the translated code** in a single fenced code block. Then, immediately below
   the block, write a **`### Diff vs source`** section with 3–7 bullets explaining what
   changed and *why* — not just what is different syntactically, but what semantic risks
   the new framework introduces (e.g. "vectorbt fills on the next bar's open, so I
   shifted signals by 1 to match the source's bar-close fill assumption").
6. **Behavioral equivalence check.** State which behaviors should match across versions
   and which intentionally differ. If you cannot make them match (e.g. Pine Script
   strategies always run on close, but the user wants intra-bar entries in Nautilus),
   call it out.
7. **Offer to round-trip.** If the user asked for one target, mention that you can also
   produce the other formats from the same contract — many users want vectorbt for
   sweeps and Nautilus for live, off the same source.

## Extrapolate workflow (code ↔ human / academic)

Extrapolation needs more reasoning than translation because you're filling in
information that isn't in the source. Take your time. Think before writing.

1. **Identify direction.** Code → human, human → code, or human → human. Each has its
   own reference file (`natural-language.md`, `academic-extrapolation.md`).
2. **Reason about intent.** Why does this strategy work, what is the edge, what assumption
   is it betting on? For code → academic this becomes the abstract and motivation. For
   code → social this becomes the hook. For paper → code this is what tells you which
   details are load-bearing and which are decoration.
3. **High-reasoning lookups — mandatory for any non-trivial extrapolation:**
   - **`/deep-tool-wiki`** — invoke whenever extrapolation touches a HyperFrequency-forked
     library or any tool the user has indexed there. It returns the layered InfraNodus +
     Context7 + Auggie synthesis, which is what you need to ground claims about how a
     library actually works rather than guessing.
   - **`/alpha-extract-consortium`** — invoke whenever the source or target is an
     **academic document**. This skill will be created next; until it exists, fall back to
     the `paper-lookup` and `literature-review` skills, plus `docs-dual-lookup` for any
     library APIs the paper references. When the consortium skill is available, prefer it
     for paper ↔ alpha extraction because it will handle the assumption-mining,
     reproducibility-flagging, and citation-grounding steps that this skill does not.
   - **`docs-dual-lookup`** — invoke for any third-party library you mention by name in
     the extrapolated output. Faithfulness to the actual API surface matters even in a
     blog post; readers will copy-paste.
4. **Match audience register.** A Twitter thread is not a methods section. See
   `references/natural-language.md` for the register cheatsheet (spoken / blog / social
   each have different rules around length, jargon density, hooks, and CTAs).
5. **Cite what you grounded.** When extrapolating from a paper, cite it. When grounding a
   claim on a `deep-tool-wiki` answer, say which tool/library backed it. The user reads
   these to check your work.
6. **Round-trip sanity check.** After extrapolating code → academic or paper → code, ask
   yourself: "If I gave the output back to a fresh agent and asked for the inverse
   translation, would it land near the original?" If not, you've drifted. This is the
   single most useful check for catching hallucination in extrapolation mode.

## Inputs to ask for (only if missing)

Don't interrogate. Most users give you enough on the first message. Only ask when one of
these is genuinely missing and you cannot proceed:

- **Source format & target format** (if either is ambiguous).
- **Strategy semantics** the source code does not make explicit — usually only an issue
  for hand-written pseudocode or natural-language descriptions.
- **Execution assumptions** for code targets: bar-close vs intrabar entries, fees,
  slippage model, sizing rule. Pick sensible defaults and *state them* if the user did
  not specify; do not block on this.
- **Audience** for human targets: technical blog vs non-technical Twitter vs LaTeX paper.

## Output structure

Code translations:

````
### Target: <framework>

```<lang>
<code>
```

### Diff vs source
- <change 1 — what + why + semantic risk>
- <change 2>
- ...

### Behavioral equivalence
- Matches source on: <list>
- Intentionally differs: <list, with reason>
- Verify with: <one-line how-to-check>
````

Extrapolations (code → human):

```
### <Format>: <title>

<the prose / thread / post, in the right register>

### Faithfulness notes
- <claim 1 in the prose> ← grounded in <source line / paper section / tool lookup>
- <any approximation or simplification you made and why>
```

Extrapolations (paper → code): use the **translate** output structure but add a
**`### Paper → code mapping`** section listing each load-bearing claim from the paper and
the line(s) of code that implement it.

## Target-specific failure modes — check before emitting

These are the five failure modes that scored vectorbt translations below the
4.0 pass threshold in cycle-5b iter-4. Emit code that satisfies every row:

| Failure mode | Wrong | Right |
|---|---|---|
| Double-shifted crossover with pre-shifted bands | `(a > b.shift(1)) & (a.shift(1) <= b.shift(2))` | `(a > b) & (a.shift(1) <= b.shift(1))` — same `b` on both legs. If `b` is ALREADY `upper.shift(1)`, do NOT shift it again. |
| Fill timing misstated as next-bar OPEN | "`shift(1)` approximates next-bar open" | `Portfolio.from_signals` defaults to signal-bar **CLOSE**; `shift(1)` → next-bar CLOSE. For next-bar OPEN use `price=open.shift(-1)` or document the residual bias. |
| Sizing via `np.inf` for percent-of-equity | `size=np.inf, size_type='amount'` | `size=1.0, size_type='percent'` (fractional 0–1 in VBT Pro 0.26+). `np.inf` is a max-available sentinel, not "100%". |
| `SizeType.TargetPercent` scale mismatch with Pine's `percent_of_equity=100` | `size_type=SizeType.TargetPercent, size=100` (→ would target 100× equity!) | Use **`SizeType.TargetPercent100`** (accepts [0,100]) OR `SizeType.TargetPercent` with `size=1.0` (fractional [0,1]). Pine's `strategy.percent_of_equity=100` ↔ `SizeType.TargetPercent100, size=100` OR `SizeType.TargetPercent, size=1.0`. Confirmed by the VBT Pro RefGraph enum catalog. |
| Look-ahead via `ta.highest`/`ta.lowest` without prior-bar shift | `upper = ta.highest(high, 20)` used directly as a breakout level | `ta.highest(high, 20)` **includes the current bar** in Pine v6. For prior-bar breakout level use `ta.highest(high, 20)[1]`. When porting, the Pine source's `[1]` offset is load-bearing — do NOT strip it during translation. |
| Wilder/EMA confusion | Treating `ta.rsi` as EMA-smoothed | `vbt.RSI` uses Wilder (ewm alpha=1/N) — matches Pine `ta.rsi` 1:1. `ta.sma/ta.stdev` translations still need `ddof=0` + simple rolling mean. |
| Crossover re-firing across re-entries | Plain `>`/`<` comparison used as signal | Use crossover predicate (exactly one True at the transition) and enforce one-position-at-a-time state via explicit entry/exit masks. |
| Two competing `from_signals` calls emitted | Two `Portfolio.from_signals(...)` blocks showing different fill conventions, tied together with a no-op `if False else` ternary | **Emit exactly ONE `Portfolio.from_signals` call.** Pick one fill convention (signal-bar close OR next-bar open) and commit — if you pass `price=open_series` for next-bar-open semantics, do it directly; don't emit a shadowed alternate + commented/no-op switch. The diff_vs_source block documents the choice, not the code. |

Pine target, Nautilus target, C++ target each have their own failure-mode
tables — see the matching `references/<target>.md` for those. The rule above
is: **don't skip this table**; every vectorbt emission must justify each row.

### Vectorbt — forbidden constructs (iter-2 regressions)

Ship **none** of these. If you typed one, delete it before emitting:

- `size=np.inf` combined with `size_type='percent'` — the two are incompatible.
  Use `size=1.0, size_type='percent'` for 100% of equity, or `size=np.inf` with
  `size_type='amount'` (never `'value'`, never `'percent'`).
- Any `if False else ...` ternary or `x = a if False else b` construct — dead
  code. Pick one branch at authorship time and emit only that.
- More than one `Portfolio.from_signals(...)` call in a single translation.
  Commit to one fill convention and emit one call.
- `entries.shift(1)` applied on top of a crossover mask that already uses
  `prev_series = series.shift(1)` in its comparison — that's the double-shift
  trap. The prior-bar comparison in the crossover already shifts; don't shift
  the resulting boolean mask again.

### Vectorbt — anchor on the canonical example

Before emitting a vectorbt translation, read
`references/mtf-ema-cross-example.md` end-to-end. That file is the
reference shape every vectorbt emission should structurally resemble:
one `Portfolio.from_signals`, explicit sizing with `size=1.0, size_type='percent'`,
crossover predicates without double-shift, a `diff_vs_source` that honestly
states the Pine-vs-vbt fill-timing gap rather than trying to paper over it
with dead code. If your emission structurally diverges, stop and re-read
that file.

### Deep-tool-wiki cross-references

Full consolidated catalogues live in the deep-tool-wiki / llm-wiki (offline):

- **vectorbtpro:** `02-KB-main/vectorbtpro/pitfalls.md` — fill-timing,
  sizing scale, enum semantics (`SizeTypeT`, `ConflictModeT`,
  `OppositeEntryModeT`), `adjust` default mismatches, `ddof` conventions.
- **pine-script v6:** `02-KB-main/pine-script/pitfalls.md` — pitfalls
  V6-A through V6-T, including `int/int` truncation change (v5→v6), `ta.*`
  inside `if` blocks, `strategy.exit qty_percent` semantics, `trail_points`
  in ticks, `time`/`hour`/`dayofweek` as series, `alertcondition` vs
  `alert`, `use_bar_magnifier` free-plan no-op.
- **nautilus-trader:** `02-KB-main/nautilus-trader/pitfalls.md` —
  py↔rust boundary, v1/v2/pyo3 runtime divergence.

When the translator encounters a pattern that feels ambiguous, read the
relevant `pitfalls.md` — it's faster than rediscovering the same trap.

## Anti-patterns

- **Don't translate without reading both reference files.** Skipping them produces
  syntactically-valid-looking code that subtly misbehaves on bar boundaries, lookahead,
  or fill timing. These are exactly the bugs that survive review.
- **Don't extrapolate from a paper without invoking `/alpha-extract-consortium`** (or its
  fallbacks until it exists). Papers omit assumptions on purpose; mining them is the
  whole point of that skill, and doing it by hand is where hallucinations enter.
- **Don't skip the diff explanation.** The diff is the thing the user reviews to trust the
  translation. A code block alone is half the deliverable.
- **Don't fabricate library APIs.** If you cannot verify a function/class exists in the
  current version of vectorbt or nautilus_trader, say so and run `docs-dual-lookup`
  before emitting it. This is the #1 source of broken translations.
- **Don't claim vectorbt's `.ewm()` matches Pine `ta.ema` by default.** It doesn't —
  pandas (and therefore vectorbt's EWM-backed indicators) default to `adjust=True`,
  a bias-corrected weighting that diverges from Pine's recursion. The first ~20 bars
  drift visibly and the divergence doesn't damp out cleanly. Always pass `adjust=False`
  *and* run the vectorbt validation recipe in `references/pinescript-v6.md` before
  asserting numeric equivalence. Related: `size=np.inf` with `size_type='percent'` is
  a misuse — use `size=1.0` (fractional) and state the vectorbt version's percent
  convention (0.0–1.0 in 0.26+, 0–100 earlier).
- **Don't emit a vectorbt-pro call without a Context7 citation.** VBT Pro's NB-level
  indicators (`bbands_1d_nb`, `atr_nb`, etc.) default to Pine-compatible params —
  but the hand-rolled pandas path does not. The shakedown judge consortium penalises
  translations that assert API behaviour without evidence. Cite the Context7 snippet
  heading (source: `/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt`) for each
  non-trivial VBT Pro function in the Diff vs source section.
- **Don't skip the vault check.** `mcp__neuro-link-recursive__nlr_wiki_search` with
  the framework name surfaces project-specific idioms curated by the user that
  static references cannot capture. A missed vault hit means re-discovering what
  the user already wrote down.
- **Don't call Pine's `ta.ema` a Wilder smoother.** `ta.ema` uses α=2/(n+1);
  `ta.rma` is Wilder (α=1/n). `ta.rsi` and `ta.atr` use `ta.rma` internally,
  not `ta.ema`. Mislabelling in the diff propagates the confusion even when
  emitted code happens to be right. See `references/pinescript-v6.md` Pitfall 1
  for the mapping table.
- **Don't double-shift a pre-lagged indicator in a crossover check.** When Pine
  writes `ta.crossover(close, upper[1])`, the `[1]` already applied the lag.
  The prior-bar half of the pandas crossover expression compares to the SAME
  pre-lagged series, not to a further-shifted copy. See `references/pinescript-v6.md`
  Pitfall 3b for the decision table.
- **Don't claim vectorbt's `Portfolio.from_signals` fills at next-bar open by
  default.** The default fill price is the signal bar's CLOSE. To emulate Pine's
  `process_orders_on_close=false`, pass `price=open_next` explicitly. See
  `references/vectorbt-pro.md` fill-timing section for the decision tree.
- **Don't over-engineer the natural-language outputs.** A blog post that reads like a
  methods section has failed. See `references/natural-language.md` for the register
  guidance.

## The canonical example

`references/mtf-ema-cross-example.md` contains a complete multi-timeframe EMA cross
strategy in:

1. Basic Python (pandas)
2. vectorbt
3. NautilusTrader (Python)
4. NautilusTrader (Rust)
5. Pine Script v6
6. C++
7. Blog-post extrapolation
8. Academic-paper extrapolation

Each version is followed by a **Diff vs basic Python** explanation. Read this file
end-to-end before your first translation — every reference file in this skill assumes
you've internalized the patterns there.

---

## Grading rubric contract (for harness integration)

This section is machine-readable by `$RUN_ROOT/harness/` graders. When a
batch-create-eval run invokes this skill and needs to mechanically score the
output, it keys off the fields below. Update this table in lockstep with
`references/*.md` failure-mode tables.

### Strict-pass requirements per mode

| Mode | Must have | Evaluated by |
|---|---|---|
| translate (code→code) | `### Target: <framework>` header + single fenced code block + `### Diff vs source` with ≥3 bullets + `### Behavioral equivalence` section | section-presence regex + `tree-sitter-grader.py` AST cosine ≥ 0.80 vs target-lang reference |
| translate (code→code) | ≥2 verifiable framework API refs (e.g. `Portfolio.from_signals`, `strategy.entry`, `OrderFactory.market`) with file:line citation in the Diff section | `lsp-grader.py` symbols_with_callsite / symbol_count ≥ 0.60 |
| translate (code→code) | Zero forbidden constructs (see Vectorbt forbidden-constructs + per-target failure-mode tables in this file) | regex scan for forbidden patterns |
| extrapolate (code→human) | `### <Format>: <title>` header + prose in the right register + `### Faithfulness notes` with each claim grounded | presence regex + citation-link-count ≥ 1 per substantive claim |
| extrapolate (paper→code) | translate-style output + `### Paper → code mapping` section listing each load-bearing paper claim vs line-of-code | all translate requirements + `Paper → code mapping` section present with ≥3 rows |
| any | No hallucinated library APIs — every `vbt.*`, `nautilus_trader.*`, `pinescript.*` call must be verifiable in the current version | `lsp-grader.py` per-symbol callsite count, cross-checked against `docs-dual-lookup` result for any symbol `lsp-grader.py` reports as `unreferenced` |

### Penalty constants (for composite scoring)

```yaml
strict_pass_floor_overall: 0.80
strict_pass_floor_per_category:
  strategy-translator: 0.80
  swe-bench: 0.65
  gap-bridging: 0.70
penalty:
  hallucinated_api: -0.25           # any unreferenced symbol that's not a known-external-lib
  missing_diff_section: -0.15       # translate output with code block but no Diff vs source
  missing_equivalence_section: -0.10
  forbidden_construct: -0.30        # per occurrence (size=np.inf + percent, two Portfolio.from_signals, etc.)
  stale_library_call: -0.15         # call present in docs but for an older major version
known_external_libs:
  # symbols from these roots are "referenced via import but legitimately live outside the target repo"
  - vectorbtpro
  - vectorbt
  - nautilus_trader
  - pandas
  - numpy
  - polars
  - optuna
  - ray
  - reqwest
  - tokio
  - serde
  - clap
  - anyhow
  - tracing
```

### Harness invocation

The grader reads this section verbatim (YAML block above) and applies:

```
# pseudo
overall_score = sum(category_pass_rate * weight) / sum(weights)
per_response_score = 1.0
  - sum(penalty[forbidden_construct] for occurrence in response)
  - penalty[hallucinated_api] * (1 - lsp_score)
  - ...
strict_pass = per_response_score >= strict_pass_floor_per_category[category]
```

See `$RUN_ROOT/harness/README.md` for the concrete grader CLI and
`$RUN_ROOT/harness/tree-sitter-grader.py` / `lsp-grader.py` for implementation.

### Session logging contract

Every invocation of this skill that completes a translate or extrapolate MUST
emit a session-log record to `$RUN_ROOT/evidence/g7-recursive-harness/<round>/runs/<prompt_id>.jsonl`
(if run via the harness) or `~/.claude/projects/<project>/sessionlog.jsonl`
(if run interactively). Record schema:

```json
{
  "ts": "<ISO8601Z>",
  "skill": "strategy-translator",
  "mode": "translate|extrapolate",
  "source_format": "pine-v6|python|...",
  "target_format": "vectorbtpro|nautilus-py|...",
  "response_len_chars": 2134,
  "sections_emitted": ["Target: vectorbtpro", "Diff vs source", "Behavioral equivalence"],
  "api_refs_cited": ["vbt.Portfolio.from_signals", "vbt.bbands_1d_nb"],
  "citations_count": 3,
  "citation_sources": ["context7:/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt", "nlr_wiki:vectorbtpro/pitfalls"],
  "forbidden_constructs_detected": [],
  "tree_sitter_cosine": 0.88,
  "lsp_score": 0.75,
  "lsp_unreferenced": ["SomeNewClass::method"],
  "strict_pass": true
}
```

`$RUN_ROOT/harness/sessionlog.py` provides the `emit_record()` helper. When a
grader subprocess wraps a completion, use `python sessionlog.py score-and-emit
--completion <path> --prompt-id <id> --target-repo <path>` to run both graders
and write the record atomically.
