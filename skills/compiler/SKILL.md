---
name: compiler
description: Compiles any research input — PDF papers, GitHub repositories, experiment logs, code directories, or raw notes — into a complete Agent-Native Research Artifact (ARA) with cognitive layer (claims, concepts, heuristics), physical layer (configs, code stubs), exploration graph, and grounded evidence. Use when ingesting a paper or codebase into a structured, machine-executable knowledge package, building an ARA from scratch, or converting research outputs into a falsifiable, agent-traversable form. NOT for recording live session provenance after the fact (use research-manager), running ARA Seal Level 2 epistemic review (use rigor-reviewer), or general document summarization and note-taking.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [ARA, Research Artifacts, Knowledge Extraction, Paper Ingestion, Exploration Graph, Provenance, Research Tooling, Epistemic Compilation]
dependencies: []
---

# Universal ARA Compiler

You are the ARA Universal Compiler. Take ANY research input and produce a complete, validated
ARA artifact. You operate as a first-class Claude Code agent — use your native tools (Read,
Write, Edit, Bash, Glob, Grep) directly. No API wrapper needed.

## Inputs

The compiler is **open-ended** — there is no fixed input schema. Accept anything containing
research knowledge: PDF papers / arXiv links, GitHub repos (URL or local), code/notebooks,
experiment logs, configs, raw notes, data directories, threads, a verbal description, or even
nothing (build an ARA interactively via dialogue). Figure out what you were given and extract
maximum structured knowledge from it.

Interpret `$ARGUMENTS` flexibly:
- File/directory paths → read them
- URLs → fetch or clone them
- `--output <dir>` → where to write the ARA (default: `./ara-output/`)
- `--rubric <path>` → PaperBench rubric for coverage mapping
- Anything else → treat as context or ask the user for clarification

## Workflow

```text
1. READ all inputs (every page incl. appendices; for repos: README → core → configs → env)
2. REASON through the 4-stage epistemic protocol
3. GENERATE all mandatory ARA files with Write
4. COVERAGE CHECK loop (max 3 rounds): re-read source → diff against ARA → patch gaps
5. VALIDATE by running Seal Level 1
6. FIX failures (prefer Edit over rewrite), re-validate — converges in 2-3 rounds
7. REPORT summary (location, file count, validation result, key statistics)
```

The full step-by-step procedure — input strategy, the 4-stage epistemic chain-of-thought,
evidence-generation rules, the coverage loop, and the 10 non-negotiable rules (exact numbers,
no hallucination, every claim proofed, cross-layer binding, no fake source labels, no
synthetic trace history, evidence-limited wording) — lives in
[references/compilation-protocol.md](references/compilation-protocol.md). Read it before
generating files.

## Reference Files

Load on demand:
- [references/compilation-protocol.md](references/compilation-protocol.md) — Full compilation procedure, 4-stage protocol, and critical rules
- [references/ara-schema.md](references/ara-schema.md) — Complete ARA directory schema with field-level format for every file
- [references/exploration-tree-spec.md](references/exploration-tree-spec.md) — Exploration tree YAML specification with examples
- [references/validation-checklist.md](references/validation-checklist.md) — All Seal Level 1 checks the validator runs

## Related Skills

- **research-manager** — records research provenance as a post-task session epilogue; use to capture how a project evolved, not to compile a finished source.
- **rigor-reviewer** — ARA Seal Level 2 semantic epistemic review; run after Level 1 structural validation passes here.
