# Search, recursion, dedup & the spec lens (behavioral spec)

Four tightly-related engine behaviors: deterministic embeddings, hybrid retrieval,
recursive composition, near-duplicate detection — plus the spec lens that
underpins them all. Clean-room; constants are parity targets.

## Hash embeddings (deterministic, local-only)

The default `Embedder` is a **FNV-1a hash embedder**: it hashes text features
(unigrams and bigrams) into a fixed vector, **384 dimensions** by default, with
**zero external dependencies** and full determinism. It satisfies the
no-external-embedding constraint (no API call, no downloaded model).

- `build_embedder(config)` selects by name: `""`/`"hash"` → `HashEmbedder`; a
  `"local"` (ONNX) backend is declared but is honest **`NotImplemented`
  vaporware** — the reimplementation must not silently fall back to a network
  model. `embedding_dims == 0` is a config error.
- The `Embedder` trait exposes `dims()` and an `embed(text) -> Vec<f32>`. The
  hash embedder zero-initializes a `dim`-length vector and accumulates hashed
  feature contributions; identical text ⇒ identical vector (a parity exact-match
  target, alongside slugify and RRF ordering).

## Hybrid search + Reciprocal Rank Fusion

Retrieval fuses a **lexical (BM25)** leg and a **semantic (embedding)** leg with
**Reciprocal Rank Fusion**:

```
RRF(d) = Σ_i  weight_i / (k + rank_i(d))
```

`RrfConfig` defaults: **`k = 60`**, `bm25_weight = 1.0`, `semantic_weight = 1.0`.
Higher `k` flattens the influence of exact rank position. A `HybridResult`
records the fused `score` plus the (1-indexed, optional) `bm25_rank` and
`semantic_rank` so you can see which leg surfaced each hit.

**Porting note (from § a.7):** the donor's lexical leg is a substring/scan
implementation, and although a tantivy index is *built*, it is bypassed. The
first-party crate should **replace the substring-scan leg with real SQLite FTS5
(or a wired tantivy)** and pin which semantics the parity tests target — the RRF
*ordering* is the exact-match parity target, so the lexical leg's ranking must be
made deterministic and documented.

## Recursive composition (`extends` / `includes`)

Skills compose two ways, both resolved recursively with cycle safety:

- **`extends`** — single-parent inheritance chain (override/merge sections).
  `detect_inheritance_cycle` walks the chain and returns the exact cycle path if
  one exists. The chain is bounded by **`MAX_INHERITANCE_DEPTH = 5`**; a chain
  with many `includes` (≥5) raises a `ManyIncludes` resolution warning.
- **`includes`** — composition of slice bundles from other skills (the mechanism
  behind meta-skills / per-eval-class presets).

Resolution is memoized by a **resolution cache** keyed on content hashes: a
cached resolution is invalidated when a dependency's hash changes, and dependents
are transitively invalidated. A separate capability-based `DependencyGraph`
(nodes = skills with provides/requires capabilities, edges = "from depends on
to", indexed capability→providers) supports auto-loading prerequisites, with a
`DependencyLoadMode` controlling at what disclosure level dependencies load
(None / dependencies-at-overview-root-at-requested (default) / full / minimal)
and its own `max_depth` guard (default 100) on the BFS.

## Near-duplicate detection

`dedup` finds near-duplicate skills by a **weighted blend of two similarities**:

- **Semantic** — cosine similarity of embeddings, `semantic_weight = 0.7`.
- **Structural** — overlap of triggers, tags, and requirements,
  `structural_weight = 0.3`; a tag-overlap ratio above `0.5` boosts the
  structural score.
- **Match threshold** `similarity_threshold = 0.85`; up to `max_candidates = 100`
  candidates are evaluated per query skill.

Dedup is advisory (it surfaces candidates for review) — it does not delete; the
autoresearch pipeline routes confirmed duplicates through HITL.

## The spec lens & determinism (subsystem 6)

`SpecLens` is the bidirectional bridge between the in-memory `SkillSpec` and the
on-disk `SKILL.md`:

- `compile(spec) -> String` renders deterministic markdown.
- `parse(md) -> SkillSpec` parses frontmatter + body back into a spec.
- `verify_roundtrip(spec)` asserts `parse(compile(spec)) ≡ spec` — this exact
  round-trip is **parity test #1**. A mismatch is an error, not a warning.

Behavioral details the reimplementation must honor:

- **Ids are H1-slugs.** The skill id is `slugify(title)` derived from the first
  H1, not the `name` field — the catalogue keys on the slug id.
- **Inheritance/composition fields live in YAML frontmatter**, not the markdown
  body — they are parsed from frontmatter only, not re-derived from prose.
- **Incremental indexing** is content-hash based: unchanged skills are not
  re-embedded or re-sliced.
- **`format_version`** freezes v1 algorithms — chars/4 token estimate, the
  slugify rules, the hash-embedding vectors, and RRF ordering — so a later
  algorithm change is a versioned migration, never a silent parity break.

## Layering

Skills resolve under a **Base < Org < Project < User** precedence (higher layer
overrides lower), combined with the content-hash incremental index so a
higher-layer override invalidates only the affected skills.
