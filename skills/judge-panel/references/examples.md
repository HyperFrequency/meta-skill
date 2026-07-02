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

## Example 2 — 4-way fusion tournament (cross_ranking + Borda)

**Goal:** four candidate answers (e.g. four fusion-panel outputs) to the same prompt; pick the best
without provenance or position bias.

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
  "topology": "cross_ranking", "aggregation": "trimmed"
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
  "metadata": { "topology": "cross_ranking", "aggregation": "trimmed(k=1)", "n_judges": 5 }
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

## Feeding the ledger (all three examples)

After each verdict, append one row per judge with its `predicted_score`/`predicted_decision`. When
the realized outcome later arrives — a human confirms the winner, the strategy's out-of-sample PnL
lands, CI catches (or misses) the race — reconcile the rows. Over many calls the ledger learns that
`j-gemini` catches concurrency bugs (raise its weight on code candidates) and, say, that `j-gpt`
runs lenient (subtract its bias offset). See [self-calibration.md](self-calibration.md).
