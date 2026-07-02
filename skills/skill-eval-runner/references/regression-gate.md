# Regression gate — enforcing the rubric in CI

`scripts/gate.py` turns a scorecard into a build pass/fail. It is the piece that
makes the rubric *load-bearing*: a skill that regressed below pass — or below
where it used to be — blocks the merge.

## Gate contract

```bash
python3 scripts/gate.py scorecard.json                      # below-pass gate
python3 scripts/gate.py scorecard.json --baseline base.json # + regression gate
python3 scripts/gate.py scorecard.json --baseline base.json --allow-regression
```

Two independent checks:

1. **Below-pass** (always on). Fails if any dimension score `< pass_threshold`
   (4) **or** the scorecard is incomplete (a judged dimension is still null) **or**
   its own `pass` flag is not exactly `true`. A green build must be a fully
   scored, genuine PASS — no partial credit, no "auto-checks were fine."
2. **Regression** (only with `--baseline`). Fails if any dimension dropped below
   the baseline's score for that dimension, *even when both clear 4*. This
   ratchets quality up: a skill that earned DEPTH 5 may not silently slide to 4.
   `--allow-regression` downgrades a drop from FAIL to a `WARN` line.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Gate passed |
| 1 | Gate failed (below pass, incomplete, or a blocked regression) |
| 2 | Bad invocation (unreadable scorecard/baseline) |

## Rubric-version guard

Per-dimension comparison is only meaningful when both scorecards were graded
under the same `rubric_version` — anchors move between rubric releases. If the
scorecard and baseline disagree on `rubric_version`, the gate prints a loud
WARNING, **skips the regression check**, and applies only the below-pass gate.
After any rubric bump you must **re-baseline** (see below) so future runs compare
like with like.

## The baseline: store it, bump it

The baseline is simply the last-green scorecard, committed next to the skill:

```
target-skill/
  SKILL.md
  .skill-eval/
    baseline.scorecard.json   # committed; the quality floor
```

- **Create it** the first time a skill reaches PASS: copy the passing scorecard
  to `.skill-eval/baseline.scorecard.json` and commit it.
- **Raise it** whenever a skill legitimately improves (a judged dimension goes
  up): re-run, confirm PASS, overwrite the baseline, commit. This locks in the
  gain — the ratchet only turns one way.
- **Re-baseline after a rubric bump**: grade under the new `rubric-vN.json`,
  confirm PASS, replace the baseline. The version guard above depends on this.

Never lower a baseline to make a red build go green — that defeats the gate. If a
drop is intentional (e.g. you deliberately moved depth out of a dimension's
scope), justify it in the commit message and use `--allow-regression` for that
one run, then re-baseline.

## Gating one skill in CI

Use `references/skill-eval.github-action.yml` as-is. It runs the deterministic
pass on every push touching the skill; the judged dimensions come from a
committed scorecard the author generated locally (CI has no model in the loop by
default). The workflow's job is to enforce that (a) FORMAT still passes
deterministically and (b) the committed scorecard PASSES and has not regressed
against the baseline.

## Gating a whole directory of skills

There is no batch mode by design — this skill scores **one** skill. To gate a
tree, loop over it in the CI step and fail if any single gate fails:

```bash
set -e
rc=0
for dir in skills/*/; do
  [ -f "$dir/SKILL.md" ] || continue
  card="$dir/.skill-eval/scorecard.json"
  base="$dir/.skill-eval/baseline.scorecard.json"
  [ -f "$card" ] || { echo "MISSING scorecard: $dir"; rc=1; continue; }
  if [ -f "$base" ]; then
    python3 scripts/gate.py "$card" --baseline "$base" || rc=1
  else
    python3 scripts/gate.py "$card" || rc=1
  fi
done
exit $rc
```

For an *ecosystem-wide* health view — duplicate names, trigger collisions,
coverage across many repos — that loop is the wrong tool. Use **meta-skill**; it
operates at fleet scale. This gate stays surgical: per-skill, pass/fail, no
catalogue.

## Common gate failures

- **"NOT SCORED (incomplete scorecard)"** — the committed scorecard was produced
  by the deterministic pass only. Run the judge pass (`references/scoring-runner.md`)
  and commit the merged scorecard.
- **"rubric_version mismatch … skipping regression check"** — you bumped the
  rubric but never re-baselined. Re-baseline under the new version.
- **Gate green locally, red in CI** — the scorecard's `target` path is absolute
  and machine-specific, but the gate only reads `dimensions`/`pass`, so path
  drift is harmless. A real divergence is usually an uncommitted scorecard or a
  stale baseline; diff the two files.
