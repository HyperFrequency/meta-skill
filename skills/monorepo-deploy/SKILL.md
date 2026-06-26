---
name: monorepo-deploy
description: Ship a monorepo as an installable product — signed + notarized installers for mac arm64, linux x86_64, linux aarch64; docker-compose for dev + prod; and cloud deploys to Modal, Lambda Labs, and Ray clusters. Drives the work through gigaprompt evidence-bar discipline + batch-create-eval parallel worktrees + triple-gate install-from-zero proof. Emits a `.ready.json` per target and refuses to stamp READY without one. Handles dependency-hell with `uv` lockfiles + system-package audits. Wires nautilus_trader + optuna sweeps as the canonical workload. Use when the user asks to make a monorepo "actually installable", "deploy across platforms", "ship end-to-end with proof", "install package for mac/linux/cloud", "build one installer per OS", or describes a multi-target release where "done" means a working install on every target with evidence. Also triggers on "installer hell", "deploy to Modal + Lambda + Ray", "pin models + dashboards per target", "dependency hell across OSes".
---

# monorepo-deploy

Turns a monorepo into a shippable product across 3 OSes + docker + 3 cloud targets. Every target produces a `.ready.json` proof file; nothing stamps READY without one.

## When this triggers

Fire when the user asks any of:
- "ship this monorepo end-to-end with installers"
- "make a deployable package for mac + linux + cloud"
- "build installers for mac arm64, linux x86 and arm"
- "deploy to Modal / Lambda / Ray with proof"
- "fix dependency hell across OSes"
- "READY-TO-USE per target, no hand-waving"

Do NOT fire for:
- Single-platform CLI release — use `cargo-dist`/`dist init` directly.
- Library-only publish — use `uv publish` / `maturin publish` / `npm publish` directly.
- Docker-only deploy — plain `docker compose build && push`.

## What this skill is NOT

- A replacement for `gigaprompt` — call `/gigaprompt` to generate the rigorous spec; this skill is the *executor* that ships the result.
- A replacement for `batch-create-eval` — delegates parallel worktree dispatch to it.
- A one-size-fits-all installer — every target has its own smoke-test protocol. This skill enforces the contract, not the details.

## Core workflow (7 phases)

```
1. Inventory + inferred target matrix           ──┐
2. Pin APIs via docs-dual-lookup (Context7+Auggie)│  Plan
3. Scaffold pkg/ tree + Makefile                  │
4. Decompose via /batch-create-eval               │
───────────────────────────────────────────────   ──┘
5. Build each target in an isolated worktree     ──┐
6. Smoke-test per target; emit .ready.json        │  Ship
7. Aggregate; outer /loop until ALL.ready.json    │
   has every expected target green + adversarial──┘
   review returns no high-severity finding.
```

Phase 4 hands control to `batch-create-eval`, Phase 7 hands control to `loop`. This skill is the *glue* that keeps the contract consistent across them.

## Phase 1 — Inventory + inferred target matrix

Inspect the repo and produce a target matrix. Minimum fields per target:

| Target | Kind | Artifact | Signing | Smoke protocol |
|---|---|---|---|---|
| macos-arm64 | installer | `.pkg` | Developer ID Installer + notarytool | `installer -pkg … -target /tmp/stg`; `$BIN --version`; launchctl |
| linux-x86_64 | installer | `.deb` + `.rpm` + `.AppImage` | none or GPG | `apt install` / `dnf install`; `systemctl status`; healthcheck |
| linux-aarch64 | installer | `.deb` + `.rpm` + `.AppImage` | none or GPG | `arm64v8/ubuntu:22.04` smoke |
| docker | compose stack | images | none | `compose up -d`; every service healthy; dashboards reach 200 |
| cloud-modal | deploy | `modal.App` | modal token | `modal run app.py::fn` returns non-empty |
| cloud-lambda | provision | live instance | SSH key | REST provision, wait, SSH bootstrap, curl smoke |
| cloud-ray | cluster | autoscaling YAML | AWS/GCP creds | `ray up`; `ray job submit`; result read from storage |

If the user didn't specify a subset, default to the full matrix and flag that the matrix is big. Offer to drop targets they don't need.

## Phase 2 — API pinning (docs-dual-lookup)

For every third-party library that shows up in the target recipes (nautilus_trader, optuna, vectorbtpro, ray, modal, docker-compose, pkgbuild/notarytool, fpm, cargo-dist, uv, sentence-transformers, huggingface-hub, etc.), invoke `docs-dual-lookup` (Context7 + Auggie in parallel). Cite which source confirmed each API claim. Never write code that calls a signature the lookup didn't confirm.

Cache the pins into `.batch-runs/<run_id>/research/api-pins.md`. Subsequent phases consume this file and refuse to deviate without an explicit user override.

See `references/api-pin-template.md` for the schema.

## Phase 3 — Scaffold `pkg/`

Produce the standard tree:

```
pkg/
├── Makefile                     # `make all` drives every target
├── README.md                    # contract + READY-TO-USE schema
├── macos/
│   ├── README.md
│   ├── build.sh                 # codesign → pkgbuild → productbuild → notarytool → stapler
│   ├── resources/distribution.xml
│   └── scripts/{preinstall,postinstall}
├── linux-x86_64/
│   ├── README.md
│   ├── build.sh                 # fpm -s dir -t deb/rpm -a amd64
│   ├── scripts/{postinstall.sh,preremove.sh}
│   └── systemd/<service>.service
├── linux-aarch64/               # mirror of x86_64 with -a aarch64
├── docker/
│   ├── compose.yaml             # Compose v2 with dev/prod profiles
│   ├── Dockerfile.<service>
│   └── build.sh
├── cloud/
│   ├── modal/app.py + deploy.sh
│   ├── lambda/{client.py,bootstrap.sh,deploy.sh,terraform/}
│   └── ray/{cluster.yaml,job.py,deploy.sh}
├── scripts/
│   ├── aggregate_proof.py       # reads .proof/*.ready.json → ALL.ready.json
│   ├── smoke/<target>.sh        # per-target smoke protocol
│   └── model-preflight.sh       # `huggingface-cli download` the model triple
└── .proof/                      # gitignored; produced at build time
    ├── <target>.ready.json      # one per target
    └── ALL.ready.json           # aggregated
```

`pkg/README.md` contains the `.ready.json` schema — every target MUST emit a file matching it.

## Phase 4 — Decompose + dispatch via `batch-create-eval`

Invoke `/batch-create-eval` with the target matrix as its unit list. Each unit:

- Name: `pkg-<target>-build+smoke` (e.g. `pkg-macos-arm64-build+smoke`).
- Claims a worktree under `.worktrees/<run_id>-<unit>/`.
- Executes the target's `build.sh`, captures stdout/stderr/exit-code.
- Runs the target's smoke protocol; captures.
- Writes `pkg/.proof/<target>.ready.json`.
- Writes the evidence dir under `.batch-runs/<run_id>/evidence/<unit>/`.

Dependencies:
- `model-triple-preflight` unit runs before any target build that needs models present.
- `docker` depends on `model-triple-preflight`.
- Cloud deploys depend on `model-triple-preflight` + cloud-creds probe.

## Phase 5 — Build per target

Each worktree agent obeys:

1. `--effort max` (fallback `xhigh`; hard halt if below).
2. No `/compact` mid-run.
3. Evidence directory is the only "done" signal.
4. If `build.sh` fails 3× with the same error signature, HALT and surface.
5. `docs-dual-lookup` is authoritative; never invent an API signature.

## Phase 6 — Smoke per target

Every smoke script writes a `.ready.json` of the form:

```json
{
  "target": "<target-id>",
  "version": "<git describe>",
  "artifact": "<relative path to the produced artifact>",
  "sha256": "<sha256 of the artifact>",
  "smoke_tests": [
    {"name": "<test_name>", "exit_code": 0, "stdout_head": "<first 200 chars>"}
  ],
  "models_present": ["<file>", ...],
  "dashboards_reachable": {
    "optuna-dashboard": "<url returning 200>",
    "vbtpro-dashboard": "<url returning 200>"
  },
  "timestamp": "<ISO8601 UTC>"
}
```

If any field is missing, the smoke is FAIL. The aggregator will refuse to write `ALL.ready.json`.

## Phase 7 — Aggregate + outer /loop

`pkg/scripts/aggregate_proof.py` reads every `pkg/.proof/*.ready.json`, validates the schema, and writes `pkg/.proof/ALL.ready.json` only if:
- Every expected target is present.
- Every `smoke_tests[*].exit_code == 0`.
- Every `dashboards_reachable.*` URL is present.

Then invoke `/loop` with the shakedown cycle. Two consecutive zero-error cycles + a clean `/codex:adversarial-review --effort max` = complete.

## Dependency-hell policy

- One Python runtime per target. `uv`-managed venv. `uv.lock` cross-platform TOML.
- System deps audited into `pkg/<target>/system-deps.txt` (brew for mac; apt/yum for linux).
- Cargo workspace at the monorepo root if any Rust crates ship; `dist init` generates release.yml.
- Node? Don't. If you must: pin via `pnpm` + `pnpm-lock.yaml`.
- Never call `pip install` in post-install hooks; pre-install everything into the artifact.

## Model + dashboard contract (HyperFrequency-specific defaults)

If the repo contains `skills/neuro-link-setup/scripts/download_models.sh`, the skill treats it as the authoritative model triple. Otherwise the user must provide one.

Model triple (canonical):
1. Embedder — `mradermacher/Octen-Embedding-8B-GGUF` → `Octen-Embedding-8B.Q8_0.gguf` in `$NLR_ROOT/models/`.
2. Reranker — `ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF` → `qwen3-reranker-0.6b-q8_0.gguf` in `~/.cache/qmd/models/`.
3. Query expansion — `tobil/qmd-query-expansion-1.7B-gguf` → `qmd-query-expansion-1.7B-q4_k_m.gguf` in `~/.cache/qmd/models/`.

Dashboards reached during smoke:
1. `optuna-dashboard` on :8080.
2. vectorbtpro dashboard on :8501 — no first-party dashboard exists; scaffold a Plotly Dash app over `vbt.Portfolio` if the monorepo doesn't ship one.

## Evidence bar (verbatim in every emitted gigaprompt)

Include `references/evidence-bar.md` verbatim. Summary: byte-level, reproducible commands, SHA pins, real smoke per target, no "it should work".

## Anti-patterns

- Shipping a .pkg signed with Developer ID **Application** (wrong cert; installers need Developer ID **Installer**).
- Using `modal.Stub` — it was removed in Modal 1.0; raises AttributeError.
- Using `ray.tune.run(...)` instead of `ray.tune.Tuner` (deprecated).
- `fpm -a arm64` for rpm — wrong; rpm uses `aarch64`. Use `-a aarch64` for both deb/rpm; fpm normalizes.
- Hand-editing systemd units into `/lib/systemd/system/` via `-C` — use `--deb-systemd`/`--rpm-systemd` flags so fpm generates the correct postinst hooks.
- Deploying to Lambda Labs expecting a Python SDK — there isn't one; use the REST API.
- Optuna Ray integration via `optuna.integration.*` — that module split off; use `ray.tune.search.optuna.OptunaSearch` from the Ray side.

## References

- `references/evidence-bar.md` — the hard-fail catalogue (emit verbatim).
- `references/api-pin-template.md` — schema for the pinned-API file.
- `references/ready-json-schema.md` — the `.ready.json` contract.
- `references/gigaprompt-handoff.md` — how this skill composes with `/gigaprompt --rescue` / `--lateral-pass`.

## Scripts

- `scripts/build-all.sh` — top-level `make all` wrapper with banner + timing.
- `scripts/smoke/<target>.sh` — per-target smoke.
- `scripts/aggregate_proof.py` — `.ready.json` → `ALL.ready.json`.
