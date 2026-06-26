#!/usr/bin/env python3
"""tearsheet.py — generate the HTML proof tearsheet for a run cycle.

Inputs:
  - run manifest (~/.claude/relentless-inception/runs/<run_id>/manifest.json)
  - cycle directory (~/.claude/relentless-inception/runs/<run_id>/cycle-<N>/)
    containing:
      - personas/*.json     (sim-user reports)
      - reasoning-traces/   (per-agent stream snapshots, optional)
      - tool-calls.jsonl    (filtered to "significant")
      - adversarial-verdicts/*.json
      - ship-report.json    (if shipped)
      - verdict.json        (from test-evaluator)

Output:
  - tearsheet.html (self-contained, no external requests)

Render strategy:
  - Use the template at assets/tearsheet_template.html.
  - Inject sections via simple {{PLACEHOLDER}} substitution.
  - Embed JSON payloads as <script type="application/json"> tags so the
    tearsheet stays inspectable without server-side help.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "assets" / "tearsheet_template.html"


def safe_read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def render_personas(cycle_dir: Path) -> str:
    personas_dir = cycle_dir / "personas"
    if not personas_dir.is_dir():
        return "<p><em>No persona reports for this cycle.</em></p>"
    rows = []
    for f in sorted(personas_dir.glob("*.json")):
        data = safe_read_json(f) or {}
        name = data.get("persona", f.stem)
        passed = data.get("passed_count", "?")
        failed = data.get("failed_count", "?")
        errors = len(data.get("errors", []))
        summary = html.escape(data.get("summary", ""))[:300]
        rows.append(
            f"<tr><td>{html.escape(str(name))}</td>"
            f"<td>{passed}</td><td>{failed}</td><td>{errors}</td>"
            f"<td>{summary}</td></tr>"
        )
    return (
        "<table><thead><tr><th>persona</th><th>pass</th><th>fail</th>"
        "<th>errors</th><th>summary</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_acceptance_criteria(manifest: dict, verdict: dict | None) -> str:
    criteria = manifest.get("acceptance_criteria", [])
    if not criteria:
        return "<p><em>No acceptance criteria recorded.</em></p>"
    status = (verdict or {}).get("criteria_status", {}) if verdict else {}
    rows = []
    for i, crit in enumerate(criteria):
        key = f"AC{i+1}"
        s = status.get(key, "?")
        cls = {"satisfied": "ok", "partial": "warn", "unsatisfied": "fail"}.get(s, "")
        rows.append(
            f"<tr class='{cls}'><td>{key}</td><td>{html.escape(str(crit))}</td>"
            f"<td>{html.escape(str(s))}</td></tr>"
        )
    return "<table><thead><tr><th>id</th><th>criterion</th><th>status</th></tr></thead>" \
           f"<tbody>{''.join(rows)}</tbody></table>"


def render_adversarial_verdicts(cycle_dir: Path) -> str:
    d = cycle_dir / "adversarial-verdicts"
    if not d.is_dir():
        return "<p><em>No adversarial verdicts for this cycle.</em></p>"
    rows = []
    for f in sorted(d.glob("*.json")):
        v = safe_read_json(f) or {}
        rows.append(
            f"<tr><td>{html.escape(f.stem)}</td>"
            f"<td>{html.escape(v.get('gate', '?'))}</td>"
            f"<td>{html.escape(v.get('verdict', '?'))}</td></tr>"
        )
    return "<table><thead><tr><th>name</th><th>gate</th><th>verdict</th></tr></thead>" \
           f"<tbody>{''.join(rows)}</tbody></table>"


def render_ship(cycle_dir: Path) -> str:
    ship = safe_read_json(cycle_dir / "ship-report.json")
    if not ship:
        return "<p><em>No ship event for this cycle.</em></p>"
    return f"<pre>{html.escape(json.dumps(ship, indent=2))}</pre>"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycle-dir", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    cycle_dir = Path(args.cycle_dir).expanduser().resolve()
    if not cycle_dir.is_dir():
        print(f"error: {cycle_dir} not a directory", file=sys.stderr)
        return 1

    manifest_path = cycle_dir.parent / "manifest.json"
    manifest = safe_read_json(manifest_path) or {}
    verdict = safe_read_json(cycle_dir / "verdict.json")

    if not TEMPLATE.exists():
        print(f"error: template missing at {TEMPLATE}", file=sys.stderr)
        return 1

    body = TEMPLATE.read_text()
    body = body.replace("{{RUN_ID}}", html.escape(str(manifest.get("run_id", "?"))))
    body = body.replace("{{CYCLE}}", html.escape(cycle_dir.name))
    body = body.replace("{{STARTED_AT}}", html.escape(str(manifest.get("started_at", "?"))))
    body = body.replace("{{ACCEPTANCE_CRITERIA}}", render_acceptance_criteria(manifest, verdict))
    body = body.replace("{{PERSONAS}}", render_personas(cycle_dir))
    body = body.replace("{{ADVERSARIAL_VERDICTS}}", render_adversarial_verdicts(cycle_dir))
    body = body.replace("{{SHIP_REPORT}}", render_ship(cycle_dir))
    body = body.replace("{{MANIFEST_JSON}}", html.escape(json.dumps(manifest, indent=2)))

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    print(f"tearsheet: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
