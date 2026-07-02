# Scoring runner — how to score a SKILL.md

The runner is **hybrid**. `scripts/eval_skill.py` proves the deterministic half;
the model (you) judges the reading-comprehension half. This file is the judge
protocol. Read it before assigning any judge score — a score without a concrete,
cited note is not a valid score.

## Step 1 — deterministic pass

```bash
python3 scripts/eval_skill.py /abs/path/to/target-skill-dir --out scorecard.json
```

Always pass an **absolute** path. The runner derives the directory slug from the
last path segment, so `.` or a trailing slash makes `name_matches_slug` compare
against the wrong string. This writes a scorecard with:

- `dimensions.format.score` — auto-computed 0–5 from the FORMAT checks.
- `dimensions.structured_disclosure.notes` — the router byte-size result (the
  auto half of dimension 4). Its **score stays null** — you still judge the
  "delegates to references / not a wall of text" half.
- `dimensions.{depth,completeness,frontier_guidelines}.score` — null, awaiting you.
- `auto_checks` — the raw booleans, `description_length`, `skill_bytes`,
  `broken_links`. Read these; they are your evidence for FORMAT.

Exit 1 here means a hard FORMAT check failed (name != slug, missing version,
over-cap description, broken `references/` link). Fix the skill and re-run before
judging — a skill that fails FORMAT cannot PASS regardless of the judge scores.

## Step 2 — read the target like a practitioner

For the judged dimensions, open and actually read:

1. The target `SKILL.md` end to end.
2. **Every** file under its `references/` and `scripts/` — depth lives there, and
   DEPTH/COMPLETENESS are unscoreable from the router alone.
3. When the skill wraps a library or tool, spot-check that its commands/APIs are
   real. Verify against the source repo or `context7`/`deep-tool-wiki`; do not
   accept an API you cannot confirm — an invented call caps DEPTH at 2.

## Step 3 — score each judged dimension against the anchors

Open `references/rubric-v1.json`. Each dimension carries `anchors` for 5/4/3/2/0
and a `checks` list with `hard`/`soft` severity. Rules:

- **Any hard-check failure caps the dimension at 2.** A soft weakness caps at 4.
- Pick the anchor whose description best matches what you actually found — do not
  average, do not round up out of politeness.
- **DEPTH** — is it concrete (real commands/flags/params) or vague prose? Is the
  deep material in `references/`? An accuracy error is a hard fail.
- **COMPLETENESS** — does it cover everything the description promises, plus edge
  cases and failure modes? Find one realistic scenario a practitioner hits that
  the skill leaves unaddressed — if you can, it is at most a 3.
- **STRUCTURED DISCLOSURE** — the size half is already in the notes; you add the
  judgment: does SKILL.md route to `references/` or inline depth it should
  delegate? Over budget *and* inlining depth is a 2.
- **FRONTIER-MODEL GUIDELINES** — imperative voice, crisp triggers AND
  anti-triggers, explicit boundaries, sibling cross-links, no redundancy,
  nothing misleading. Misleading guidance is a hard fail.

Write a one-line **note per dimension** naming the concrete evidence (a quote, a
missing section, a specific vague sentence). The scorecard is a record someone
else must be able to trust without re-reading the skill.

## Step 4 — merge and get the verdict

Write the judge scores to a small JSON file:

```json
{ "depth": 4, "completeness": 5, "structured_disclosure": 4, "frontier_guidelines": 4 }
```

Then merge:

```bash
python3 scripts/eval_skill.py /abs/path/to/target-skill-dir \
    --judge-scores judge.json --out scorecard.json
```

`--judge-scores` also accepts an inline JSON string. The runner recomputes
`min_score` and `pass` (= every dimension >= `pass_threshold`), prints the
verdict, and exits **0 on PASS, 1 on FAIL**. Scores outside 0–5 are rejected
(exit 2) so a typo can't fake a pass.

## Failure modes the runner deliberately does NOT hide

- **A judge dimension left null** → `pass` is null, summary says INCOMPLETE. With
  no `--judge-scores`, exit code reflects only the auto-checks (0 if FORMAT is
  clean). Never report a null-pass scorecard as green.
- **`name_matches_slug` false on a path you know is fine** → you passed `.`,
  a symlink, or a trailing slash. Re-run with the real absolute directory.
- **Broken-link false negatives** → the runner only follows `references/` and
  `scripts/` paths. A link written as a bare filename or an external URL is not
  checked; judge those by eye under FRONTIER-MODEL GUIDELINES.
- **Heuristic WHEN/WHEN-NOT checks** are soft cues (substring match on phrases
  like "not for", "instead"). They can miss a well-written anti-trigger phrased
  unusually — treat a soft FORMAT ding as a prompt to read the description, not
  as gospel.

## Where this sits

- Producing the SKILL.md you score → **skill-creator**.
- Enforcing the scorecard in CI → `references/regression-gate.md`.
- Auto-evolving a failing description with the score as fitness →
  `references/gepa-autofix.md`.
- Rolling passing skills into the wider library → **meta-skill**.
