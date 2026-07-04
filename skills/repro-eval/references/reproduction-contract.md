# The reproduction contract

An experiment is **reproducible** iff its logged record resolves to a complete,
pinned provenance set AND re-executing under that set lands within a declared
tolerance. This file defines the completeness checklist and how each artifact
reference is resolved. If any item is missing or a reference dangles, the
experiment fails as `unresolvable` **before** re-execution is attempted.

## Completeness checklist

Every field below must be present and non-null on the `experiment-tracker`
record. This is the class-8 criteria schema — "completeness checklist (config,
prompt versions, scorer versions, costs, traces all resolvable)".

| Field | What it pins | Resolution source |
|---|---|---|
| `config_snapshot_hash` | the exact functions/variants/metrics/evals config the run used | `flywheel-config` → `ConfigSnapshot` (see below) |
| `dataset_version` | the exact datapoints + splits scored | `experiment-tracker` dataset registry (versioned, diff/restore) |
| `seeds` | RNG seeds for sampler, dataset shuffle, any stochastic solver | recorded per-run; one seed per stochastic source, not one global seed |
| `variant` / `prompt_version` | the prompt template + schema that was the unit under test | `experiment-tracker` prompt registry (sequential versions / label) |
| `scorer_id + scorer_version` | the exact scorer code/rubric that produced each score | `harness_eval` scorer registry (immutable versions) |
| `score_config_id + score_config_version` | judge model, thresholds, choice-scores | `harness_eval` `ScoreConfig` registry |
| `provider_sampling_params` | temperature, top_p, max_tokens, provider seed per model call | recorded on each `ModelInference` row |
| `costs` | recorded per-inference cost + usage (tokens) | `llm-router` cost tracking → surfaced in `experiment-tracker` |
| `trace_ids` | OTel trace(s) + `.traj` trajectory artifact for the run | `trace-store`; trajectory in the contract plane |
| `kbi_metadata` | K/B/I epistemic tags (Known / Believed / Inferred) + QualityFlags | episteme-style sample metadata on the eval record |

A record that is missing any row is **not** re-executable. Report exactly which
rows are absent — do not silently substitute defaults (an unrecorded temperature
is a provenance defect, not "temperature = 0").

## The config-snapshot hash — content-addressed identity

The single most important provenance field. A `ConfigSnapshot` carries a
**structural** `SnapshotHash` (tensorzero `config/snapshot/`, Apache-2.0 —
referenced, not copied) computed from the config's *logical content*, not its
serialized text:

- Walk the `serde_json::Value` form of the config with a self-describing
  canonical encoding.
- 1-byte **type tag** per node (null/bool/number/string/array/object).
- 8-byte big-endian **length prefix** on strings/arrays/objects — prevents
  collisions like `["ab"]` ↔ `["a","b"]` and `{"a":"b"}` ↔ `{"ab":""}`.
- **Sorted object keys** (canonical order).
- **f64 IEEE-754 big-endian bit pattern** for numbers — stable even when the
  same value round-trips through different textual forms (`0.7` vs `0.6999…`).

Why structural rather than TOML-bytes hashing matters for reproduction:

- **Round-trip identity.** Preserved by every `StoredConfig → JSON → StoredConfig`
  and `→ TOML →` round-trip, so re-deriving the hash from the stored config must
  match the stored hash — that equality *is* step 2's verification.
- **Independence from formatting.** Immune to TOML-crate version bumps and float
  reformatting, so the same logical config on two harness versions resolves to
  the **same** snapshot row and hash. A text hash would drift and make an
  unchanged config look like a different experiment.
- **Cross-machine / cross-restart stability.** Same config ⇒ same hash on any
  architecture or process — required for a re-execution on a different worker to
  claim identity with the original.

Resolution: `config_snapshot_hash` → look up the `config_snapshots` row →
rehydrate `StoredConfig` from stored `config_jsonb` → re-derive the structural
hash → assert equality with the logged hash. Mismatch = corrupted/tampered
snapshot = `unresolvable`.

## Artifact-reference resolution

Every reference on the record must resolve to a live, content-identical artifact:

- **Dataset version** → the versioned datapoint set. Reject if the version was
  mutated in place (versions are immutable; a diff/restore lineage must exist).
- **Prompt/variant version** → exact template text + input/output schema. A label
  (e.g. `prod`) is NOT a version — resolve the label to the concrete version the
  run pinned, or fail (labels move; runs pin).
- **Scorer + score_config versions** → the immutable registry entries. A scorer
  whose version was hand-edited without a bump is `unresolvable`.
- **Trace ids** → spans present in `trace-store`; the `.traj` trajectory blob
  present in the contract plane (CAS). A retention-expired trace that the record
  still claims is a hard fail (record over-promised its own resolvability).
- **CAS blobs** → resolve `BlobRef`s; a dangling blob is `unresolvable`.

## K/B/I metadata — what the record is allowed to claim

K/B/I tags (episteme, Apache-2.0 — pattern referenced) mark, per result
component, whether it is **Known** (deterministically re-derivable), **Believed**
(reproducible only within a statistical band), or **Inferred** (a downstream
computation). The reproduction gate reads these to pick the right tolerance: a
`Known` component must match exactly; a `Believed` component is held to the
variance band. A record that tags a stochastic judge score as `Known` is itself
a completeness defect — the tag must match the true determinism class from
`references/determinism-sources.md`.

## Failure outputs

- Missing checklist row → `unresolvable` (report the row).
- Reference does not resolve → `unresolvable` (report the reference + why).
- Snapshot hash mismatch on re-derivation → `unresolvable` (corrupted snapshot).
- All present and resolving → proceed to `references/re-execution-runner.md`.
