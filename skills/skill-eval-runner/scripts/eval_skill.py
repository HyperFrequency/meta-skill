#!/usr/bin/env python3
"""eval_skill.py — score one target SKILL.md against the Frontier Agent-Skill Rubric.

Hybrid runner:
  * A DETERMINISTIC pass proves everything a script can prove — the FORMAT
    dimension and the router-size half of STRUCTURED DISCLOSURE. It emits a
    scorecard with those dimensions auto-scored and the reading-comprehension
    dimensions (DEPTH, COMPLETENESS, the qualitative half of STRUCTURED
    DISCLOSURE, FRONTIER-MODEL GUIDELINES) left null.
  * An LLM-JUDGE pass (done by the model, not this script) fills the null
    dimensions against the anchors in references/rubric-v1.json. Feed those
    scores back in via --judge-scores to compute the final PASS/FAIL.

Stdlib + PyYAML only. No network, no pip installs.

Exit codes:
  0  auto-checks clean (no --judge-scores) OR final scorecard PASSES
  1  a hard auto-check failed, OR final scorecard FAILS
  2  bad invocation (missing SKILL.md, unreadable judge file, etc.)

Original work. Reads no third-party skill text; the rubric it enforces is the
user's own, encoded in references/rubric-v1.json.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"error: PyYAML is required but could not be imported: {exc}", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
RUBRIC_PATH = os.path.join(SKILL_ROOT, "references", "rubric-v1.json")

# Judge-only dimension ids in rubric order (filled by the model, not this script).
JUDGE_DIMENSIONS = ("depth", "completeness", "structured_disclosure", "frontier_guidelines")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Local paths the SKILL.md points at. We only follow references/ and scripts/
# so we don't chase external URLs or code identifiers that happen to contain a slash.
LOCAL_LINK_RE = re.compile(r"(?<![\w./-])((?:references|scripts)/[\w./-]+?)(?=[\s`\"')\]]|$)")

WHEN_CUES = ("use when", "trigger", "when the user", "when you", "reach for", "invoke when")
WHEN_NOT_CUES = ("not for", "do not use", "don't use", "instead", "rather than", "skip ", "not when", "not to ")


def load_rubric():
    with open(RUBRIC_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_skill_md(skill_dir):
    """Return (raw_text, byte_size) for the SKILL.md in skill_dir (case-tolerant)."""
    for name in ("SKILL.md", "skill.md"):
        path = os.path.join(skill_dir, name)
        if os.path.isfile(path):
            data = open(path, "rb").read()
            return data.decode("utf-8", errors="replace"), len(data)
    return None, 0


def parse_frontmatter(raw):
    """Return (frontmatter_dict_or_None, parse_ok)."""
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return None, False
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, False
    if not isinstance(data, dict):
        return None, False
    return data, True


def find_broken_links(raw, skill_dir):
    """Every references//scripts/ path in SKILL.md that does not resolve on disk."""
    broken = []
    for rel in set(LOCAL_LINK_RE.findall(raw)):
        cleaned = rel.rstrip(".,)")
        if not os.path.exists(os.path.join(skill_dir, cleaned)):
            broken.append(cleaned)
    return sorted(broken)


def run_deterministic(skill_dir, rubric):
    """Compute auto_checks + auto-scored FORMAT and router-size for STRUCTURED DISCLOSURE."""
    slug = os.path.basename(os.path.normpath(skill_dir))
    raw, byte_size = read_skill_md(skill_dir)
    if raw is None:
        return None, slug, None, 0

    frontmatter, parse_ok = parse_frontmatter(raw)
    fm = frontmatter or {}
    name = str(fm.get("name", "")).strip()
    description = str(fm.get("description", "") or "").strip()
    version = fm.get("version", None)

    desc_lower = description.lower()
    checks = {
        "frontmatter_parses": parse_ok,
        "name_matches_slug": bool(name) and name == slug,
        "description_present": bool(description),
        "description_within_cap": len(description) <= 1024,
        "description_states_what": bool(description),  # non-empty opening capability clause
        "description_states_when": any(cue in desc_lower for cue in WHEN_CUES),
        "description_states_when_not": any(cue in desc_lower for cue in WHEN_NOT_CUES),
        "version_present": version is not None and str(version).strip() != "",
        "scannable_markdown": ("\n#" in raw or "\n-" in raw or "\n*" in raw or "```" in raw),
        "no_broken_reference_links": len(find_broken_links(raw, skill_dir)) == 0,
    }
    broken = find_broken_links(raw, skill_dir)
    target_bytes = _router_target_bytes(rubric)
    router_ok = byte_size <= target_bytes

    auto_checks = {
        "slug": slug,
        "name": name,
        "description_length": len(description),
        "version": None if version is None else str(version),
        "skill_bytes": byte_size,
        "router_target_bytes": target_bytes,
        "router_within_budget": router_ok,
        "broken_links": broken,
        "checks": checks,
    }

    format_score, format_notes = _score_format(checks, len(description))
    sd_note = (
        f"router size {byte_size} B <= {target_bytes} B budget"
        if router_ok else
        f"router size {byte_size} B EXCEEDS {target_bytes} B budget — move depth into references/"
    )
    return auto_checks, slug, (format_score, format_notes), (router_ok, sd_note)


def _router_target_bytes(rubric):
    for dim in rubric["dimensions"]:
        if dim["id"] == "structured_disclosure":
            for chk in dim["checks"]:
                if chk["id"] == "router_size":
                    return int(chk.get("target_bytes", 12288))
    return 12288


def _score_format(checks, desc_len):
    """Deterministic 0-5 FORMAT score from the check results, per rubric anchors."""
    hard = [
        "frontmatter_parses", "name_matches_slug", "description_present",
        "description_within_cap", "version_present", "no_broken_reference_links",
    ]
    soft = ["description_states_what", "description_states_when",
            "description_states_when_not", "scannable_markdown"]
    hard_fails = [c for c in hard if not checks[c]]
    soft_fails = [c for c in soft if not checks[c]]

    notes = []
    if hard_fails:
        notes.append("HARD failures: " + ", ".join(hard_fails))
    if soft_fails:
        notes.append("soft weaknesses: " + ", ".join(soft_fails))
    if desc_len > 900:
        notes.append(f"description is {desc_len}/1024 chars — tightening headroom recommended")

    if len(hard_fails) >= 2:
        score = 0
    elif len(hard_fails) == 1:
        score = 2
    elif soft_fails:
        # All hard checks pass. One soft weakness -> 4; more -> 3.
        score = 4 if len(soft_fails) == 1 else 3
    else:
        score = 5
    if not notes:
        notes.append("all FORMAT checks pass")
    return score, notes


def build_scorecard(skill_dir, rubric, judge_scores):
    auto_checks, slug, fmt, sd = run_deterministic(skill_dir, rubric)
    if auto_checks is None:
        return None

    format_score, format_notes = fmt
    router_ok, sd_note = sd

    dimensions = {
        "format": {"score": format_score, "auto": True, "notes": format_notes},
        "depth": {"score": None, "auto": False, "notes": []},
        "completeness": {"score": None, "auto": False, "notes": []},
        "structured_disclosure": {"score": None, "auto": False, "notes": [sd_note]},
        "frontier_guidelines": {"score": None, "auto": False, "notes": []},
    }

    if judge_scores:
        for dim_id in JUDGE_DIMENSIONS:
            if dim_id in judge_scores:
                score = int(judge_scores[dim_id])
                if not 0 <= score <= 5:
                    raise ValueError(f"judge score for '{dim_id}' out of range 0-5: {score}")
                dimensions[dim_id]["score"] = score

    filled = [d["score"] for d in dimensions.values() if d["score"] is not None]
    all_filled = all(d["score"] is not None for d in dimensions.values())
    min_score = min(filled) if filled else None
    passed = (min_score >= rubric["pass_threshold"]) if all_filled else None

    return {
        "rubric_id": rubric["rubric_id"],
        "rubric_version": rubric["rubric_version"],
        "pass_threshold": rubric["pass_threshold"],
        "target": os.path.abspath(skill_dir),
        "slug": slug,
        "generated": datetime.now(timezone.utc).isoformat(),
        "auto_checks": auto_checks,
        "dimensions": dimensions,
        "min_score": min_score,
        "pass": passed,
    }


def print_summary(card):
    print(f"skill-eval-runner :: {card['slug']}  (rubric {card['rubric_version']})")
    for dim_id, dim in card["dimensions"].items():
        score = "  ?" if dim["score"] is None else f"  {dim['score']}"
        tag = "auto" if dim["auto"] else "judge"
        print(f"  [{score}] {dim_id:<22} ({tag})")
        for note in dim["notes"]:
            print(f"          - {note}")
    if card["pass"] is None:
        missing = [k for k, v in card["dimensions"].items() if v["score"] is None]
        print(f"  => INCOMPLETE — judge dimensions still null: {', '.join(missing)}")
    else:
        verdict = "PASS" if card["pass"] else "FAIL"
        print(f"  => {verdict} (min dimension = {card['min_score']}, threshold = {card['pass_threshold']})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score a SKILL.md against the Frontier Agent-Skill Rubric.")
    ap.add_argument("skill_dir", help="Path to the target skill directory (containing SKILL.md).")
    ap.add_argument("--judge-scores", help="JSON file/inline with {depth,completeness,structured_disclosure,frontier_guidelines} in 0-5.")
    ap.add_argument("--out", help="Write the scorecard JSON to this path.")
    ap.add_argument("--auto-only", action="store_true", help="Exit 0 on clean auto-checks even without judge scores.")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.skill_dir):
        print(f"error: not a directory: {args.skill_dir}", file=sys.stderr)
        return 2

    rubric = load_rubric()

    judge_scores = None
    if args.judge_scores:
        try:
            if os.path.isfile(args.judge_scores):
                judge_scores = json.load(open(args.judge_scores, encoding="utf-8"))
            else:
                judge_scores = json.loads(args.judge_scores)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: could not read --judge-scores: {exc}", file=sys.stderr)
            return 2

    try:
        card = build_scorecard(args.skill_dir, rubric, judge_scores)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if card is None:
        print(f"error: no SKILL.md found in {args.skill_dir}", file=sys.stderr)
        return 2

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(card, handle, indent=2)
            handle.write("\n")

    print_summary(card)

    # Exit-code policy.
    if card["pass"] is True:
        return 0
    if card["pass"] is False:
        return 1
    # Incomplete (no judge scores yet): success only if the auto-checks are clean.
    auto_hard_ok = card["dimensions"]["format"]["score"] >= rubric["pass_threshold"]
    if args.auto_only or judge_scores is None:
        return 0 if auto_hard_ok else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
