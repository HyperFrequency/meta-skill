#!/usr/bin/env bash
# uv_workspaces.sh — ship a multi-member workspace. See references/shipping.md.
# Stub: real implementation per references/shipping.md#uv-workspaces.
set -euo pipefail
OUT_DIR="${OUT_DIR:-dist}"
mkdir -p "$OUT_DIR"
uv lock --check
uv build --out-dir "$OUT_DIR" --all-packages "$@"
echo "shipping/uv_workspaces.sh: built $(ls "$OUT_DIR"/*.whl 2>/dev/null | wc -l) wheel(s) into $OUT_DIR"
