#!/usr/bin/env python3
"""compare-pine-reference.py — numeric equivalence vs a Pine reference.

Compares a vectorbt backtest's per-bar equity (or returns) series against
a reference series exported from TradingView/Pine (or any other engine),
and prints the bar-by-bar delta plus summary divergence metrics. Use it
for the validation step when the user provided a Pine script / published
backtest to match (see references/validation.md and references/fill-timing.md).

This does NOT translate Pine — that is /strategy-translator's job. It only
checks numeric agreement between two already-produced equity curves.

Usage:
    python compare-pine-reference.py vbt_equity.csv pine_equity.csv
    python compare-pine-reference.py vbt.csv pine.csv --column equity --tol 1e-4

Each CSV must have a datetime index column (first column) and a value
column (default name: `equity`). The two series are aligned on their
shared timestamps before comparison; non-overlapping bars are reported.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd


def load_series(path: pathlib.Path, column: str) -> pd.Series:
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    if column not in frame.columns:
        # fall back to the single value column if the named one is absent
        if frame.shape[1] == 1:
            column = frame.columns[0]
        else:
            raise KeyError(
                f"{path}: column '{column}' not found; available: {list(frame.columns)}"
            )
    return frame[column].astype(float)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vbt_csv", type=pathlib.Path, help="vectorbt equity/returns CSV")
    parser.add_argument("pine_csv", type=pathlib.Path, help="Pine reference equity/returns CSV")
    parser.add_argument("--column", default="equity", help="value column name (default: equity)")
    parser.add_argument(
        "--tol",
        type=float,
        default=1e-4,
        help="relative tolerance for the pass/fail gate (default: 1e-4)",
    )
    args = parser.parse_args()

    for path in (args.vbt_csv, args.pine_csv):
        if not path.is_file():
            print(f"[fail] not a file: {path}", file=sys.stderr)
            return 2

    vbt_series = load_series(args.vbt_csv, args.column)
    pine_series = load_series(args.pine_csv, args.column)

    shared = vbt_series.index.intersection(pine_series.index)
    if len(shared) == 0:
        print("[fail] no overlapping timestamps between the two series", file=sys.stderr)
        return 3

    vbt_only = len(vbt_series.index.difference(pine_series.index))
    pine_only = len(pine_series.index.difference(vbt_series.index))
    if vbt_only or pine_only:
        print(f"[warn] non-overlapping bars: vbt-only={vbt_only}, pine-only={pine_only}")

    a = vbt_series.loc[shared]
    b = pine_series.loc[shared]
    abs_delta = (a - b).abs()
    # relative delta guards against division by zero on flat reference bars
    rel_delta = abs_delta / b.abs().clip(lower=1e-12)

    print(f"[ok] compared {len(shared)} overlapping bars on column '{args.column}'")
    print(f"     max abs delta  = {abs_delta.max():.6g}")
    print(f"     mean abs delta = {abs_delta.mean():.6g}")
    print(f"     max rel delta  = {rel_delta.max():.6g}")
    worst = abs_delta.idxmax()
    print(f"     worst bar      = {worst}  vbt={a.loc[worst]:.6g}  pine={b.loc[worst]:.6g}")

    if rel_delta.max() > args.tol:
        print(
            f"[fail] max relative delta {rel_delta.max():.3g} exceeds tol {args.tol:.3g} — "
            "check fill timing (close vs next-bar open) and fee/slippage settings"
        )
        return 10
    print(f"[ok] within tolerance (tol={args.tol:.3g})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
