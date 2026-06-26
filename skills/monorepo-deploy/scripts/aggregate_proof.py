#!/usr/bin/env python3
"""Aggregate pkg/.proof/<target>.ready.json files into ALL.ready.json.

Usage: aggregate_proof.py <proof_dir>

Exits non-zero if any target is missing, any smoke_tests.exit_code != 0,
or any dashboards_reachable URL is absent.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_TARGETS = {
    "macos-arm64",
    "linux-x86_64",
    "linux-aarch64",
    "docker",
    "cloud-modal",
    "cloud-lambda",
    "cloud-ray",
}

REQUIRED_MODELS = {
    "Octen-Embedding-8B.Q8_0.gguf",
    "qwen3-reranker-0.6b-q8_0.gguf",
    "qmd-query-expansion-1.7B-q4_k_m.gguf",
}


def main(proof_dir_str: str) -> int:
    proof_dir = Path(proof_dir_str)
    if not proof_dir.is_dir():
        print(f"ERROR: {proof_dir} is not a directory", file=sys.stderr)
        return 2

    ready_files = sorted(proof_dir.glob("*.ready.json"))
    ready_files = [f for f in ready_files if f.name != "ALL.ready.json"]

    targets_green: list[str] = []
    targets_failed: list[tuple[str, str]] = []
    dashboards_all_green = True
    models_all_green = True
    version: str | None = None

    for f in ready_files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            targets_failed.append((f.stem, f"invalid JSON: {e}"))
            continue

        target = data.get("target")
        if target not in EXPECTED_TARGETS:
            targets_failed.append((target or f.stem, "target not in EXPECTED_TARGETS"))
            continue

        if version is None:
            version = data.get("version", "UNKNOWN")

        for test in data.get("smoke_tests", []):
            if test.get("exit_code") != 0:
                targets_failed.append((target, f"smoke {test.get('name')} exit {test.get('exit_code')}"))
                break
        else:
            dashboards = data.get("dashboards_reachable", {})
            if not dashboards.get("optuna-dashboard"):
                dashboards_all_green = False
                targets_failed.append((target, "optuna-dashboard URL missing"))
                continue

            present = set(data.get("models_present", []))
            if not REQUIRED_MODELS.issubset(present):
                models_all_green = False
                targets_failed.append((target, f"models missing: {REQUIRED_MODELS - present}"))
                continue

            targets_green.append(target)

    targets_missing = sorted(EXPECTED_TARGETS - set(targets_green) - {t for t, _ in targets_failed})
    failed_only = sorted({t for t, _ in targets_failed})

    out = {
        "run_id": proof_dir.parent.parent.name if proof_dir.parent.name == ".proof" else "UNKNOWN",
        "version": version or "UNKNOWN",
        "targets_green": sorted(targets_green),
        "targets_missing": targets_missing,
        "targets_failed": [{"target": t, "reason": r} for t, r in targets_failed],
        "dashboards_all_green": dashboards_all_green and not failed_only,
        "models_all_green": models_all_green,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps(out, indent=2))

    if targets_missing or failed_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
