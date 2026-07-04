# The D11 `harness_skills` crate contract

How the six behavioral subsystems land as the first-party `harness_skills`
(skill-manager) crate under `centrifuge-/rust/harness/crates/`, what parity means,
and the licensing fences. This is the authoritative § a.7 map, restated as a build
contract. Clean-room throughout.

## Trait seams (the ports that decouple donor externals)

The donor shells out to external binaries (`cass`, `bv`, `bd`, `cm`, `ubs`); the
first-party crate **replaces every one with a trait**, so nothing external is a
required dependency:

| Trait | Replaces | Backed by |
|---|---|---|
| `SessionSource` | the `cass` binary (session mining input) | harness OTel spans + LLM logs (`trace-store`), `.traj` artifacts, Claude Code session logs, lightspeed/forgecode event logs |
| `GraphAnalyzer` | `bv` graph binary | petgraph / the first-party `harness_graph` engine |
| `Embedder` | — | `HashEmbedder` (FNV-1a 384-dim) default; ONNX-local honest `NotImplemented` |
| `SkillRepository` | direct FS access | vaultfile / Postgres / BM25 backends (`harness_store`) |
| `AntiPatternDetector` | — | `DefaultDetector` + custom detectors |

`cm` / `ubs` become **optional features**, never required deps.

## Storage & indexing

Dual persistence: **SQLite** (schema migrations 001–013 on rusqlite/sqlx with
**real FTS5**) with an optional git-archive feature, plus a content-hash
incremental index pipeline. In neuro-centrifuge the Store plane
(`harness_store`) provides the backends; the crate keeps the migration set and
the FTS5 semantics as the parity contract (the donor's built-but-bypassed tantivy
index is *not* the parity target — pick FTS5 or a wired tantivy and pin it).

## YAML skill-test framework (feeds skill-eval-runner & D13 class 1)

A `TestDefinition` (YAML) drives executable skill tests:

- `name` (required), `description`, `skill_id` (required), optional `setup`,
  required `steps`, optional `cleanup` (runs even on failure), `timeout`, `tags`,
  skip conditions, and system `requirements`.
- `TestStep` is an untagged enum: **`load_skill`** (at a disclosure level),
  **`run`** (a shell command), **`assert`** (conditions), plus a **SafetyGate**.
- The runner executes setup → steps → cleanup and rolls assertion results up to a
  pass/fail — the executable eval-criteria engine for D13 **class 1** (skill
  frontier rubric), consumed by the sibling **skill-eval-runner** skill.

Quality scoring (`quality` module) produces a weighted breakdown across
**structure / content / evidence / usage / toolchain / freshness** — the numeric
skill-health signal that complements the rubric verdict.

## Security gate (reconcile, don't stack)

The donor's security stack — **ACIP** injection quarantine + secret scanner on
the log-ingest path, and **DCG** command tiers — must be **reconciled with the
Macro tool-plane guards into one gate, not two**. The scrub (secret scan + ACIP +
anonymizer) runs on any session **before** it enters the store or an LLM synthesis
step (see anti-pattern mining). Untrusted content is `taint`-labeled and forces
review. The simulation sandbox (tempdir + blocklist) is a **policy-level cheap
pre-gate, explicitly NOT a security boundary** — document it as such.

## MCP surface

The donor exposes an MCP server (**12 tools**). The first-party crate
**reimplements it on `rmcp`** so it plugs into the D4 front gateway as a tool
provider — it is *not* a third MCP gateway (that decision is locked elsewhere;
the crate is a tool source behind the one gateway).

## Phase split (P1 vs P2)

**P1 (D6 exit path):** spec-lens + core types, Base<Org<Project<User layering +
content-hash index, progressive disclosure, micro-slicing + constrained packing +
pack contracts, hash embeddings + hybrid search + RRF, anti-pattern data model +
mining pipeline (behind `SessionSource`), the trajectory composite (phase
segmentation + quality gate), YAML skill tests, quality scoring, recursive
composition + meta-skills, the suggestion bandit, dual persistence with FTS5, the
reconciled security gate, the rmcp MCP surface, lint/validate/fmt, and the parity
corpus.

**P2:** Brenner guided mining + `UncertaintyQueue` active learning (3–7 targeted
queries when confidence is low), dedup/diff at scale, and bundles/sync/
cross-project/backup/cloud-auth (reference-only).

## Parity corpus (D2)

Parity is **behavioral**, asserted by tests, never by shared code. The donor's
corpus is 29 e2e suites + property tests + insta snapshots. **Exact-match parity
targets:**

- **spec-lens round-trip** (`parse(compile(spec)) ≡ spec`) — test #1;
- **slugify** (H1 → id);
- **hash-embedding vectors** (FNV-1a, 384-dim, deterministic);
- **RRF ordering** (k=60 fusion result order).

Numeric-behavior parity targets (assert values, re-derive logic): confidence
`min(n/(n+2), 0.9) + diversity_bonus`; quality gate `min_score 0.3` with the
default weight/penalty table; disclosure budgets `100/500/1500`; dedup
`0.7/0.3` weights at threshold `0.85`; bandit UCB
`sqrt(ln(total)/obs)·0.1`; inheritance depth `5`.

## Licensing fences (§ f-adjacent)

- **meta_skill** is **MIT + an OpenAI/Anthropic rider** → clean-room *behavioral*
  reimplementation only; **no copied code**; carry `NOTICE.md`. This entire skill
  is written to that fence.
- Freeze donor algorithms (chars/4 token estimate, H1-slug) for v1 behind
  `format_version` so parity is stable.
- Sibling fences when porting *other* skill content into first-party crates:
  gitnexus\* = PolyForm-NC, copula-dependency = BUSL-1.1, pdf/pptx/docx =
  Anthropic-proprietary, openobserve = AGPL — exclude or re-derive.
  tensorzero / episteme / dspy-rs / lightspeed are Apache-2.0/MIT (safe to
  reference).

## Library facts (engine ≠ library)

The engine operates over the canonical library at
`/Users/DanBot/hyperfrequency/neuro-quant-agent-skills` branch
`heal/frontier-rubric` (**378** leaf `SKILL.md`; the HyperFrequency-local path is
a stale ~170-skill main checkout; `CATALOG.md` lags — refresh counts). These are
*library state*, not engine behavior — this skill documents the engine; library
governance is **meta-skill**'s job.

## Cross-links to the D12/D13 fabric

- **Loop-3** (trajectory & anti-pattern analysis) — consumes the trajectory
  composite + anti-pattern mining; confirmed rules → the versioned anti-pattern
  registry this crate owns. See sibling skills **trajectory-miner**,
  **hitl-interview**.
- **Loop-4** (autonomous skill eval & evolution) — DETECT uses bandit outcomes +
  anti-pattern hits; EVAL uses the YAML skill tests + quality scoring; GATE is
  the Voyager commit gate. See **skill-eval-runner** for the class-1 rubric gate.
- **D13 classes 1/3/7** — class 1 uses the skill-test framework + quality
  scoring; classes 3/7 use the trajectory composite as a cheap pre-judge filter.
