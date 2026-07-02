# Worked examples

Three end-to-end walkthroughs: a PASS/FAIL gate, a K-way anonymized tournament, and a debate that
flips a majority. Each shows the `PanelRequest` and the resulting `Verdict`. Judge prompts follow
the scaffolds in [topologies.md](topologies.md); schemas are in [contract.md](contract.md).

---

## Example 1 — PASS/FAIL gate (independent + majority)

**Goal:** does this answer clear the bar before it ships? Odd panel (3), majority vote.

Request:

```jsonc
{
  "candidate": { "id": "ans-42", "content": "Water boils at 100°C at sea level; at altitude the boiling point drops." },
  "task_context": "At what temperature does water boil, and does altitude matter?",
  "rubric": {
    "criteria": [
      { "name": "accuracy",     "description": "Physically correct.",           "weight": 0.6 },
      { "name": "completeness", "description": "Addresses the altitude part.",   "weight": 0.4 }
    ],
    "scale": { "min": 1, "max": 5 }, "evidence_required": true, "pass_threshold": 3.5
  },
  "judges": [
    { "id": "j-opus",   "model": "claude-opus-4-8", "temperature": 0 },
    { "id": "j-gpt",    "model": "gpt-5.2",         "temperature": 0 },
    { "id": "j-gemini", "model": "gemini-3.1-pro",  "temperature": 0 }
  ],
  "topology": "independent", "aggregation": "median"
}
```

Votes: opus 4.8 / gpt 4.5 / gemini 4.6 — all PASS, all citing the two correct facts as evidence.

Verdict:

```jsonc
{
  "mode": "gate", "decision": "PASS", "score": 4.6, "confidence": 0.94,
  "agreement": 0.97, "dissent": [], "abstentions": [],
  "metadata": { "topology": "independent", "aggregation": "median", "n_judges": 3 }
}
```

High agreement → high (but < 0.99) confidence. Median score 4.6 ≥ threshold 3.5 → PASS.

---

## Example 2 — 4-way fusion tournament (independent ranking + Borda)

**Goal:** four candidate answers (e.g. four fusion-panel outputs) to the same prompt; pick the best
without provenance or position bias. Because `candidates[]` is present, each judge independently
ranks them via the **anonymized cross-ranking mechanism** (topologies.md) — `topology: independent`
means no judge sees another's ranking.

Request (abbrev):

```jsonc
{
  "candidates": [ {"id":"A","content":"..."}, {"id":"B","content":"..."},
                  {"id":"C","content":"..."}, {"id":"D","content":"..."} ],
  "task_context": "Summarize the risks of over-fitting a trading strategy.",
  "rubric": { "criteria": [ {"name":"correctness","weight":0.5},
                            {"name":"coverage","weight":0.3},
                            {"name":"concision","weight":0.2} ],
              "scale": {"min":1,"max":5}, "evidence_required": true },
  "judges": [ {"id":"j1","model":"claude-opus-4-8"}, {"id":"j2","model":"gpt-5.2"},
              {"id":"j3","model":"gemini-3.1-pro"}, {"id":"j4","model":"grok-4"},
              {"id":"j5","model":"llama-4-405b"} ],
  "topology": "independent", "aggregation": "borda"
}
```

Each judge sees A–D **relabeled and shuffled uniquely** (`hash(seed, judge_id)`), ranks the neutral
labels, and the panel maps rankings back. Rank aggregation = Borda:

```
Borda points (3=1st … 0=4th), summed over 5 judges:
  C = 14   A = 11   B = 6   D = 4
```

Verdict:

```jsonc
{
  "mode": "tournament", "decision": "C", "score": null, "confidence": 0.81,
  "agreement": 0.68,                          // Krippendorff alpha over the 5 rankings
  "ranked": ["C","A","B","D"],
  "dissent": [ { "judge_id": "j4", "decision": "A", "reason": "ranked A over C on concision" } ],
  "metadata": { "topology": "independent", "aggregation": "borda", "n_judges": 5, "mechanism": "anonymized_cross_ranking" }
}
```

C wins decisively; one judge preferred A (recorded as dissent). Anonymization means "C" won on
content, not because it was listed first or came from a favored model.

---

## Example 3 — debate flips a majority

**Goal:** high-stakes correctness where one judge spots a flaw the others missed.

Round 1 (independent), candidate is a diff claimed to fix a bug:

```
j-opus:   PASS (4.5) — "tests pass, logic reads correct"
j-gpt:    PASS (4.2) — "addresses the reported symptom"
j-gemini: FAIL (2.0) — evidence: "the fix mutates `cache` inside the loop; introduces a
                        race under concurrency — cites lines 40-47"
```

Round-1 majority = **PASS** (2 vs 1). With `topology: independent` this ships a race condition.

Round 2 (`topology: debate`): opus and gpt see gemini's *anonymized rationale* (scores hidden).
opus re-reads lines 40–47, confirms the race, and **revises to FAIL, citing the new evidence**.
gpt holds PASS but notes the concern.

Verdict (aggregated on Round-2 votes):

```jsonc
{
  "mode": "gate", "decision": "FAIL", "score": 2.6, "confidence": 0.74,
  "agreement": 0.55,
  "dissent": [ { "judge_id": "j-gpt", "decision": "PASS", "reason": "believes race is unreachable" } ],
  "metadata": { "topology": "debate", "aggregation": "median", "rounds": 2,
                "moved": [ { "judge_id": "j-opus", "from": "PASS", "to": "FAIL",
                             "reason": "confirmed the mutation race on new evidence" } ] }
}
```

Debate let correct minority *evidence* (not social pressure — opus cited the lines, per the
Round-2 guardrail) move the panel. Confidence is moderate, reflecting the remaining dissent — a
signal to escalate to a human before merging.

---

## Example 4 — council synthesis (3-stage, anonymized)

**Goal:** three models answer an open question; produce one *synthesized* best answer plus a peer
ranking, with anonymization killing sycophancy toward the strongest-branded model.

```jsonc
{
  "candidates": null,                          // council generates stage-1 answers itself from task_context
  "task_context": "Explain why deflated Sharpe ratio matters when selecting among many backtests.",
  "rubric": { "criteria": [ {"name":"correctness","weight":0.6}, {"name":"clarity","weight":0.4} ],
              "scale": {"min":1,"max":5}, "evidence_required": true },
  "judges": [ {"id":"m1","model":"claude-opus-4-8"}, {"id":"m2","model":"gpt-5.2"},
              {"id":"m3","model":"gemini-3.1-pro"} ],
  "topology": "council", "aggregation": "borda",
  "council": { "chairman": "gemini-3.1-pro" }
}
```

Flow: **Stage 1** — m1/m2/m3 each answer privately. **Stage 2** — each sees all three answers as
`Response A/B/C` (identities stripped, order shuffled per member) and returns a ranking; nobody
knows which answer is theirs, so no self-favoring and no deferring to a big-name model. **Stage 3**
— the chairman reads the answers + rankings and writes the final synthesis.

```jsonc
{
  "mode": "tournament", "decision": "m2", "score": null, "confidence": "HIGH",
  "agreement": 0.79, "ranked": ["m2","m1","m3"],
  "dissent": [],
  "metadata": { "topology": "council", "aggregation": "borda", "n_judges": 3,
                "synthesis": "Deflated Sharpe corrects the selection bias from testing many strategies: the more backtests you try, the higher the best in-sample Sharpe you expect by luck alone; DSR discounts the observed Sharpe by the number of trials and their correlation ..." }
}
```

The ranking says m2's answer was judged best; the deliverable callers actually use is
`metadata.synthesis`. Contrast `consciousness-council`, which would surface the *tension* between
views for a human rather than emit a single synthesized answer + rank.

---

## Example 5 — hierarchical escalation (cheap-first, episteme)

**Goal:** screen 10,000 generated replies cheaply; only spend the full panel on the ambiguous ones.

```jsonc
{
  "candidate": { "id": "reply-7731", "content": "..." },
  "task_context": "Is this reply a correct, safe answer to the user's billing question?",
  "rubric": { "criteria": [ {"name":"correct_safe","weight":1.0} ],
              "scale": {"min":0,"max":1}, "evidence_required": true },
  "judges": [ {"id":"cheap","model":"gemini-3.1-flash","weight":1.0},
              {"id":"j2","model":"claude-opus-4-8"}, {"id":"j3","model":"gpt-5.2"} ],
  "topology": "hierarchical", "aggregation": "median",
  "hierarchical": { "uncertain_range": [0.4, 0.7] }
}
```

Two outcomes on this stream:

- **reply-7731** → cheap judge scores **0.12** (clearly wrong: cites the wrong plan tier). `0.12 <
  0.4` → outside the uncertain band → return `FAIL`, `confidence: HIGH`, `escalated: false`, **1
  call**.
- **reply-8002** → cheap judge scores **0.55** (borderline). `0.4 ≤ 0.55 ≤ 0.7` → **escalate**: run
  opus + gpt, aggregate all three by median. Opus 0.8 / gpt 0.75 / cheap 0.55 → median **0.75** →
  `PASS`, `escalated: true`, **3 calls**.

```jsonc
{
  "mode": "gate", "decision": "PASS", "score": 0.75, "confidence": "MEDIUM",
  "score_sigma": 0.11, "agreement": 0.83,
  "metadata": { "topology": "hierarchical", "aggregation": "median", "escalated": true, "n_judges": 3 }
}
```

Across 10k items where ~85% land outside the band, the panel cost is ≈ `0.85·1 + 0.15·3 = 1.3`
calls/item instead of 3 — a >2x saving with the full panel reserved for the hard tail. Guard: the
cheap judge's ledger bias offset is subtracted before the range check so a lenient cheap judge
cannot wave borderline-bad replies through.

---

## Feeding the ledger (all examples)

After each verdict, append one row per judge with its `predicted_score`/`predicted_decision`. When
the realized outcome later arrives — a human confirms the winner, the strategy's out-of-sample PnL
lands, CI catches (or misses) the race — reconcile the rows. Over many calls the ledger learns that
`j-gemini` catches concurrency bugs (raise its weight on code candidates) and, say, that `j-gpt`
runs lenient (subtract its bias offset). See [self-calibration.md](self-calibration.md).
