# Evidence bar — monorepo-deploy

Include verbatim in every gigaprompt this skill emits. This is the hard-fail catalogue.

## A unit is GREEN only when ALL of the following are on disk

1. **Commands are reproducible.**
   - `.batch-runs/<run_id>/evidence/<unit>/cmd.sh` — the exact shell commands run, with stable absolute paths + env vars.
   - `.batch-runs/<run_id>/evidence/<unit>/stdout.txt` — captured stdout.
   - `.batch-runs/<run_id>/evidence/<unit>/stderr.txt` — captured stderr.
   - `.batch-runs/<run_id>/evidence/<unit>/exit_code.txt` — single-line integer.
   - Any of these missing = unit NOT green.

2. **Artifact SHAs are pinned.**
   - Installer: sha256 of the .pkg / .deb / .rpm / .AppImage file.
   - Docker: sha256 of the image digest (from `docker inspect`).
   - Cloud: Modal App Id, Lambda Instance Id, Ray Cluster Id (durable pointer to the deploy).
   - Record in `pkg/.proof/<target>.ready.json` + echo into evidence.

3. **Byte diffs are either empty or annotated.**
   - For file-change units: `diff -r before/ after/` captured in `evidence/<unit>/diff.txt`.
   - Non-empty diffs get a 1-line per-path reason in `evidence/<unit>/diff-reasons.md`.
   - Silent diffs = unit NOT green.

4. **Smoke tests are platform-specific and pass.**
   - Each target has its own protocol (see `pkg/scripts/smoke/<target>.sh`).
   - A universal "it built without erroring" check is insufficient — must exercise the binary/service against a real query.
   - Exit codes + stdout heads recorded in `.ready.json`.

5. **Dashboards are reached.**
   - `curl -sf http://localhost:8080/` → HTTP 200 for optuna-dashboard.
   - `curl -sf http://localhost:8501/` → HTTP 200 for vbtpro-dashboard (if shipped).
   - Capture the response header + first body line in evidence.

6. **Model triple presence.**
   - `ls -la <models_dir>/Octen-Embedding-8B.Q8_0.gguf` — file present with size > 0 AND sha256 matching the HF revision manifest.
   - Same for Qwen3-Reranker-0.6B + qmd-query-expansion-1.7B.
   - Missing model file = unit NOT green.

7. **No-compaction.**
   - If a worktree agent detects context pressure, it writes its evidence dir first, THEN halts and surfaces a checkpoint.
   - Compacting mid-unit and resuming is a hard fail.

## What this bar rejects

- "I ran it and it worked" with no captured output.
- Screenshots instead of command output.
- "The tests passed" without the test framework's stdout.
- Warnings-as-failures ignored unless the warning is a known-accepted line in `pkg/<target>/accepted-warnings.txt`.
- "The dashboard came up" without a captured HTTP 200.
- Docker "healthcheck passed" without a captured `docker inspect --format='{{.State.Health.Status}}'`.

## Stop conditions

Halt + surface if:
- 3 retries on the same unit with identical error signature.
- Evidence file captures any string matching `/(api[_-]?key|password|secret|token|Bearer \w+)/i`.
- `/compact` or `/clear` fires mid-unit.
- Two consecutive adversarial reviews flag the same high-severity finding.
- `--effort` drops below `xhigh` on any subagent.
- Shakedown cycle numbering tries to restart at 1.
- Install-from-zero fails twice on the same target.
