# Evidence events — durable record, confidence, Align-Evals, `_llm_scores`

A verdict that only rides back on the response envelope is lost the moment the
gate closes. Every verdict must also be **recorded three ways** so the review is
durable, confidence-adjusting, and regression-gateable:

1. an **evidence event** that raises or lowers the finding's confidence,
2. an **Align-Evals few-shot record** so the corpus of human judgments trains the
   next miner/reviewer pass,
3. an **`_llm_scores` annotation row** (`source_type: "annotation"`) so the review
   itself can be replayed and graded like any other scored artifact.

All three are append-only. Never overwrite a prior verdict; supersede it with a
new dated event so the history stays auditable.

## 1. The evidence event

One append-only event per verdict. It is the atom of the review record.

```json
{
  "event_id":     "ev-2026-07-02-0007",
  "finding_id":   "loop-bash-git-status",
  "workflow_run": "tm-scan-2026-07-02T02:14Z",
  "verdict":      "CONFIRM",              // CONFIRM|REJECT|LABEL|BOUNDARY|UNRESOLVED
  "label":        null,                    // set when verdict==LABEL
  "boundary":     null,                    // set when verdict==BOUNDARY
  "source":       "human",                 // human | default-on-timeout | auto-confirm
  "reviewer":     "danrepaci157@gmail.com",
  "evidence_ref": ["sess:a1f#42-60"],      // resolved trace links shown to the human
  "confidence_before": 0.62,
  "confidence_after":  0.80,
  "created_at":   "2026-07-02T14:05Z",
  "notes":        "loop confirmed; polling ruled out — no state change between calls"
}
```

### The confidence-update rule

A verdict is an **evidence event on the finding's confidence**, not a hard
overwrite. Update, do not replace:

- **CONFIRM** raises confidence toward 1 (a human-confirmed real cluster).
- **REJECT** lowers it toward 0 (a human-refuted false cluster).
- **LABEL** does not move the real/not-real confidence much; it rewrites
  `mode`/`name` and records a *relabel* signal.
- **BOUNDARY** rescopes (`sessions_affected`, or split/merge) without asserting
  real/not-real.
- `source: auto-confirm` (above-threshold, no human asked) records a small
  positive nudge, tagged so replay can distinguish it from a human CONFIRM.
- `source: default-on-timeout` records the evidence-backed default with a weaker
  weight than an explicit human verdict — a default is a guess, not a judgment.

Use a bounded update (e.g. a log-odds / Bayesian nudge weighted by `source`), not
a set-to-1/set-to-0, so that a later contradicting verdict can move it back and
the history reflects accumulated evidence. A finding whose confidence crosses
`review_threshold` after an event no longer needs asking on the next pass.

### Conflict / re-review

If a new verdict contradicts a recorded one (human changed their mind, or a
second reviewer disagrees):

- Append the new event; **most-recent-wins** for the working confidence.
- Mark the superseded event `superseded_by: <event_id>` — never delete it.
- If the disagreement is between two reviewers on the same finding, that split is
  itself signal: flag it for a `recursive-self-improvement` consortium look
  rather than silently taking the latest.

## 2. Align-Evals few-shot store

Every verdict is a labeled example of *what a correct anti-pattern judgment looks
like on this evidence*. Accumulated, these become the few-shot store that
calibrates the next miner run and the next reviewer — the review teaches the
loop.

Record per verdict:

```json
{
  "finding_id":  "loop-bash-git-status",
  "input": {
    "mode": "loop", "name": "Repeated `git status`…",
    "evidence_excerpt": "«scrubbed goal + diverging turns»",
    "miner_confidence": 0.62
  },
  "gold": {
    "verdict": "CONFIRM", "corrected_label": null, "corrected_boundary": null
  },
  "source": "human",
  "created_at": "2026-07-02T14:05Z"
}
```

- **CONFIRM/REJECT** examples calibrate the real/not-real detector.
- **LABEL** examples are the highest-value ones — they are corrected labels the
  miner got wrong, exactly the supervised signal a reflective pass needs.
- **BOUNDARY** examples calibrate blast-radius / scope estimation.
- Store `source: auto-confirm` and `default-on-timeout` examples but weight them
  below `human` — they are weak labels. Only `human` verdicts are gold.

The few-shot store lives beside the corpus (same sensitivity as the transcripts).
Redaction from `review-protocol.md` applies before writing any excerpt here.

## 3. `_llm_scores` annotation logging — regression-gate the review

Every decision is logged to `_llm_scores` with `source_type: "annotation"`. This
is what makes **the interview itself regression-gateable**: the review is not a
trusted oracle, it is a scored artifact you can replay.

```sql
-- one row per verdict
INSERT INTO _llm_scores
  (run_id, item_id, source_type, score, label, metadata, created_at)
VALUES
  ('tm-scan-2026-07-02T02:14Z',      -- workflow_run
   'loop-bash-git-status',           -- finding_id
   'annotation',                     -- distinguishes human review from model/judge scores
   0.80,                             -- confidence_after (or 1/0 for a hard verdict)
   'CONFIRM',                        -- the verdict
   '{"reviewer":"…","source":"human","evidence_ref":["sess:a1f#42-60"]}',
   '2026-07-02T14:05Z');
```

`source_type: "annotation"` sits alongside the other `_llm_scores` sources
(model self-scores, judge-panel scores, backtest verification badges). Because
annotations share the table:

- **Replay for drift.** Re-present a held-out set of past findings to the current
  reviewer; if new annotations diverge from the stored gold annotations beyond a
  tolerance, the reviewer (human or the harness standing in) is **drifting** —
  surface it and pause annotating, per SKILL.md. A gate that silently drifts
  corrupts every downstream fix.
- **Inter-annotator agreement.** Two reviewers' annotation rows on the same
  finding give an agreement score; low agreement flags an ambiguous finding for
  consortium review, not a coin flip.
- **Gate the loop.** `recursive-self-improvement` reads these rows to check its
  own graders against human ground truth — the annotations are the reference the
  consortium is measured against.

Never store credential *values* in `_llm_scores.metadata` — only resolved trace
refs and the verdict. This mirrors the global credential-safety rule.

## Timeout / no-response recording

When the gate hits `expires_at` (`gate-envelope.md`) with findings still open:

1. **Findings with a safe evidence-backed default** ⇒ record the default verdict
   as an evidence event with `source: default-on-timeout`, Align-Evals as a weak
   label, and an `_llm_scores` row tagged `default-on-timeout`. Confidence moves
   with reduced weight.
2. **Below-threshold findings with no safe default** (e.g. a finding whose only
   confirm-path would drive a deletion) ⇒ record `verdict: UNRESOLVED`, leave the
   finding's confidence unchanged, and keep the gate open for the next human
   touch. Do **not** auto-confirm.

A stopped, resumable gate is recoverable; a timeout that auto-confirmed a false
anti-pattern and drove a deletion is not.

## The resume summary

After recording, hand the scan workflow a compact block it resumes on (goes in
the `ApprovalResponse.resume`), not a re-read of every finding:

```markdown
### Antipattern review complete (run: tm-scan-2026-07-02T02:14Z)
Confirmed (real anti-patterns):
- loop-bash-git-status — CONFIRM, conf 0.62→0.80, tier: manual
- error-cascade-npm     — auto-confirm (0.91), tier: auto-apply (within hyper-sleep bounds)
Relabeled:
- refusal-batch-3 → context_rot (LABEL) — feeds Align-Evals as a relabel
Rejected (dropped / returned to miner):
- drift-cluster-7 — REJECT, insufficient-evidence
Unresolved (gate stays open):
- delete-stale-skill-x — UNRESOLVED, no safe default (would drive a deletion)
→ Hand confirmed manual-tier findings to recursive-self-improvement / neuro-surgery.
```

Then **return control**. You adjudicated and recorded; the scan workflow (and its
downstream fix loop) owns what happens next.
