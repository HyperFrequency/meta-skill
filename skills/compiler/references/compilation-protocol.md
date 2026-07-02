# ARA Compilation Protocol — Full Procedure

This is the detailed operating procedure for the ARA Universal Compiler. SKILL.md is the
lean router; this file holds the step-by-step reasoning protocol, generation rules, and
non-negotiable guardrails. Load it before generating any ARA files.

## Input Reading Strategy

The compiler is **open-ended** — there is no fixed input schema. Figure out what you have
and extract maximum structured knowledge from it.

1. **Identify what you have.** Glob, read, and explore the provided paths. Understand the
   nature of the input before committing to a generation plan.
2. **Maximize coverage.** Cross-reference all available sources. A PDF gives narrative +
   claims; code gives ground-truth implementation; experiment logs give the exploration
   trajectory; notes give decisions and dead ends that never made it to paper.
3. **Ask when stuck.** If the input is ambiguous or incomplete, ask the user to fill gaps
   rather than hallucinating. The user is a collaborator, not a passive consumer.
4. **Handle partial inputs gracefully.** Not every ARA field will be fillable from every
   input. Populate what you can with high confidence, mark gaps explicitly with "Not
   available from provided input", and tell the user what's missing.

For PDFs, read every page **including appendices** — appendices often carry
reproduction-critical content and should be treated with the same priority as main-text
pages. For repos, prioritize: README → core algorithm files → configs → environment files.

## 4-Stage Epistemic Chain-of-Thought

Before writing any files, reason through these four stages. Think carefully about each.

### Stage 1 — Semantic Deconstruction
Strip narrative framing. Extract the raw knowledge atoms:
- Mathematical formulations and equations
- Architectural specifications and component descriptions
- Experimental configurations (hyperparameters, hardware, datasets, seeds)
- ALL numerical results and benchmarks (exact values, never rounded)
- Citation dependencies and their roles (imports, extends, bounds, refutes)
- Negative results, ablation findings, rejected alternatives
- Implementation tricks, convergence hacks, sensitivity observations

Then perform an **evidence capture pass**:
- For every source table or figure you plan to cite, first capture the original source
  identifier and caption exactly (`Table 2`, `Figure 4`, etc.)
- Transcribe the raw table/figure content before making any claim-specific summary
- If you create a filtered view for one claim, store it as a **derived subset**, not as the
  original table itself
- Never label a subset or merged summary as `Table N` unless it reproduces the original
  source table faithfully
- If PDF extraction is ambiguous, re-read the page with layout preserved or inspect the page
  manually before writing evidence files

### Stage 2 — Cognitive Mapping
Map extracted atoms to `/logic/`:
- **problem.md**: observations (with numbers) → gaps → key insight → assumptions
- **claims.md**: falsifiable claims with proof pointers to experiment IDs (E01, E02...),
  plus a separation between direct evidence basis and higher-level interpretation
- **concepts.md**: ≥5 formal definitions with notation and boundary conditions
- **experiments.md**: ≥3 declarative verification plans (NO exact numbers — directional only)
- **solution/**: architecture (component graph), algorithm (math + pseudocode), constraints,
  heuristics
- **related_work.md**: typed dependency graph (imports/extends/bounds/baseline/refutes)

Appendix content (worked examples, prompt templates, enumerated taxonomies, annotation
schemas, extended analyses, prescriptive content) should be routed into the ARA layers where
it fits best, preserving the granularity the source uses. Never silently drop an appendix
section.

When writing claims:
- Phrase the main `Statement` at the strongest level directly supported by the cited evidence
- Put raw support in `Evidence basis`
- Put any broader synthesis in `Interpretation`
- If the evidence only shows validation metrics, do not upgrade the claim to training
  dynamics or optimization quality unless training-side evidence is also captured

`related_work.md` should reflect the paper's full citation footprint, not only the closest
predecessors. Works with a specific technical delta get full `RW` blocks; remaining citations
from the paper's References list should still be captured (more briefly) so the intellectual
neighborhood is preserved.

### Stage 3 — Physical Stubbing
Generate `/src/`:
- **configs/**: exact hyperparameter values with rationale and sensitivity
- **execution/**: ≥1 Python code stub implementing the NOVEL contribution (typed signatures,
  no boilerplate)
- **environment.md**: Python version, framework, hardware, dependencies, seeds
- If repo available: use actual code to improve stub precision
- If rubric provided: produce `rubric/requirements.md` mapping every leaf node

### Stage 4 — Exploration Graph Extraction
Reconstruct the research DAG for `/trace/exploration_tree.yaml`:
- Root nodes = central research questions
- Experiments and decisions nest as children
- Dead ends from ablations/rejected alternatives = typed leaf nodes
- ≥8 nodes, must include dead_end and decision types
- Use `also_depends_on` for DAG convergence points
- Every node must declare whether it is `explicit` from source material or `inferred` from
  reconstruction
- Explicit nodes should carry source references (table/figure/section labels)
- Inferred nodes are allowed only when they help reconstruct the paper's logic without
  pretending to be literal session logs

See [exploration-tree-spec.md](exploration-tree-spec.md) for the full YAML spec.

## Generating Files

Write ALL mandatory files. The complete directory structure and field-level format for every
file lives in [ara-schema.md](ara-schema.md). The mandatory file set the validator enforces
is enumerated in [validation-checklist.md](validation-checklist.md) §2.

Evidence-generation rules:
- Preserve **raw source tables** separately from any **derived subset** views
- A file named after a source object (for example `table3_...`) must match that source
  object's caption and contents
- If only a subset is included, the filename must say `derived_`, `subset_`, or equivalent,
  and the file must state what it was derived from
- Do not merge rows from different source tables into one evidence file unless the file is
  explicitly labeled as a derived comparison

## Coverage Check Loop (max 3 rounds)

Before running Seal validation, verify that the ARA faithfully covers the source material.
Repeat up to **3 rounds**; stop early if a round produces no patches.

Each round: re-read the source, identify anything not yet captured or only shallowly captured
in the ARA, patch those gaps, then note how many fixes were made. If zero, exit early. Pay
particular attention to appendix content and to citations from the paper's References list,
which are easy to miss on the first pass.

The coverage loop does not replace validation — it ensures the ARA is semantically complete
before structural checks run.

## Validate

Run ARA Seal Level 1 validation. The complete set of checks the validator performs lives in
[validation-checklist.md](validation-checklist.md). Fix ALL failures before reporting success.

## Fix & Iterate

For each validation failure:
1. Read the failing file
2. Apply targeted edits (prefer Edit over full rewrite to preserve correct content)
3. Re-validate after all fixes

Typically converges in 2-3 rounds.

## Report

Print a summary:
- Artifact location
- File count and total size
- Validation result (pass/fail with details)
- Key statistics: number of claims, experiments, heuristics, concepts, tree nodes, evidence
  files

## Critical Rules (non-negotiable)

1. **Exact numbers**: All numerical values copied EXACTLY from source — never round or
   approximate
2. **No hallucination**: Never invent claims, results, or heuristics not in the source
   material
3. **Experiments have NO exact numbers**: `experiments.md` contains only directional/relative
   expected outcomes. Exact numbers go in `evidence/`
4. **Every claim has proof**: Proof field references experiment IDs (E01, E02), not file paths
5. **Cross-layer binding**: Claims ↔ Experiments ↔ Evidence ↔ Code refs must all resolve
6. **Dead ends matter**: Include failed approaches, rejected alternatives, ablation findings
7. **"Not specified"**: If information is genuinely unavailable, write "Not specified in
   paper" — never guess
8. **No fake source labels**: Never call a derived subset `Table N` or `Figure N` unless it
   faithfully reproduces the original source object
9. **No synthetic trace history**: Do not invent decisions, dead ends, or experiments that are
   not explicit in the provided inputs; if a trajectory is inferred, mark it as inferred or
   omit it
10. **Evidence-limited wording**: Do not use stronger language than the evidence supports;
    separate direct observations from interpretation
