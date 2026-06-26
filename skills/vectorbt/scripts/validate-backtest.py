#!/usr/bin/env python3
"""validate-backtest.py — smoke-test an emitted vectorbt backtest.

Runs the supplied script file, intercepts the `pf` (Portfolio) object,
and prints sanity metrics. Exits non-zero if obvious bugs are detected
(all-win no-drawdown curve, zero trades, monotonically-rising equity
with no losses).

Usage:
    python validate-backtest.py path/to/backtest.py
    python validate-backtest.py path/to/backtest.py --pf-name portfolio

The script must define a vectorbt Portfolio object at module scope
(default name: `pf`).
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys


def load_module(script_path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("bt_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=pathlib.Path)
    parser.add_argument("--pf-name", default="pf", help="attribute name of the Portfolio object")
    args = parser.parse_args()

    if not args.script.is_file():
        print(f"[fail] not a file: {args.script}", file=sys.stderr)
        return 2

    mod = load_module(args.script)
    pf = getattr(mod, args.pf_name, None)
    if pf is None:
        print(f"[fail] module defines no `{args.pf_name}` at top level", file=sys.stderr)
        return 3

    print(f"[ok] loaded Portfolio from {args.script}")
    print(f"     total_return   = {pf.total_return()}")
    print(f"     sharpe_ratio   = {pf.sharpe_ratio()}")
    print(f"     max_drawdown   = {pf.max_drawdown()}")
    print(f"     trade count    = {pf.trades.count()}")
    entries = getattr(mod, "entries", None)
    exits = getattr(mod, "exits", None)
    if entries is not None:
        print(f"     entries.sum()  = {int(entries.sum())}")
    if exits is not None:
        print(f"     exits.sum()    = {int(exits.sum())}")

    # Sanity gates
    problems: list[str] = []
    if pf.trades.count() == 0:
        problems.append("zero trades — probably no entries fired")
    dd = float(pf.max_drawdown())
    tr = float(pf.total_return())
    if dd > -1e-6 and tr > 0:
        problems.append(
            f"max_drawdown={dd:.4g} with positive total_return={tr:.4g} — "
            "monotonic curve suggests look-ahead bias"
        )
    if problems:
        print("[fail] sanity failures:")
        for p in problems:
            print(f"   - {p}")
        return 10
    print("[ok] sanity checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
