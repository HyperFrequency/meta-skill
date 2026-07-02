# Review protocol — evidence, questions, verdicts

Once the gate envelope is validated (`gate-envelope.md`), work each finding.
This file covers the two acts the human sees: **the evidence you present** and
**the questions you ask** — plus the confidence gate that decides whether a
finding is asked about at all.

## The confidence gate (decide before you ask)

For each `AntiPatternFinding`, compare `confidence` to the envelope's
`review_threshold`:

| Condition | Action |
| --- | --- |
| `confidence >= review_threshold` | **Do not ask.** Record an auto-confirm evidence event (`source: auto-confirm`); the miner is already sure. |
| `confidence < review_threshold` | **Ask.** Assemble evidence, pose 3–7 questions, record a human verdict. |
| evidence unresolvable | **Auto-REJECT** as `insufficient-evidence`; never ask a question you cannot back with a trace. |

This gate is the whole reason the skill exists: it consults the human **only for
the uncertain middle**. Asking about above-threshold findings is the top
over-ask failure mode — it floods the reviewer and poisons the annotation store
with rubber-stamp CONFIRMs that teach nothing.

## Assembling the evidence bundle

A verdict is only worth recording if the human saw what they were voting on.
Before any question, build the finding's bundle from its `evidence[]`:

1. **Trace links.** Resolvable pointers back into the corpus:
   `session_id` + `turn_range` for each incident, so the reviewer can open the
   source. Include the cluster's `count` and `sessions_affected` so scope is
   visible.
2. **Transcript excerpts.** For the representative incident, cut a **minimal**
   excerpt: the session `goal` (the first user turn — the ground truth drift is
   measured against) plus only the diverging turns. Not the whole session.
   Truncate each excerpt (~1500 chars) — you need the *shape* of the failure.
3. **Before/after diffs.** When the finding carries a `proposed_fix` /
   `proposed_diff`, show it as a side-by-side diff so the reviewer can judge the
   fix's plausibility *as part of* judging the finding. (They vote on the
   finding, not the fix — but a nonsensical fix is a signal the cluster is
   mislabeled.)

### Redaction (before any excerpt is shown or stored)

Excerpts come from raw tool output and can carry secrets/PII. This mirrors
`trajectory-miner`'s redaction rule — the review inherits the same sensitivity.

- Truncate long payloads to the shape of the failure.
- Scrub credential-shaped strings: `(?i)(api[_-]?key|token|secret|password|
  authorization|bearer|aws_[a-z_]*|-----BEGIN [A-Z ]*PRIVATE KEY)` and long
  high-entropy tokens → `«redacted»`.
- Never surface `.env`, `~/.aws`, `~/.ssh`, or `settings.json` contents a scanned
  Bash call may have printed. When in doubt, drop the line.

An evidence bundle is stored alongside its evidence event — so redaction must
happen before recording, not just before display.

## The four verdict types

Every below-threshold finding is adjudicated with one primary verdict. The four
map to the four things a human can correct about a mined cluster:

| Verdict | Question it answers | Effect on the finding |
| --- | --- | --- |
| **CONFIRM** | "Is this a real anti-pattern?" → yes | raises confidence; finding stands |
| **REJECT** | "Is this a real anti-pattern?" → no (noise/false cluster) | lowers confidence; finding dropped or returned to miner |
| **LABEL** | "Is the mode/name right?" → corrected | keeps the finding, rewrites `mode`/`name`; feeds Align-Evals as a relabel example |
| **BOUNDARY** | "Is the scope right?" → corrected | narrows/widens `sessions_affected` or splits/merges the cluster |

CONFIRM/REJECT is the real/not-real axis; LABEL is the what-is-it axis; BOUNDARY
is the how-wide axis. A finding can take a primary verdict plus a refinement
(e.g. CONFIRM + BOUNDARY: "yes it's real, but it only affects the 3 codex
sessions, not all 5").

## Asking: 3–7 targeted questions

Pose the questions for one finding (or a tight group of near-identical findings)
in a **single** `AskUserQuestion` round. Aim for **3–7** questions total across
the round — enough to pin real/label/boundary, not a survey.

`AskUserQuestion` renders each question as a card with clickable options; the
human may also type a free-form answer. Shape:

```
AskUserQuestion(
  questions = [
    {
      "header":   "Real?",                                  # short card title
      "question": "Cluster 'loop-bash-git-status': 12 incidents across 5 sessions repeat `git status` with no state change. Real anti-pattern?",
      "multiSelect": false,
      "options": [
        { "label": "Confirm (default)", "description": "Genuine loop. Miner confidence 0.62 → raise. Evidence: sess a1f/turns 42–60." },
        { "label": "Reject",            "description": "False cluster — the repeats were intentional polling. Drop it." }
      ]
    },
    {
      "header":   "Label",
      "question": "Is 'loop' the right mode, or is this really context_rot that manifests as a loop?",
      "multiSelect": false,
      "options": [
        { "label": "loop (default)", "description": "Keep the miner's label." },
        { "label": "context_rot",    "description": "Relabel — the agent lost the goal, looping is a symptom." }
      ]
    },
    {
      "header":   "Scope",
      "question": "Miner tagged 5 sessions. Does the pattern hold in all 5?",
      "multiSelect": true,
      "options": [
        { "label": "All 5 (default)", "description": "Boundary confirmed as mined." },
        { "label": "Claude only",     "description": "Narrow to the 3 Claude sessions; the 2 codex ones differ." }
      ]
    }
  ]
)
```

### Conventions

- **Batch:** all questions for the finding in one `questions` array; 3–7 per
  round. More than 7 means you are surveying — cut to the verdict-bearing ones.
- **Options:** 2–4 per question, each with a `label` and a `description` that
  states what choosing it *does to the finding* (raises/lowers confidence,
  relabels, rescopes).
- **Evidence-backed default:** every question ships one `(default)` — the verdict
  the *evidence* supports if the human never answers. For a clean, well-supported
  cluster the default is CONFIRM; for a thin one it is REJECT. The default is what
  the timeout path takes.
- **Free-form escape:** the human can always type a custom label/boundary, so you
  need no "other" option — but cover the realistic space in your 2–4.
- **Fallback:** if `AskUserQuestion` is unavailable, emit one numbered prose
  block with the same content — all questions, options, marked defaults — and
  parse the reply. Never trickle questions across messages.

## Writing a good review question

- **One axis per question.** Do not bundle "is it real AND what's the label" into
  one card. Real / label / boundary are separate questions.
- **Show the evidence in the question.** Cite `session/turn` and the count inside
  the `question` text — assume the human has not read the transcript.
- **Surface the confidence move.** The description says where confidence goes
  ("0.62 → raise"), so the human sees they are grading the miner, not just the
  agent.
- **Neutral framing.** The `(default)` mark is the only steer; do not editorialize
  toward it.
- **Genuinely distinct options.** Not three phrasings of CONFIRM (leading the
  witness).

## Worked examples

### Good — below threshold, evidence-backed, three axes

The batched call above: one finding, three cards (Real? / Label / Scope), each
defaulted from the evidence, each stating its effect on the finding. The human
can accept all defaults in three clicks; each click is a recorded annotation.

### Bad — asking above threshold

> Cluster `error-cascade-npm-install` (confidence 0.91): "Is this real?"

Above `review_threshold` — auto-confirm it, do not ask. Over-asking here trains
the human that the gate wastes their time.

### Bad — verdict with no evidence shown

> "Confirm cluster `refusal-batch-3`? [Yes / No]"

No trace, no excerpt, no count. A CONFIRM here is a worthless annotation. Resolve
the evidence first; if it will not resolve, auto-REJECT as
`insufficient-evidence`.

### Bad — bundled axes

> "Is this a real loop and should we widen it to all sessions? [Yes / No]"

Two axes (real + boundary) on one card. Split into a CONFIRM question and a
BOUNDARY question so each produces a clean, separately-replayable annotation.
