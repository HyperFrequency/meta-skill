# Question Protocol

How to ask, once you have filtered to blocking-only questions (see `blocking-criteria.md`).

## The `AskUserQuestion` tool

This is the Claude Code harness tool for structured, in-band human input. It renders each question as a card with clickable options; the human may also type a free-form ("Other") answer. Use it instead of printing questions as prose — prose questions are easy for the human to skim past and hard for the calling agent to parse back.

Shape of the call (batch multiple questions in ONE call):

```
AskUserQuestion(
  questions = [
    {
      "header":      "Deploy target",          # short label, keep to a few words
      "question":    "Where should the strategy deploy first?",
      "multiSelect": false,                      # true only when several answers can co-apply
      "options": [
        { "label": "Paper (default)", "description": "Testnet / paper account. Safe, reversible. Recommended first step." },
        { "label": "Live — small",    "description": "Real capital, hard size cap. Irreversible fills." },
        { "label": "Live — full",     "description": "Real capital, full size. Highest risk." }
      ]
    },
    { ...next question... }
  ]
)
```

### Limits and conventions (assume the harness enforces these)

- **Batch:** put every open question for this gate in the single `questions` array. Keep it to roughly **1–4 questions** per round — if you have more, you have not filtered hard enough.
- **Options:** **2–4** per question. Each needs a `label` (short) and a `description` (what choosing it means, and any consequence).
- **Header:** short — a couple of words. It is the card title, not the question.
- **Free-form escape:** the human can always type a custom answer, so you do not need a "something else" option — but do cover the realistic space with your 2–4.
- **multiSelect:** default `false`. Use `true` only when choices genuinely combine (e.g. "which report sections do you want?").

If `AskUserQuestion` is unavailable in the current harness, fall back to a single numbered prose block with the same content — one message, all questions, each with options and a marked default — and parse the reply. Never trickle questions across messages.

## Building a safe default for every question

Every question ships one option marked `(default)` — the one you would pick if the human never answered. Construct it so that accepting all defaults yields a **safe, reversible, sensible** run.

Default-selection rules:
- **Reversibility first.** The default is the option that is easiest to undo (paper over live, dry-run over apply, staged over published).
- **Least surprise.** Prefer the option that matches the stated goal and existing conventions in the repo/files.
- **Least commitment.** When unsure, the default defers cost (smaller size, narrower scope) rather than commits it.
- **Approvals default to no-op.** For any category-3 approval, the default is *do not perform the irreversible action* and the description states plainly what is irreversible.

If you cannot name a safe default for a question, that question is **high-stakes and un-defaultable** — mark it so; on timeout the run must stop, not guess (see `answer-record.md`).

## Writing a good question

- **One decision per question.** Do not bundle "which stack and which deploy target" into one card.
- **Options are genuinely distinct.** Not three phrasings of the same answer (leading the witness).
- **Surface the consequence in the description.** The human should not have to infer what a choice costs.
- **Neutral framing.** Do not editorialize toward your preferred option beyond the honest `(default)` mark.
- **Self-contained.** Assume the human has not read the transcript. Give the minimum context to decide inside the `question` text.

## Worked examples

### Good — batched, blocking, defaulted

> **Q1 [Risk cap]** What max per-trade risk should the strategy use?
> - `0.5% (default)` — conservative; matches the repo's existing configs. Reversible via config.
> - `1%` — moderate.
> - `2%` — aggressive; larger drawdowns.
>
> **Q2 [Acceptance]** What counts as "done" for this backtest?
> - `Deflated Sharpe > 0 on OOS (default)` — leakage-safe bar this repo uses elsewhere.
> - `Raw Sharpe > 1` — simpler, weaker.
> - `Beat the existing baseline` — I'll pull the baseline's OOS Sharpe first.

Two questions, one round, each defaulted, consequences shown. The human can accept both defaults in two clicks.

### Bad — should not have been asked

> "Should I use pandas or polars to load the CSV?"

Inferable (check what the repo already imports) and low-stakes. Decide it, note the assumption, don't ask.

### Bad — approval smuggled as preference

> "Deploy to live? Options: `Yes (default)` / `No`"

Irreversible action with the dangerous option as default and no consequence stated. Rewrite: default `No — stay on paper`, and the `Yes` description must say "real capital, fills are irreversible."

### Bad — flood

Fifteen questions where twelve are inferable from the spec and files. Re-run the blocking filter; ship the 3 that actually block.
