#!/usr/bin/env python3
"""gate.py — CI regression gate for a skill scorecard.

Turns a scorecard (produced by eval_skill.py) into a build pass/fail:

  * BELOW PASS  — fail (exit 1) if any dimension score < pass_threshold, or if
    the scorecard is incomplete (a judge dimension is still null). A green build
    must prove a real, fully-scored PASS.
  * REGRESSION  — with --baseline, additionally fail if any dimension dropped
    below the baseline's score for that dimension, even when both clear the
    threshold. This freezes gains: a skill that scored 5 on DEPTH may not quietly
    slip to 4. Use --allow-regression to downgrade a drop from FAIL to a warning.

Rubric-version guard: if the scorecard and baseline were graded under different
rubric_versions, per-dimension comparison is unsafe (anchors may have moved), so
the regression check is skipped with a loud warning and only the below-pass check
applies. Re-baseline after a rubric bump (see references/regression-gate.md).

Exit codes:
  0  gate passed
  1  gate failed (below pass, incomplete, or a blocked regression)
  2  bad invocation (unreadable scorecard, etc.)

Stdlib only. Original work.
"""

import argparse
import json
import sys

DIMENSION_ORDER = ("format", "depth", "completeness", "structured_disclosure", "frontier_guidelines")


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dimension_scores(card):
    return {k: v.get("score") for k, v in card.get("dimensions", {}).items()}


def check_below_pass(card):
    """Return list of failure strings for missing or sub-threshold dimensions."""
    threshold = card.get("pass_threshold", 4)
    failures = []
    scores = dimension_scores(card)
    for dim_id in DIMENSION_ORDER:
        score = scores.get(dim_id)
        if score is None:
            failures.append(f"{dim_id}: NOT SCORED (incomplete scorecard)")
        elif score < threshold:
            failures.append(f"{dim_id}: {score} < {threshold} (below pass)")
    return failures


def check_regressions(card, baseline):
    """Return list of regression strings for dimensions that dropped vs baseline."""
    regressions = []
    now = dimension_scores(card)
    was = dimension_scores(baseline)
    for dim_id in DIMENSION_ORDER:
        new_score = now.get(dim_id)
        old_score = was.get(dim_id)
        if new_score is None or old_score is None:
            continue
        if new_score < old_score:
            regressions.append(f"{dim_id}: {new_score} < baseline {old_score} (regression)")
    return regressions


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regression gate for a skill scorecard.")
    ap.add_argument("scorecard", help="Path to the current scorecard JSON.")
    ap.add_argument("--baseline", help="Path to the last-green baseline scorecard JSON.")
    ap.add_argument("--allow-regression", action="store_true",
                    help="Treat per-dimension drops vs baseline as warnings, not failures.")
    args = ap.parse_args(argv)

    try:
        card = load(args.scorecard)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: could not read scorecard: {exc}", file=sys.stderr)
        return 2

    slug = card.get("slug", "?")
    print(f"gate :: {slug}  (rubric {card.get('rubric_version', '?')})")

    hard_failures = check_below_pass(card)

    regressions = []
    regression_blocking = False
    if args.baseline:
        try:
            baseline = load(args.baseline)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: could not read baseline: {exc}", file=sys.stderr)
            return 2
        if baseline.get("rubric_version") != card.get("rubric_version"):
            print(f"  WARNING: rubric_version mismatch "
                  f"(scorecard {card.get('rubric_version')} vs baseline {baseline.get('rubric_version')}); "
                  f"skipping regression check — re-baseline after a rubric bump.")
        else:
            regressions = check_regressions(card, baseline)
            regression_blocking = bool(regressions) and not args.allow_regression

    for line in hard_failures:
        print(f"  FAIL  {line}")
    for line in regressions:
        prefix = "FAIL " if not args.allow_regression else "WARN "
        print(f"  {prefix} {line}")

    if hard_failures or regression_blocking:
        print("  => GATE FAILED")
        return 1

    if card.get("pass") is not True:
        # Belt-and-suspenders: below-pass check already covers this, but never
        # let a scorecard whose own pass flag isn't True slip through green.
        print("  => GATE FAILED (scorecard pass flag is not True)")
        return 1

    print("  => GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
