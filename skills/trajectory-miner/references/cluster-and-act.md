# CLUSTER, ACT & REVIEW (Loop-3 stages 4–5)

Incidents (from `scanners.md`) become **AntiPatterns** and **Issues** = named,
recurring failure modes across the corpus; the confirmed ones are published to a
**versioned anti-pattern registry** that downstream systems consume; and the
uncertain ones hand off to `hitl-interview` before promotion. This is where the
pipeline turns observation into a durable, queryable artifact.

---

## 1. CLUSTER — group by source-type + failed-action similarity

**Stage A — deterministic bucket (always, first).**
Key = `(source_type, mode, normalized_signature)`. This resolves the crisp modes
(doom loops, stuck, recursion, cost) because their signatures already normalized
away volatile tokens. Grouping by `source_type` too keeps
"Claude-Code doom loop" separate from "OTel-traced service doom loop" — they
route to different fixes. Normalize signatures before bucketing: lowercase;
collapse whitespace; strip digits, hex, absolute paths, tmp names, line/col;
keep the stable phrase ("context length exceeded", "file not found").

**Stage B — embedding merge (fuzzy modes only).**
`context_degradation`, `correction`, and any refusal/hallucination-flavored
incidents vary in surface text; Stage-A fragments them. Embed each incident's
scrubbed `evidence`, cluster within `(source_type, mode)` by cosine — HDBSCAN
(`min_cluster_size = min_support`) or union-find at `≥ 0.75`. Fall back to
TF-IDF cosine if no embedder is available; never block on an API. "Failed-action
similarity" = distance on the *action that failed*, so two loops on different but
equivalent commands merge, while a loop and a monologue never do.

Drop clusters with `count < min_support` (default 2) into a one-offs appendix —
never a headline. A single occurrence is noise; a pattern repeats.

---

## 2. Two output objects per cluster

Each surviving cluster yields an **AntiPattern** (the rule to avoid) and,
when it points at a fixable root cause, an **Issue** (the thing to fix).

**AntiPattern** — a prescriptive, negative rule:

```json
{
  "id": "ap-doom-loop-validation-pytest",
  "version": "1",
  "rule": "NEVER re-run an unchanged failing test when the last two runs were identical",
  "instead": "Edit the test or the code under test before re-running Validation",
  "mode": "doom_loop", "source_types": ["claude","traj"],
  "severity": "high",
  "occurrences": 12,
  "confidence": 0.857,          // n/(n+2) with n=occurrences → 12/14
  "exemplars": [ {"session_id":"…","turn_range":[42,60]} ],
  "provenance": [ {"scanner_id":"doom_loop","criteria_version":"doom_loop.v2"} ],
  "status": "confirmed"          // candidate|confirmed (see §4 REVIEW)
}
```

- `rule` is always **"NEVER X when Y"** — the shape skill-heals and judges consume.
- `confidence = n / (n + 2)`: additive smoothing so small n stays humble
  (n=2 → 0.50, n=8 → 0.80, n=18 → 0.90). It expresses "how sure this is a real
  pattern, not a coincidence", NOT severity — keep the two orthogonal.

**Issue** — a fixable root cause with a live query:

```json
{
  "id": "issue-git-status-spin",
  "cause": "Planner has no stop-condition on repeated read-only Bash calls",
  "suggestedFix": "After 2 identical Bash signatures, force a plan/replan step",
  "tracesQuery": "mode=doom_loop AND signature~='doom_loop:Recon:Bash:git-status'",
  "severity": "high",
  "occurrences": 12,
  "firstSeen": "2026-06-14T…Z", "lastSeen": "2026-07-01T…Z"
}
```

- `tracesQuery` is the load-bearing field: a re-runnable selector (against the
  trace/OTel store or the incident index) that **re-fetches every matching trace
  live**. The Issue is therefore not a stale snapshot — a consumer can ask "is
  this still happening this week?" `firstSeen`/`lastSeen` come from incident
  timestamps and tell you whether a fix already landed (lastSeen stops advancing).

**Ranking** for the human view: `priority = occurrences × severity_weight
(low=1,med=2,high=4) × blast_radius (distinct sessions)`. A mode hitting 20
sessions outranks one hitting 40× in a single session.

---

## 3. ACT — publish to the versioned anti-pattern registry

Confirmed AntiPatterns + Issues are written to a **versioned registry** — the
single durable artifact this pipeline exists to produce. It is append/supersede,
never destructive:

- The registry file/store carries a `schema_version`; each entry carries its own
  `version`. Re-mining that strengthens an existing pattern **bumps its version
  and updates occurrences/confidence/lastSeen**; it does not fork a duplicate.
- Every entry keeps `provenance` (scanner_id + criteria_version + exemplars) so
  it is **re-derivable** and invalidatable when a scanner's criteria change.
- Superseding (a fix landed, occurrences went to zero) marks the entry `retired`
  with a reason; history is preserved, not deleted.

**Four consumers** read this registry — the reason it is structured, not prose:

| Consumer                     | Reads                          | Uses it to |
|------------------------------|--------------------------------|-----------|
| **skill heals** (`meta-skill`, skill-creator heal loops) | `rule` / `instead` | bake "NEVER X when Y" guidance into a skill's instructions |
| **prompt mutations** (reflective/GEPA-style optimizers) | exemplars → `{inputs, bad output, feedback}` | mutate the failing component's prompt against real negative examples |
| **judge criteria** (`judge-panel`, eval rubrics) | `rule` + severity | add scored criteria that penalize the anti-pattern in future runs |
| **rescue triggers** (`background-rescue`) | high-severity, high-confidence live patterns | arm watchdog trigger conditions so a live node matching the pattern is caught early |

Reflective-mutation note: the `correction.vN` scanner's bad→good pairs are the
richest fuel here — an exemplar's `Feedback` should carry the concrete `mode`,
the `suggestedFix`, and the AntiPattern `id` so the proposal is grounded, not a
vague "this was wrong". Weight records by cluster `occurrences`/`priority` so a
one-off doesn't get optimized at the systemic mode's expense.

This skill **produces the failure signal and the registry entry. It never applies
a fix** — no prompt is mutated, no skill edited, no rescue fired by trajectory-
miner. The consumers, gated by their own review, decide.

---

## 4. REVIEW — hand uncertain patterns to `hitl-interview`

An AntiPattern is born `status: "candidate"`. It is promoted to `"confirmed"`
(and only then read by consumers as authoritative) via one of:

- **Auto-confirm:** high `confidence` (≥ 0.8, i.e. n ≥ 8) **and** a crisp
  deterministic mode (doom_loop / stuck / recursion) whose exemplars a human
  need not adjudicate.
- **HITL confirm:** everything else — fuzzy modes (context-degradation,
  hallucination-flavored), high blast-radius but low confidence, or a proposed
  `rule` that would meaningfully constrain future agents. Hand these to
  **`hitl-interview`**: it presents the exemplar excerpts, the drafted
  `rule`/`instead`, and asks the human to confirm, edit, or reject. Only the
  human-blessed rule is promoted.

Route the borderline set deliberately: the more a rule will *constrain* downstream
agents (a broad "NEVER refuse code refactors"), the lower the auto-confirm bar
should be and the more it belongs in front of a person. Over-eager auto-confirm
poisons every consumer at once.

---

## 5. Redaction & privacy

Exemplar excerpts are already scrubbed at ingest (secrets, injection quarantine,
PII pseudonyms — `ingest-and-scrub.md` §7). Still, at emit time: truncate each
excerpt (`≤ 1500` chars — you need the *shape* of the failure), and re-run the
secret regex as a belt-and-suspenders pass before writing it into the registry or
a reflective record. The registry and any reflective dataset are **as sensitive
as the transcripts they came from** — store them beside the corpus, not in a
shared location.

---

## 6. Cross-links

- **`hitl-interview`** — the REVIEW handoff; human confirmation of candidate
  anti-patterns before promotion.
- **`background-rescue`** — a live consumer (rescue triggers) AND the inverse
  operation: it re-grounds ONE stuck node in real time; this skill finds those
  nodes in BATCH, after the fact, across the corpus.
- **`recursive-self-improvement`** — the graded, HITL improvement loop that
  consumes the registry (skill heals + prompt mutations) and decides what lands.
- **`meta-skill` / `skill-creator`** — the skill-heal consumers of `rule`/`instead`.
- **`judge-panel`** — consumes anti-patterns as judge criteria.
