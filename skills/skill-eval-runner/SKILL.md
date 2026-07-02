---
name: skill-eval-runner
version: 0.1.0
description: >-
  Score a single target SKILL.md against THE FRONTIER AGENT-SKILL RUBRIC (a
  versioned 5-dimension criteria schema) and gate CI so a skill can never
  regress below pass. Use when the user says "score this skill", "does this
  SKILL.md pass the frontier rubric", "grade a skill", "add a skill quality
  gate to CI", "fail the build if a skill drops below pass", or after
  authoring/healing a skill to prove it clears the bar. Runs a deterministic
  FORMAT pre-pass (YAML parses, name == directory slug, description <= 1024
  chars, version present, no broken references/ links, router size) then an
  LLM-judge pass over DEPTH, COMPLETENESS, STRUCTURED DISCLOSURE, and
  FRONTIER-MODEL GUIDELINES using 0-5 anchors; PASS requires every dimension
  >= 4. The regression gate diffs a fresh scorecard against a committed
  baseline. Do NOT use for whole-fleet audits, duplicate/collision detection,
  or catalogue health (use meta-skill), nor to author a skill from scratch
  (use skill-creator) — this scores and gates one already-written skill.
---

# skill-eval-runner

Turn THE FRONTIER AGENT-SKILL RUBRIC from tribal knowledge — today it lives only
implicitly inside meta-skill heal workflows and git history — into an **explicit,
versioned artifact** you can score against and enforce in CI. This skill owns
three things: the rubric **schema** (`references/rubric-v1.json`), the **runner**
that scores one `SKILL.md` against it, and the **regression gate** that fails a
build when a skill drops below pass.

Scope is deliberately narrow: **one skill, one scorecard, one gate decision.**
For everything wider, route out:

- **meta-skill** — fleet governance: catalogue every repo, score ecosystem
  health, find duplicate names and trigger collisions. Run it *after* this skill
  to fold a passing skill into the wider library.
- **skill-creator** — authoring and iterating a single skill (draft → evals →
  rewrite). Run it *before* this skill to produce the SKILL.md you then score.

Think of the pipeline as: **skill-creator writes → skill-eval-runner scores &
gates → meta-skill integrates.**

## The rubric (v1, frozen)

Score each dimension **0–5**. **PASS = every dimension >= 4** (no averaging — a
single 3 fails the skill). The five dimensions:

1. **FORMAT** — frontmatter parses; `name` EXACTLY equals the directory slug;
   description <= 1024 chars stating WHAT + WHEN-to-use + WHEN-NOT; `version`
   present; scannable markdown; no broken `references/` links.
2. **DEPTH** — technically accurate, expert-level; concrete commands/APIs/params,
   not vague prose; deep material pushed to `references/`.
3. **COMPLETENESS** — covers the full scope; edge cases, failure modes,
   boundaries; no gap a practitioner hits in real use.
4. **STRUCTURED DISCLOSURE** — SKILL.md is a concise router (<~12 KB) that
   delegates depth to `references/`; not a wall of text.
5. **FRONTIER-MODEL GUIDELINES** — imperative voice; clear triggers/anti-triggers;
   explicit boundaries; cross-links to sibling skills; no redundancy; nothing
   misleading.

The authoritative, machine-readable form (per-dimension checks + calibrated 0–5
anchors) is `references/rubric-v1.json`. Never hand-edit a score without reading
the anchors — read `references/rubric-schema.md` before you judge.

## Run it

The runner is **hybrid**: a deterministic pass handles everything a script can
prove (FORMAT + the router-size half of STRUCTURED DISCLOSURE); an LLM-judge pass
scores the dimensions that need reading comprehension.

```bash
# 1. Deterministic pass — emits a scorecard with FORMAT auto-scored,
#    judge dimensions left null. Exit 0 if auto-checks clean, 1 if not.
python3 scripts/eval_skill.py /path/to/target-skill-dir --out scorecard.json

# 2. Judge pass — YOU (the model) read the target SKILL.md + its references/,
#    score DEPTH / COMPLETENESS / STRUCTURED DISCLOSURE / FRONTIER-MODEL
#    GUIDELINES against the anchors, and write a small judge file:
#       {"depth":4,"completeness":5,"structured_disclosure":4,"frontier_guidelines":4}

# 3. Merge judge scores → final PASS/FAIL (exit 0 pass, 1 fail).
python3 scripts/eval_skill.py /path/to/target-skill-dir \
    --judge-scores judge.json --out scorecard.json
```

Step 2 is not optional and not a rubber stamp. The exact judge procedure —
what to read, how to apply each anchor, how to write concrete failure notes so a
score is defensible — is in **`references/scoring-runner.md`**. Read it before
you assign any judge score.

## Gate CI

The gate turns a scorecard into a build pass/fail and, given a committed
baseline, blocks regressions.

```bash
# Fail (exit 1) if any dimension < 4.
python3 scripts/gate.py scorecard.json

# Also fail if any dimension dropped vs the last green run.
python3 scripts/gate.py scorecard.json --baseline baseline.scorecard.json
```

Wire it into a repo with the ready workflow in
**`references/skill-eval.github-action.yml`**. The full gate contract — exit
codes, baseline semantics, how to store and bump the baseline, and how to gate a
whole directory of skills — is in **`references/regression-gate.md`**.

## Version the rubric, don't fork it

The rubric is a released artifact with its own SemVer (`rubric_version` inside
`rubric-v1.json`, independent of this skill's `version`). Tightening a check or
adding a dimension is a rubric release, not an ad-hoc edit — every scorecard
records the `rubric_version` it was graded under so old results stay
interpretable. The rules for a MAJOR/MINOR/PATCH rubric bump (and how to add
`rubric-v2.json` without breaking committed baselines) are in
**`references/rubric-schema.md`**.

## Optional: auto-fix a failing skill

When a skill fails on DEPTH or FRONTIER-MODEL GUIDELINES, you can close the loop
by evolving the weakest text (usually the `description`) with the user's MIT
`gepa` crate as the optimizer and this rubric's score as the fitness signal.
This is opt-in and off the critical path — see **`references/gepa-autofix.md`**.

## Boundaries

- **Scores, does not rewrite.** The runner reports; fixing the skill is
  skill-creator's job (or the optional gepa loop). Keep the roles separate.
- **One skill at a time.** Directory sweeps are a thin loop over single runs
  (see the gate reference) — this is not a catalogue tool. That is meta-skill.
- **Deterministic checks are load-bearing, judge scores are earned.** Never mark
  a judge dimension >= 4 without a concrete, cited reason in the scorecard notes.
- **Original content only.** This skill and its scripts are original work; they
  read source repos for accuracy but copy no text or code from noncommercial,
  BUSL, AGPL, or proprietary sources.
