#!/usr/bin/env python3
"""Merge identical proposals across graders and bucket by consensus.

Reads the per-grader grade artifacts produced by spawn_consortium.py
(05-self-improvement-HITL/grades/<period>/<grader-id>/*.md), extracts every
"### Proposal: <slug>" block, deduplicates near-identical proposals by
Jaccard similarity on stemmed slug tokens (threshold 0.6, per
references/consortium-protocol.md), and buckets the unique proposals by how
many graders raised them:

    count >= 2  -> HITL batch          (consensus)
    count == 1  -> low-consensus       (informational only, never auto-applied)

This script is invoked by /recursive-self-improvement between Phase 1
(consortium grading) and Phase 3 (HITL gate).

Usage:
    dedup_proposals.py --period <YYYY-MM-DD> [--threshold 0.6]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(os.environ.get("NLR_ROOT", Path(__file__).resolve().parents[4]))
GRADES_DIR = REPO_ROOT / "05-self-improvement-HITL" / "grades"

PROPOSAL_HEADER = re.compile(r"^###\s*Proposal:\s*(?P<slug>.+?)\s*$", re.MULTILINE)
TOKEN = re.compile(r"[a-z0-9]+")


class Proposal(NamedTuple):
    slug: str
    grader_id: str
    body: str


def slug_tokens(slug: str) -> frozenset[str]:
    """Lowercase alphanumeric tokens, naive plural stemming (trailing 's')."""
    tokens = {t[:-1] if t.endswith("s") and len(t) > 3 else t
              for t in TOKEN.findall(slug.lower())}
    return frozenset(tokens)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def parse_proposals(grade_file: Path, grader_id: str) -> list[Proposal]:
    text = grade_file.read_text(encoding="utf-8")
    matches = list(PROPOSAL_HEADER.finditer(text))
    proposals: list[Proposal] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        proposals.append(Proposal(slug=m.group("slug"), grader_id=grader_id,
                                  body=text[start:end].strip()))
    return proposals


def cluster(proposals: list[Proposal], threshold: float) -> list[list[Proposal]]:
    """Greedy single-link clustering by slug-token Jaccard >= threshold."""
    clusters: list[list[Proposal]] = []
    token_cache = {id(p): slug_tokens(p.slug) for p in proposals}
    for p in proposals:
        placed = False
        for c in clusters:
            if any(jaccard(token_cache[id(p)], token_cache[id(q)]) >= threshold for q in c):
                c.append(p)
                placed = True
                break
        if not placed:
            clusters.append([p])
    return clusters


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--period", required=True, help="YYYY-MM-DD (grades subdir)")
    ap.add_argument("--threshold", type=float, default=0.6,
                    help="Jaccard similarity threshold for merging (default 0.6)")
    args = ap.parse_args()

    period_dir = GRADES_DIR / args.period
    if not period_dir.is_dir():
        print(f"ERROR: no grades found at {period_dir}", file=sys.stderr)
        return 1

    proposals: list[Proposal] = []
    for grader_dir in sorted(p for p in period_dir.iterdir() if p.is_dir()):
        for grade_file in sorted(grader_dir.glob("*.md")):
            proposals.extend(parse_proposals(grade_file, grader_dir.name))

    if not proposals:
        print("No proposals extracted; nothing to dedup.", file=sys.stderr)
        return 0

    consensus, low_consensus = [], []
    for c in cluster(proposals, args.threshold):
        graders = sorted({p.grader_id for p in c})
        entry = {
            "slug": c[0].slug,
            "graders": graders,
            "count": len(graders),
            "variants": [{"grader": p.grader_id, "body": p.body} for p in c],
        }
        (consensus if len(graders) >= 2 else low_consensus).append(entry)

    result = {"period": args.period, "threshold": args.threshold,
              "consensus": consensus, "low_consensus": low_consensus}
    json.dump(result, sys.stdout, indent=2)
    print()
    print(f"\n{len(consensus)} consensus proposal(s) for HITL, "
          f"{len(low_consensus)} low-consensus (informational only)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
