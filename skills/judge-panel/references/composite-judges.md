# DAG composite judges (DeepEval-style)

A single rubric score is often too flat. "Is this answer good?" really means: *if* it is
off-topic, score 0 regardless of prose quality; *else if* it contradicts the source, cap at 2;
*else* score on clarity + completeness. That branching logic is a **directed acyclic graph** of
sub-judgments — a **DAG composite judge** (the pattern DeepEval calls a `DAGMetric` /
deep-acyclic-graph metric).

A DAG judge is still just a judge: it takes `(candidate, rubric)` and returns one `JudgeVote`. The
panel does not care how the vote was produced — it aggregates the resulting scalar/decision
normally. The DAG lives *inside* one judge (referenced by `judges[i].composite`), giving that judge
a structured, auditable path from candidate to score.

## Node types

| Node | Role | Output |
|---|---|---|
| **TaskNode** | Extract/derive a fact from the candidate ("what is the claimed answer?"). | A value passed to children. |
| **BinaryJudgementNode** | A yes/no gate ("does it cite a source?"). | Branch selection. |
| **NonBinaryJudgementNode** | A multi-way classification ("tone: formal / casual / hostile"). | Branch selection. |
| **VerdictNode** (leaf) | Terminal score/decision for the path that reached it. | The judge's `score`/`decision`. |

Edges carry the branch condition. Every root-to-leaf path ends in exactly one `VerdictNode`, so the
graph is total (no candidate falls through without a verdict) and acyclic (no loops).

## Worked DAG — grading a support reply

```
                 [TaskNode: extract the answer's core claim]
                              │
              [BinaryJudgementNode: on-topic for the ticket?]
                 no │                                 │ yes
        [VerdictNode: score 0                [BinaryJudgementNode: factually
         "off-topic"]                         consistent with the KB article?]
                                        no │                          │ yes
                          [VerdictNode: cap 2            [NonBinaryJudgementNode:
                           "contradicts KB"]              completeness = full/partial/thin]
                                                  full │      partial │      thin │
                                            [Verdict 5]   [Verdict 3.5]   [Verdict 2]
```

Each node is a small, cheap LLM call (or a deterministic check) with its **own** evidence-before-
answer prompt — invariant #1 holds at every node, not just the leaf. The traversed path is recorded
in `JudgeVote.raw` so the verdict is fully explainable ("scored 3.5: on-topic ✓, KB-consistent ✓,
completeness = partial").

## Composite spec (referenced from a judge)

```jsonc
{
  "composite_id": "support-reply-v2",
  "nodes": [
    { "id": "claim",   "type": "task",    "prompt": "State the reply's core claim in one sentence." },
    { "id": "topic",   "type": "binary",  "prompt": "Is that claim on-topic for the ticket? Cite evidence.",
      "edges": { "no": "v_offtopic", "yes": "kb" } },
    { "id": "v_offtopic", "type": "verdict", "score": 0, "label": "off-topic" },
    { "id": "kb",      "type": "binary",  "prompt": "Is it consistent with the KB article? Cite the passage.",
      "edges": { "no": "v_contradict", "yes": "complete" } },
    { "id": "v_contradict", "type": "verdict", "score_cap": 2, "label": "contradicts-KB" },
    { "id": "complete", "type": "nonbinary", "prompt": "Completeness: full | partial | thin? Cite gaps.",
      "edges": { "full": "v_full", "partial": "v_partial", "thin": "v_thin" } },
    { "id": "v_full",    "type": "verdict", "score": 5 },
    { "id": "v_partial", "type": "verdict", "score": 3.5 },
    { "id": "v_thin",    "type": "verdict", "score": 2 }
  ],
  "root": "claim"
}
```

## When to use a DAG vs a flat rubric

- **Use a DAG** when scoring has **hard gates** ("wrong answer ⇒ zero, nothing else matters") or
  **conditional criteria** (a criterion only applies on some branches). The DAG makes those rules
  explicit and consistent instead of hoping a flat-rubric judge remembers them.
- **Stay flat** when all criteria always apply and combine linearly — a DAG then just adds cost and
  latency (one call per node) for no gain.
- **Cost:** a DAG judge is `depth` sequential calls per candidate; keep graphs shallow, and prefer
  deterministic checks (regex, exact-match, a unit test) for nodes that don't need an LLM.

## Interaction with the panel

- A DAG judge is one member of the panel. Run several *different* DAG (or flat) judges and aggregate
  as usual — the DAG structures *one* judge's reasoning, it does not replace the multi-judge panel.
- The DAG's branch conditions are themselves prompts, so they are **evolvable variants** (SKILL.md)
  and calibratable against the ledger like any judge prompt.
- Boundary: designing the *node prompts and thresholds* is single-judge design → `ce-advanced-
  evaluation`. judge-panel only wires the nodes into a judge and aggregates the result.
