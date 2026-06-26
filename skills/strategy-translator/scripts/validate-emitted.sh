#!/usr/bin/env bash
# validate-emitted.sh — runs per-target validation on a translation output.
#
# Dispatches based on file extension:
#   *.pine       → pine-validate CLI (TradingView-compatible compiler check)
#   *.py         → python -c "import sys; compile(open(sys.argv[1]).read(), '<f>', 'exec')"
#                  + ast check for common pitfall patterns
#   *.cpp,*.cc   → g++ -fsyntax-only
#   *.rs         → rustc --crate-type=bin --emit=metadata (needs Cargo.toml)
#
# Exits 0 if all checks pass, non-zero on first failure. Intended to be
# invoked at the END of the translate workflow before returning the
# translation to the user.

set -euo pipefail

FILE="${1:?usage: validate-emitted.sh <path-to-translation>}"
[ -f "$FILE" ] || { echo "[fail] not a file: $FILE"; exit 2; }

EXT="${FILE##*.}"

case "$EXT" in
  pine)
    if command -v pine-validate >/dev/null 2>&1; then
      pine-validate "$FILE"
    else
      PINE_LSP_ROOT="${PINELSP_INSTALL_DIR:-$HOME/.local/share/neuro-link/pinelsp}"
      NODE_BIN="$PINE_LSP_ROOT/dist/packages/cli/src/cli.js"
      if [ -f "$NODE_BIN" ]; then
        node "$NODE_BIN" "$FILE"
      else
        echo "[warn] pine-validate not on PATH and cli.js not at $NODE_BIN — skipping"
        exit 0
      fi
    fi
    ;;
  py)
    python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read()); print('[ok] python parses')" "$FILE"
    # Lightweight pattern checks
    if grep -q 'ewm(' "$FILE" && ! grep -q 'adjust=False' "$FILE"; then
      echo "[warn] .ewm() without adjust=False — likely diverges from Pine ta.ema"
    fi
    if grep -q "rolling.*std" "$FILE" && ! grep -q 'ddof=0' "$FILE"; then
      echo "[warn] .rolling().std() without ddof=0 — likely diverges from Pine ta.stdev"
    fi
    if grep -qE 'size\s*=\s*np\.inf' "$FILE"; then
      echo "[warn] size=np.inf — prefer size=1.0 with size_type='percent'"
    fi
    ;;
  cpp|cc|cxx)
    if command -v g++ >/dev/null 2>&1; then
      g++ -fsyntax-only -std=c++17 "$FILE"
      echo "[ok] C++ syntax check"
    else
      echo "[warn] g++ not available — skipping C++ syntax check"
    fi
    ;;
  rs)
    echo "[info] Rust syntax check requires a Cargo project; skipping standalone file check"
    ;;
  *)
    echo "[warn] no validator for extension .$EXT — skipping"
    ;;
esac
