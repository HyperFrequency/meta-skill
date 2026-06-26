#!/usr/bin/env python3
"""Orchestrator entrypoint for /relentless-inception.

This is a *scaffold*. The real agent dispatch happens inside Claude Code
when the skill is invoked: the LLM reads SKILL.md + the relevant
references/ + agents/ files and spawns subagents via the Agent tool.

What this script does:
  - Parse CLI flags (matches references/settings-and-flags.md)
  - Resolve a run_id, scaffold the run-state directory
  - Load (or create) the RunManifest
  - Run check_prereqs.sh, refuse to start on fatal failure
  - Refuse to start if main/master is the current branch
  - Watch for the kill switch and trigger files (rescue path)
  - Print the resolved plan + entry banner; then exit, leaving the
    Claude-Code-side orchestrator (the LLM reading this skill) in charge.

When the skill's runtime layer matures (Slice C+), this script gains real
dispatch logic that imports `orchestrator.RunManifest` from the
neuro-harness companion package and drives the loop. For now it documents
the contract.

Usage:
    orchestrator.py "<task>" \\
        --plan=staff-up|kitchen-sink-monorepo|lawyer-up \\
        --exec=gigaprompt|proof-loops|skynet|exaflop-infiniloop \\
        --intensity=1|2|3 \\
        --budget-soft-hours=N \\
        --budget-hard-usd=N \\
        --resume=<run_id>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
HOME = Path.home()
STATE_DIR = HOME / ".claude" / "relentless-inception"
KILL_SWITCH = STATE_DIR / "KILL"
TRIGGERS_DIR = STATE_DIR / "triggers"
RUNS_DIR = STATE_DIR / "runs"


def run_id_for(task: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    short = uuid.uuid4().hex[:6]
    return f"ri-{stamp}-{short}"


def check_prereqs() -> int:
    script = SKILL_DIR / "scripts" / "check_prereqs.sh"
    if not script.exists():
        print(f"error: {script} missing", file=sys.stderr)
        return 1
    return subprocess.run(["bash", str(script)]).returncode


def refuse_if_main_branch() -> None:
    """Per the skill's safety rules, never run on main/master."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        branch = result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return  # Not a git repo — caller's responsibility
    if branch in {"main", "master"}:
        print(
            f"error: refusing to run /relentless-inception on '{branch}'.\n"
            "       Create or switch to a feature branch first.",
            file=sys.stderr,
        )
        sys.exit(2)


def check_kill_switch() -> None:
    if KILL_SWITCH.exists() and KILL_SWITCH.stat().st_size > 0:
        print(
            f"error: kill switch is set at {KILL_SWITCH}.\n"
            "       Remove it (or empty it) before starting a new run.",
            file=sys.stderr,
        )
        sys.exit(3)


def scaffold_run(run_id: str, args: argparse.Namespace) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "rescues").mkdir(exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        return run_dir

    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "prompt": args.task,
        "planning_mode": args.plan,
        "execution_mode": args.exec,
        "intensity": args.intensity,
        "orchestrator_review_style": args.orchestrator_review_style,
        "subagent_review_style": args.subagent_review_style,
        "budget_soft_hours": args.budget_soft_hours,
        "budget_hard_usd": args.budget_hard_usd,
        "allow_degradation": args.allow_degradation,
        "platform": None,
        "runtime": None,
        "acceptance_criteria": [],
        "phases": [],
        "shakedown_cycles": [],
        "rescue_cycles": [],
        "gate_history": [],
        "stop_reason": None,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return run_dir


def import_orchestrator_package() -> object | None:
    """If running inside the neuro-harness workspace, import the companion
    types. Otherwise return None and the caller uses stdlib shapes."""
    try:
        import orchestrator  # noqa: F401  (companion package from neuro-harness)
        return orchestrator
    except ImportError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="relentless-inception",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", nargs="?", default="")
    parser.add_argument("--plan", choices=["staff-up", "kitchen-sink-monorepo", "lawyer-up"], default="staff-up")
    parser.add_argument("--exec", dest="exec", choices=["gigaprompt", "proof-loops", "skynet", "exaflop-infiniloop"], default="proof-loops")
    parser.add_argument("--intensity", type=int, choices=[1, 2, 3], default=3)
    parser.add_argument("--orchestrator-review-style", choices=["code-function-nexus", "adversarial-review", "simulate-users-harness"], default="adversarial-review")
    parser.add_argument("--subagent-review-style", choices=["verify-proof", "adversarial-pass-fail"], default="verify-proof")
    parser.add_argument("--budget-soft-hours", type=int, default=40)
    parser.add_argument("--budget-hard-usd", type=int, default=50)
    parser.add_argument("--allow-degradation", action="store_true")
    parser.add_argument("--resume", default=None, help="resume an existing run_id instead of starting a new one")
    args = parser.parse_args(argv)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TRIGGERS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    check_kill_switch()

    rc = check_prereqs()
    if rc != 0:
        print(f"\nrefusing to start — fix prereqs first (check_prereqs.sh exited {rc})", file=sys.stderr)
        return rc

    refuse_if_main_branch()

    run_id = args.resume or run_id_for(args.task)
    run_dir = scaffold_run(run_id, args)

    companion = import_orchestrator_package()
    companion_status = "available" if companion else "absent (running in stdlib-only mode)"

    print(f"""
╭──────────────────────────────────────────────────────────────╮
│ /relentless-inception                                         │
├──────────────────────────────────────────────────────────────┤
│ run_id           : {run_id}
│ planning mode    : {args.plan}
│ execution mode   : {args.exec}
│ intensity        : {args.intensity}
│ budget soft (h)  : {args.budget_soft_hours}
│ budget hard ($)  : {args.budget_hard_usd}
│ allow degradation: {args.allow_degradation}
│ orchestrator pkg : {companion_status}
│ run dir          : {run_dir}
╰──────────────────────────────────────────────────────────────╯

The Claude Code orchestrator (the LLM reading this skill) now takes over:
  1. read SKILL.md + the planning-mode reference for {args.plan}
  2. spawn planner + architecture-analyzer (see agents/planner.md, agents/architecture-analyzer.md)
  3. run the plan gate via scripts/adversarial_review.sh
  4. proceed per references/execution-modes.md#{args.exec}

The background-agent watches via the Stop hook + scripts/stall_watchdog.sh.
The relay hook (scripts/relentless_relay.sh) is the rescue entry point.

To stop: `touch {KILL_SWITCH}` and wait up to 60 seconds.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
