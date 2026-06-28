---
name: neuro-quant-pine-language-tooling
description: >
  Routes Pine Script v6 TOOLING work: validating, parsing, fixing, or
  documenting Pine with the local `pinelsp` toolchain (parser, language
  service, LSP, CLI validator, MCP server, tree-sitter grammar, VSCode
  extension), the `pine-script` deep-tool-wiki v6 knowledge base, and
  `openalgo-pinets`/PineTS indicator conversion. Use when the user says
  "pine script", "pinelsp", "validate this .pine file", "fix my LSP
  behavior", "pine v6 error", "convert pine to vectorbt", "convert pine to
  nautilus", "port this Pine indicator to PineTS", or "OpenAlgo chart
  integration". Carries the Pine v6 guardrails (int/int division, strict
  bool / no bool na, short-circuit and/or, dynamic request.*, repaint /
  realtime rollback / varip) and the pinelsp 5-layer model. For the actual
  cross-framework strategy PORT (Pine -> vectorbt / NautilusTrader / Rust /
  C++ / paper) use the strategy-translator skill; this skill owns the Pine
  tooling surface, not the translation.
allowed-tools: Read, Grep, Glob, Bash
---

# Pine Language Tooling

Use this family for Pine Script v6 language support and conversion tooling. It owns the local `pinelsp` toolchain, the Pine Script v6 reference/wiki coverage, and OpenAlgo/PineTS application patterns. For the actual cross-framework strategy port, hand off to `strategy-translator`.

## Scope

This family owns three surfaces:

- `pinelsp`: TypeScript Pine Script v6 language tooling: parser, language service, LSP, MCP server, CLI validator, VSCode extension, pipeline scripts, and tree-sitter grammar.
- `pine-script`: canonical Pine Script v6 knowledge base, including pitfalls, built-ins, refgraphs, and TradingView reference snapshots.
- `openalgo-pinets`: applied PineTS/OpenAlgo charting surface for converting Pine-like indicators into TypeScript/JavaScript indicator modules.

Use this skill when the task matches one of these signals:
- validate / parse / inspect a `.pine` file
- pinelsp (parser, language service, LSP, CLI, MCP, VSCode extension)
- Pine v6 error or pitfall
- TradingView script tooling
- convert Pine indicator to PineTS / OpenAlgo chart
- "convert pine to vectorbt", "convert pine to nautilus" (tooling/diagnostics side; the port itself routes to `strategy-translator`)

Route general RAG ingestion, wiki indexing, and qmd retrieval debugging to `knowledge-rag-control-plane`. Route the cross-framework strategy translation/extrapolation itself to `strategy-translator`.

## Required Workflow

1. Restate the goal, target repo/tool, and acceptance evidence.
2. Open `references/resource-map.md` before loading broader docs.
3. Open `references/verification-checklist.md` for the smallest relevant proof path.
4. Use `references/handoff-template.md` when a long workflow should move to another family skill (including `strategy-translator` for the actual port).
5. Load full docs only when needed from `deep-tool-wiki/<tool>/wiki.md` or `neuro-link/02-KB-main/<tool>/index.md`.
6. Separate verified facts, assumptions, missing resources, and blocked checks in the final answer.

## Operating Rules

Pine Script's source of truth is TradingView. Local tools can parse, validate, document, and partially simulate, but they do not execute Pine canonically. State that boundary whenever conversion or backtest parity is part of the request.

Before editing tooling, classify the task:

| User intent | Primary route | Verification |
| --- | --- | --- |
| Validate a `.pine` file | `pine-validate` / language service | CLI exit, diagnostics, fixture test |
| Fix LSP behavior | `pinelsp/packages/lsp` plus language-service caller | `pnpm run build:tsc`, targeted LSP test |
| Fix parser/type behavior | `pinelsp/packages/core` or `parser-ts` | parser/core tests, corpus or snippet smoke |
| Refresh Pine reference data | `pinelsp/packages/pipeline` and `pine-data` | generated data diff, docs smoke |
| Convert Pine to PineTS/OpenAlgo | `openalgo-pinets` | JS indicator calculation test plus chart/API smoke |
| Update Pine wiki coverage | `deep-tool-wiki/pine-script` | coverage matrix and pitfall checklist |

Ask before network crawling TradingView docs or modifying generated Pine data.

## pinelsp 5-Layer Model

Start from the smallest layer that can explain the behavior:

1. Parser/tokenizer: syntax shape and AST recovery.
2. Core/type layer: Pine forms, built-ins, diagnostics, and semantic rules.
3. Language service: completions, hovers, validation API.
4. LSP adapters: URI/range conversions, document lifecycle, capability wiring.
5. CLI/MCP/VSCode: packaging and host integration.

Expected commands:

```bash
cd pinelsp
pnpm run build:tsc
pnpm test -- --runInBand
./dist/packages/cli/src/cli.js --help
./dist/packages/lsp/bin/pine-lsp.js --version
```

If the repo uses Vitest without `--runInBand`, adapt to the actual test runner instead of forcing a Jest flag.

## Pine v6 Guardrails

Never translate or validate Pine v6 as if it were v5. Explicitly check:

- `int / int` division behavior.
- strict `bool` values with no boolean `na`.
- short-circuiting `and` / `or`.
- dynamic `request.*` behavior.
- `for` loop bound re-evaluation.
- `strategy.exit()` quantity and stop/limit priority changes.
- repainting, realtime rollback, `barstate.isconfirmed`, and `varip`.
- object quotas and max bars back behavior.

When in doubt, add a minimal `.pine` snippet fixture that isolates the rule.

## openalgo-pinets Pattern

Use this route when Pine-like logic needs to become a working web/chart indicator. Keep conversion explicit:

1. Extract Pine inputs and defaults.
2. Map series data to arrays or PineTS context.
3. Recreate built-ins with named helpers, not opaque chained expressions.
4. Separate data fetching from indicator math.
5. Validate parameter ranges before calculation.
6. Render output with TradingView Lightweight Charts or the existing local chart module.

OpenAlgo runtime assumptions:

- OpenAlgo API host defaults to `http://127.0.0.1:5000`.
- The Flask app defaults to `http://127.0.0.1:5005`.
- Secrets belong in `.env`, never committed.

## Progressive Disclosure

This skill keeps local resources in its own folder for immediate operation, but the full documentation belongs in deep-tool-wiki and the navigable leaf docs belong in 02-KB-main. Do not duplicate long API docs here. If a full doc is missing, use the generated stub path from the resource map and mark the lookup incomplete.

## Local Resources

- `references/resource-map.md`: relevant repos, package map, command surface, local docs, deep-tool-wiki targets, and missing-doc status.
- `references/verification-checklist.md`: proof gates for this family.
- `references/handoff-template.md`: structured handoff for multi-step workflows.
- `evals/evals.json`: trigger, false-positive, and missing-resource cases.
- `agents/openai.yaml`: minimal UI metadata for skill discovery.

## Covered Tools

| Tool | Source | Full docs | KB lookup |
| --- | --- | --- | --- |
| pinelsp | `pinelsp` | `deep-tool-wiki/pinelsp/wiki.md` | `neuro-link/02-KB-main/pinelsp/index.md` |
| Pine Script | `deep-tool-wiki/pine-script` | `deep-tool-wiki/pine-script/wiki.md` | `neuro-link/02-KB-main/pine-script/index.md` |
| openalgo-pinets | `toolbox/openalgo-pinets` | `deep-tool-wiki/openalgo-pinets/wiki.md` | `neuro-link/02-KB-main/openalgo-pinets/index.md` |
| vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` |
| Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Failure Modes

- Local validation is not canonical TradingView execution.
- Generated Pine reference snapshots can drift with TradingView docs.
- PineTS conversion can match indicator math without matching TradingView strategy execution semantics.
- LSP range/position bugs often live in adapter conversion, not the parser.
- Repainting and realtime rollback are semantic traps that static validators may not fully catch.

## Done Criteria

A Pine tooling task is done when the response includes:

- Which layer was changed or inspected.
- Whether the issue is parser, semantic, LSP adapter, generated-data, conversion, or runtime integration.
- The exact test or smoke command run.
- Any TradingView parity limitation.

For draft-only work, list proposed Markdown files and say no toolchain runtime state was changed.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.
