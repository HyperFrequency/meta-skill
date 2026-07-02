# Answer Record — durable context and resume

Answers must outlive the session that collected them. A run may pause tonight and resume next week in a fresh context window; a sibling agent may need the same decision. The interview ledger is the single source of truth for "what has the human already told us."

## The interview ledger

**Default path:** `state/interview-ledger.md` at the project/goal root. If the harness config (e.g. relentless-inception's run dir, or an `e2e-agentic-ML` checkpoint dir) defines its own answers/decisions store, write there instead — reconcile, do not fork a second ledger. **One ledger per project/goal.**

One append-only entry per resolved decision. Never overwrite a prior answer; supersede it with a new dated entry so the history is auditable.

```markdown
## <short decision title>
- id: <stable-slug>            # e.g. risk-cap, deploy-target
- category: requirement | preference | approval | disambiguation | acceptance | precondition
- question: "<exact question posed>"
- answer: "<the human's chosen option or free-form text>"
- source: human | default-on-timeout | inferred | superseded-by:<id>
- asked_at: 2026-07-02T14:03Z
- answered_at: 2026-07-02T14:05Z
- gate: <which run gate/phase asked it>
- notes: "<consequence, scope, or the assumption reasoning if inferred>"
```

### What to record

- **Every human answer** — verbatim choice or typed text.
- **Every inferred assumption** from the blocking filter — decisions you made *instead* of asking, with `source: inferred` and the reasoning. This is what lets the human audit "why did it build it this way" and lets a future run avoid re-deriving it.
- **Every timeout default taken** — `source: default-on-timeout`.

Recording inferences is as important as recording answers: an unrecorded inference becomes an invisible silent assumption — exactly the failure this skill exists to prevent.

## Threading answers back into a paused run

After recording, hand the calling agent a **resume summary** — a compact block it can prepend to its next step so it continues with real inputs, not a re-read of the whole transcript:

```markdown
### Resume with human input (gate: <name>)
Decisions now settled:
- <title>: <answer>  (source)
- <title>: <answer>  (source)
Assumptions recorded (not asked, safe defaults): 
- <title>: <inferred value> — <one-line why>
Still open / deferred to a later gate:
- <title> — will block at <later gate>
→ Continue from: <the concrete next step the run should take>
```

Keep it short. The full detail lives in the ledger; the resume summary is the working set. Then **return control** — you are the elicitation pass, not the executor. Do not start doing the underlying task.

## No-response / timeout handling

The human may never answer (walked away, async run, overnight). Behavior:

1. **Every open question had a safe default** ⇒ take all defaults, record each as `source: default-on-timeout`, emit the resume summary, and let the run continue. This is the whole point of defaulting: an unattended run still makes safe progress.
2. **Any open question was un-defaultable** (a high-stakes approval or a requirement with no safe fallback) ⇒ do **not** guess. Record the taken defaults for the rest, then **checkpoint the run and stop cleanly**: write the still-open question(s) to the ledger with `answer: <UNANSWERED>`, leave a clear "resume needs: <question>" marker, and exit. The next human touch picks up exactly there.

Never let a timeout silently commit an irreversible action. A stopped run is recoverable; a wrong deploy is not.

## Conflict resolution

If a new answer contradicts a recorded one (human changed their mind, or two runs disagree):
- **Most-recent-wins** for the working value; mark the old entry `source: superseded-by:<new-id>`.
- If the contradiction is material and the human's intent is unclear, surface it as its own next-round question ("earlier you chose X, now Y — which holds?") rather than picking silently.

## Provenance discipline

- Timestamp every entry; keep asked/answered times distinct so latency is visible.
- Attribute every value to `human` / `inferred` / `default-on-timeout` / `superseded-by` — an unattributed answer is untrustworthy on the next run.
- Never store credential *values* in the ledger — only the name of the var the human was asked to set (see `blocking-criteria.md` → credential preconditions).
