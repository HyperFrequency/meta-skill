---
name: skill-manager-engine
version: 0.1.0
description: >-
  Clean-room BEHAVIORAL SPECIFICATION of the meta_skill (`ms`) engine as the
  contract for neuro-centrifuge's D11 `harness_skills` crate: anti-pattern
  mining, the trajectory-detection composite (phase segmentation +
  session-quality gate), constrained token packing + progressive disclosure,
  recursive skill composition, near-duplicate detection, and the bandit that
  ranks skill suggestions. Use when specifying, porting, or parity-testing the
  Rust skill-manager crate; when you need the exact behaviors, constants, and
  formulas a reimplementation must honor (confidence n/(n+2), quality min_score
  0.3, RRF k=60, FNV-1a 384-dim embeddings, 8 bandit arms, inheritance depth 5);
  or when wiring the engine into D12 loops 3/4 and D13 classes 1/3/7. Describes
  OBSERVED behavior only (meta_skill is MIT + OpenAI/Anthropic rider). Do NOT use
  to score/gate one SKILL.md (use skill-eval-runner), audit the whole skill fleet
  (use meta-skill), or author/heal a skill (use skill-creator) — this documents
  the ENGINE, not the library.
---

# skill-manager-engine

This skill is the **behavioral contract** for the neuro-centrifuge `harness_skills`
crate (a.k.a. skill-manager) — the D11 skill engine. It captures, as an
implementation-independent specification, the behaviors of the `ms` (meta_skill)
donor so a first-party Rust reimplementation can be built and **parity-tested
against observed behavior**, never against copied source.

**Clean-room boundary (load-bearing).** meta_skill ships under MIT with an
OpenAI/Anthropic usage rider. This document describes *what the engine does* —
data models, algorithms, constants, invariants — in original prose. It names the
donor's types as behavioral vocabulary (the parity targets), but reproduces **no
source code**. Every crate that consumes this spec must re-derive the logic and
carry its own `NOTICE.md`. Donor read-for-accuracy is allowed; donor copy is not.

Scope is the **engine's seven subsystems**. It is not the skill library, not a
single-skill scorer, and not a fleet auditor — those route out (see Cross-links).

## The seven subsystems (route to depth)

1. **Anti-pattern mining** — turning failure evidence (rollbacks, corrections,
   failure signals, explicit markers) into versioned `NEVER X when Y` rules with
   evidence-strength confidence and source-diversity bonuses. This is the D12
   loop-3 backbone and the HITL-review schema.
   → `references/anti-pattern-mining.md`

2. **Trajectory-detection composite** — the two-stage cheap first-pass over a
   session: **phase segmentation** (Recon → Change → Validation → WrapUp) then a
   **session-quality gate** (weighted positive signals minus backtracking /
   abandonment penalties, `min_score 0.3`) that filters junk sessions *before*
   expensive judging. Feeds D12 loop-3 and D13 classes 3/7.
   → `references/trajectory-composite.md`

3. **Token packing + progressive disclosure** — six disclosure levels with token
   budgets, micro-slicing a skill into typed atomic slices, and a
   density-greedy constrained packer (mandatory slices, coverage quotas, novelty
   penalty, swap-improve passes) driven by named **pack contracts**
   (complete/debug/refactor/learn/quickref/codegen) that map to eval-class
   context loads.
   → `references/packing-and-disclosure.md`

4. **Search, recursion & dedup** — deterministic FNV-1a hash embeddings (384-dim,
   zero external calls), hybrid lexical+semantic retrieval fused by Reciprocal
   Rank Fusion (`k=60`), recursive `extends`/`includes` composition with cycle
   detection and a depth-5 inheritance ceiling, and near-duplicate detection
   (semantic 0.7 + structural 0.3, match threshold 0.85).
   → `references/search-recursion-dedup.md`

5. **Bandit suggestions** — an 8-arm multi-armed bandit (Thompson/Beta sampling
   with a UCB exploration bonus) over ranking signals, rewarded by real skill
   outcomes (`SkillFeedback`), optionally contextualized by a 28-dim feature
   vector. This is the D12 loop-4 skill-selection learner.
   → `references/bandit-suggestions.md`

6. **Spec lens & determinism** — the `SkillSpec ↔ SKILL.md` bidirectional lens
   whose exact round-trip is parity test #1; H1-slug ids; content-hash
   incremental indexing; the `format_version` freeze that pins v1 algorithms
   (chars/4 token estimate, slugify, hash-embedding vectors, RRF ordering).
   → `references/search-recursion-dedup.md` (§ Spec lens)

7. **D11 crate contract** — how the six subsystems land as `harness_skills`,
   the trait seams (`SessionSource`, `Embedder`, `GraphAnalyzer`,
   `SkillRepository`), the parity corpus, phase (P1/P2) split, security-gate
   reconciliation with the Macro tool-plane, and licensing fences.
   → `references/crate-contract.md`

## When this fires vs when it does not

Use it when the task is about the **engine's behavior or its port**:

- Writing or reviewing the `harness_skills` crate spec / PRD section.
- Answering "what confidence does a 3-evidence anti-pattern get?", "what's the
  quality-gate cutoff?", "how are slices ranked into a token budget?", "which
  signals does the suggestion bandit arm on?".
- Building D2 parity tests that assert the reimplementation matches `ms` behavior.
- Wiring the engine into D12 loop-3 (trajectory/anti-pattern scan) or loop-4
  (skill eval & evolution), or feeding its trajectory composite into D13.

Do **not** use it for:

- **Scoring/gating one SKILL.md** against the frontier rubric → `skill-eval-runner`.
- **Fleet governance** (catalogue, health, duplicate-name/trigger-collision
  detection across many repos) → `meta-skill`.
- **Authoring or healing a single skill** (draft → evals → rewrite) → `skill-creator`.
- General library facts (the 378-skill count, branch, CATALOG state) — those are
  library state, not engine behavior; see `references/crate-contract.md` § Library facts.

## Invariants a reimplementation must never break

- **Determinism.** Embeddings, slugs, token estimates, RRF ordering, and the
  spec-lens round-trip are pure functions of input — no clocks, no network, no
  RNG in the indexing/packing path. The bandit is the *only* stochastic
  component, and its RNG is explicit and seedable.
- **Evidence monotonicity.** Adding evidence to an anti-pattern never lowers its
  confidence; removing the last evidence returns it to 0.
- **Budget safety.** The packer never exceeds its token budget; mandatory-slice
  omission is a hard error unless explicitly downgraded.
- **Local-only embeddings.** The default embedder makes no external call; any
  `local`-ONNX backend is honest `NotImplemented`, never a silent network hop.
- **Cycle safety.** Recursive composition detects cycles and enforces the depth
  ceiling rather than looping.

## Cross-links

- **skill-eval-runner** (sibling) — the frontier-rubric *scorer + regression
  gate* for one skill. This engine's quality scoring and YAML skill-test
  framework feed it; it does not replace it.
- **meta-skill** — fleet-level audit/catalogue/health. This engine is one
  component that meta-skill governs; run meta-skill *around* a library, this spec
  *inside* the engine.
- **skill-creator** — single-skill authoring. Produces the SKILL.md files this
  engine indexes, packs, and suggests.
- **trajectory-miner**, **hitl-interview** — the D12 loop-3 skills that consume
  this engine's trajectory composite and anti-pattern schema.
- Autoresearch spec § a.7 (`neuro-centrifuge-autoresearch.md`) is the
  authoritative feature/phase map this skill documents.
