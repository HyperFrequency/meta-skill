#!/usr/bin/env python3
"""Generate a strategy tear sheet.

Performance section is rendered by the `quantstats-rs` Rust engine; the optional
MAE / leverage section is computed by this skill's local `tearsheet_helpers.py`.
This replaces the retired Python-QuantStats / external `StrategyComparisonTearsheet`
path.

Two input modes:
  --returns RETURNS.csv      Two columns `date,return` (YYYY-MM-DD, decimal fraction
                             where 0.01 == +1%). Passed straight to quantstats-rs.
  --trades  TRADES.csv  --capital N
                             A trades CSV. A *daily* returns series is derived by
                             summing each day's net PnL and dividing by `--capital`
                             (a deliberately simple, documented approximation — for
                             exact period returns, supply --returns directly).

The quantstats-rs binary is located on PATH; if absent, falls back to
`cargo run --manifest-path <crate>/Cargo.toml --bin quantstats-rs`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CRATE_DIR = Path(os.path.expanduser("~/neuro-centrifuge-repos/quantstats-rs"))

# Make the local helper importable regardless of the working directory.
sys.path.insert(0, str(SKILL_DIR))


def quantstats_rs_command() -> list[str]:
    """Return the argv prefix that runs the quantstats-rs CLI."""
    on_path = shutil.which("quantstats-rs")
    if on_path:
        return [on_path]
    manifest = CRATE_DIR / "Cargo.toml"
    if manifest.is_file():
        return [
            "cargo", "run", "--quiet",
            "--manifest-path", str(manifest),
            "--bin", "quantstats-rs", "--",
        ]
    sys.exit(
        "error: `quantstats-rs` not found on PATH and the crate is not at "
        f"{CRATE_DIR}. Build it with `cargo install --path {CRATE_DIR}`."
    )


# --- column detection (trades CSVs vary; accept common aliases) ----------------
_DATE_KEYS = ("exit_time", "exit_date", "exit", "close_time", "date", "timestamp")
_PNL_KEYS = ("pnl", "pnl_abs", "profit", "net_pnl", "realized_pnl")
_MAE_KEYS = ("max_adverse_excursion", "mae", "mae_pct")
_RET_KEYS = ("return_pct", "return", "ret_pct", "pnl_pct")


def _first_present(row: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return k
    return None


def read_trades(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"error: {path} has no trade rows")
    return rows


def trades_to_returns_csv(trades: list[dict], capital: float) -> str:
    """Derive a date,return series from trades and write it to a temp CSV."""
    date_key = _first_present(trades[0], _DATE_KEYS)
    pnl_key = _first_present(trades[0], _PNL_KEYS)
    if not date_key or not pnl_key:
        sys.exit(
            "error: could not find an exit-date column "
            f"({_DATE_KEYS}) and a PnL column ({_PNL_KEYS}) in the trades CSV. "
            "Supply --returns instead for exact period returns."
        )
    daily_pnl: dict[str, float] = defaultdict(float)
    for t in trades:
        day = str(t[date_key])[:10]  # YYYY-MM-DD prefix of any ISO timestamp
        try:
            daily_pnl[day] += float(t[pnl_key])
        except (TypeError, ValueError):
            continue
    if not daily_pnl:
        sys.exit("error: no parseable PnL in trades CSV")

    fd, tmp = tempfile.mkstemp(prefix="qsr_returns_", suffix=".csv")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["date", "return"])
        for day in sorted(daily_pnl):
            w.writerow([day, f"{daily_pnl[day] / capital:.8f}"])
    return tmp


def render_mae(trades: list[dict], out_path: str) -> str:
    """Run the local MAE/leverage helper and write a JSON report."""
    import tearsheet_helpers as h  # local, numpy/scipy only

    # CSV values arrive as strings; the helper does numeric comparisons, so
    # coerce the fields it reads (under canonical OR alias names) to float.
    norm: list[dict] = []
    for t in trades:
        item = dict(t)
        mk = _first_present(t, _MAE_KEYS)
        rk = _first_present(t, _RET_KEYS)
        if mk is not None:
            try:
                item["max_adverse_excursion"] = float(t[mk])
            except (TypeError, ValueError):
                item["max_adverse_excursion"] = None
        if rk is not None:
            try:
                item["return_pct"] = float(t[rk])
            except (TypeError, ValueError):
                item["return_pct"] = 0.0
        norm.append(item)

    report = h.generate_mae_analysis_report(norm)
    mae_path = out_path.rsplit(".", 1)[0] + "_mae.json"
    with open(mae_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    return mae_path


def main() -> int:
    p = argparse.ArgumentParser(description="Generate a strategy tear sheet (quantstats-rs + MAE).")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--returns", help="returns CSV: date,return")
    src.add_argument("--trades", help="trades CSV (requires --capital)")
    p.add_argument("--capital", type=float, help="starting capital, for --trades")
    p.add_argument("--benchmark", help="benchmark returns CSV (date,return)")
    p.add_argument("-o", "--output", default="tearsheet.html", help="output HTML path")
    p.add_argument("--strategy-title", default="Strategy")
    p.add_argument("--benchmark-title")
    p.add_argument("--rf", type=float, default=0.0, help="annual risk-free rate (fraction)")
    p.add_argument("--periods", type=int, default=252, help="periods per year")
    p.add_argument("--mae", action="store_true", help="also emit the MAE/leverage JSON report")
    args = p.parse_args()

    trades: list[dict] | None = None
    if args.trades:
        if args.capital is None:
            p.error("--trades requires --capital")
        trades = read_trades(args.trades)
        returns_csv = trades_to_returns_csv(trades, args.capital)
        cleanup_returns = True
    else:
        returns_csv = args.returns
        cleanup_returns = False

    cmd = quantstats_rs_command() + [
        "report", "--returns", returns_csv,
        "--output", args.output,
        "--strategy-title", args.strategy_title,
        "--rf", str(args.rf), "--periods", str(args.periods),
    ]
    if args.benchmark:
        cmd += ["--benchmark", args.benchmark]
        if args.benchmark_title:
            cmd += ["--benchmark-title", args.benchmark_title]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        if cleanup_returns:
            try:
                os.unlink(returns_csv)
            except OSError:
                pass

    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        return result.returncode
    print(result.stdout.strip())

    if args.mae:
        if trades is None:
            sys.stderr.write("warning: --mae needs --trades; skipping MAE report\n")
        else:
            print(f"wrote {render_mae(trades, args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
