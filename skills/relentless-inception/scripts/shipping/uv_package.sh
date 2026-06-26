#!/usr/bin/env bash
# uv_package.sh — ship a single uv-built wheel. See references/shipping.md.
# Stub: real implementation per references/shipping.md#uv-install-package.
set -euo pipefail
OUT_DIR="${OUT_DIR:-dist}"
mkdir -p "$OUT_DIR"
uv build --out-dir "$OUT_DIR" "$@"
pip install --dry-run "$OUT_DIR"/*.whl >/dev/null
twine check "$OUT_DIR"/*.whl
cat > "$OUT_DIR/ship-report.json" <<JSON
{"ship_type":"uv-package","artifacts":[$(ls "$OUT_DIR"/*.whl 2>/dev/null | awk '{printf "{\"path\":\"%s\"},", $0}' | sed 's/,$//')],"timestamp":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
JSON
echo "ship-report: $OUT_DIR/ship-report.json"
