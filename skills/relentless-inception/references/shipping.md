# Shipping

`/relentless-inception` ships its deliverable when the plan declares one. Three ladders, picked by the planner based on the deliverable type:

1. `uv install package` — single wheel or sdist, optionally signed, optionally uploaded.
2. `uv workspaces` — coordinated multi-member workspace release.
3. `Una + Dagger` — multi-arch builds + cloud deploy via Dagger pipelines.

All three are idempotent and write a structured `ship-report.json` consumed by the tearsheet generator.

---

## uv install package

Use when the deliverable is a single Python package.

Script: `scripts/shipping/uv_package.sh`

What it does:

```
1. uv build  (produces wheel + sdist in dist/)
2. Optionally sign the wheel (if SIGNING_KEY_PATH is set)
3. Validate the wheel: pip install --dry-run dist/<wheel>
4. Validate metadata: twine check dist/*
5. If --upload, twine upload to <index-url>  (defaults to PyPI)
6. Emit ship-report.json
```

ship-report.json schema:

```json
{
  "ship_type": "uv-package",
  "package_name": "...",
  "version": "...",
  "artifacts": [{"path": "...", "sha256": "...", "size_bytes": N}],
  "signed": true|false,
  "uploaded_to": "..." | null,
  "validation": {"pip_dry_run": "ok", "twine_check": "ok"},
  "timestamp": "..."
}
```

---

## uv workspaces

Use when the deliverable is a monorepo with multiple workspace members that need a coordinated version bump.

Script: `scripts/shipping/uv_workspaces.sh`

What it does:

```
1. Read root pyproject.toml [tool.uv.workspace].members
2. For each member, bump version per --bump=(major|minor|patch) or explicit version
3. uv lock  (regenerate workspace lockfile)
4. For each member, uv build  (per-member wheel)
5. Optionally sign each wheel
6. Validate every wheel
7. Tag the repo: v<root-version>
8. If --upload, upload all wheels
9. Emit ship-report.json (per-member rows)
```

ship-report.json adds a `members` array:

```json
{
  "ship_type": "uv-workspaces",
  "root_version": "...",
  "members": [
    {"name": "...", "version": "...", "artifacts": [...], "signed": ..., "uploaded_to": ...}
  ],
  "tag": "v...",
  ...
}
```

---

## Una + Dagger

Use when the deliverable needs multi-arch builds (mac-arm + linux-arm + linux-x86) or cloud deploy.

Script: `scripts/shipping/dagger_deploy.sh`

What it does:

```
1. Verify Dagger CLI is installed and dagger.json is at <repo>/dagger/dagger.json
2. dagger -m ./dagger call bootstrap --source=.     (init submodules, uv sync)
3. dagger -m ./dagger call test --source=.          (full test suite in container)
4. For each target arch in {linux/amd64, linux/arm64, darwin/arm64}:
      dagger -m ./dagger call build-image --source=. --target=runtime
      docker save ... -> dist/neuro-harness-<arch>.tar
5. If --deploy=cloud-run:
      gcloud run deploy ...
6. If --deploy=modal:
      modal deploy ...
7. If --deploy=lambda-labs:
      ssh ... and docker compose up -d
8. Emit ship-report.json
```

ship-report.json:

```json
{
  "ship_type": "dagger",
  "dagger_engine_version": "...",
  "build_matrix": [
    {"arch": "...", "artifact": "...", "sha256": "...", "size_bytes": N}
  ],
  "tests": {"passed": N, "failed": N, "duration_seconds": N},
  "deploys": [
    {"target": "cloud-run", "service_url": "...", "revision_id": "..."},
    {"target": "modal", "app_name": "...", "version_hash": "..."}
  ],
  "timestamp": "..."
}
```

---

## When to ship vs not

The planner decides whether a run ships at all. A few rules:

- Adversarial-review must approve at the phase gate before any `ship_*.sh` script runs.
- If the simulated-user harness has any error reports, no ship.
- If the budget soft cap is hit during shipping, the partial ship-report is saved and the run pauses.

The kill switch immediately aborts an in-flight ship, but does not roll back already-uploaded artifacts (impossible to do generically).

---

## Reading a ship-report

Tearsheet generator reads `ship-report.json` and renders:

- Artifact table with sha256, size, sign status
- Validation results (pip dry-run, twine check)
- For Dagger: per-arch build status with timing
- Deploy URLs / revision IDs as clickable links (in the HTML tearsheet)

Manual inspection from CLI:

```bash
jq '.' ship-report.json
```
