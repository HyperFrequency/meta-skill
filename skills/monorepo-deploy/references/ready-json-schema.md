# .ready.json — the READY-TO-USE contract

Every target the `monorepo-deploy` skill drives MUST emit a file at `pkg/.proof/<target>.ready.json` matching this schema. Absence = NOT READY. Schema mismatch = FAIL.

## Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["target", "version", "artifact", "sha256", "smoke_tests", "models_present", "dashboards_reachable", "timestamp"],
  "properties": {
    "target": {
      "type": "string",
      "enum": ["macos-arm64", "linux-x86_64", "linux-aarch64", "docker", "cloud-modal", "cloud-lambda", "cloud-ray"]
    },
    "version": {
      "type": "string",
      "description": "output of `git describe --tags --always --dirty`"
    },
    "artifact": {
      "type": "string",
      "description": "relative path from pkg/ root to the emitted artifact (e.g. dist/neuro-link-0.1.0-arm64.pkg)"
    },
    "sha256": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "sha256 of the artifact file for installers; of the running container image for docker; of the deployed app id for cloud"
    },
    "smoke_tests": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["name", "exit_code", "stdout_head"],
        "properties": {
          "name": {"type": "string"},
          "exit_code": {"type": "integer"},
          "stdout_head": {"type": "string", "maxLength": 500},
          "stderr_head": {"type": "string", "maxLength": 500}
        }
      }
    },
    "models_present": {
      "type": "array",
      "minItems": 3,
      "items": {"type": "string"},
      "description": "filenames (not paths) of the model triple. Minimum 3: embedder, reranker, query-expansion"
    },
    "dashboards_reachable": {
      "type": "object",
      "required": ["optuna-dashboard"],
      "properties": {
        "optuna-dashboard": {"type": "string", "format": "uri"},
        "vbtpro-dashboard": {"type": ["string", "null"], "format": "uri"}
      }
    },
    "timestamp": {"type": "string", "format": "date-time"},
    "notes": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

## Example — macos-arm64

```json
{
  "target": "macos-arm64",
  "version": "0.1.0-12-ga8f3c9d",
  "artifact": "dist/neuro-link-0.1.0-arm64.pkg",
  "sha256": "a7f23e9c4b8d1f0e...",
  "smoke_tests": [
    {"name": "installer_dry_run", "exit_code": 0, "stdout_head": "installer: Package name is neuro-link\ninstaller: Installing at base path /tmp/staging"},
    {"name": "cli_version", "exit_code": 0, "stdout_head": "neuro-link 0.1.0 (a8f3c9d)"},
    {"name": "launchd_loaded", "exit_code": 0, "stdout_head": "PID\tStatus\tLabel\n42817\t0\tcom.hyperfrequency.neuro-link"},
    {"name": "spctl_accept", "exit_code": 0, "stdout_head": "dist/neuro-link-0.1.0-arm64.pkg: accepted"}
  ],
  "models_present": [
    "Octen-Embedding-8B.Q8_0.gguf",
    "qwen3-reranker-0.6b-q8_0.gguf",
    "qmd-query-expansion-1.7B-q4_k_m.gguf"
  ],
  "dashboards_reachable": {
    "optuna-dashboard": "http://localhost:8080/",
    "vbtpro-dashboard": "http://localhost:8501/"
  },
  "timestamp": "2026-04-22T18:30:00Z",
  "notes": [
    "Notarytool submission id: 2e42f3-5a1b...",
    "Stapler staple succeeded"
  ]
}
```

## ALL.ready.json — aggregated

Written by `pkg/scripts/aggregate_proof.py`. Schema:

```json
{
  "run_id": "20260422-hf-nq-deployable-a7c3",
  "version": "0.1.0-12-ga8f3c9d",
  "targets_green": ["macos-arm64", "linux-x86_64", ...],
  "targets_missing": [],
  "targets_failed": [],
  "dashboards_all_green": true,
  "models_all_green": true,
  "timestamp": "<ISO8601>"
}
```

The skill + `/loop` termination condition:

- `targets_missing` empty AND `targets_failed` empty AND `dashboards_all_green == true` AND `models_all_green == true`.
- PLUS two consecutive shakedown cycles with zero error fingerprints.
- PLUS `/codex:adversarial-review --effort max` introducing no new high-severity finding.
