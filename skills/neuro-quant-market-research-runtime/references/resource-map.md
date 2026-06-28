# Market Research Runtime Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `vectorbtpro` | vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` | existing-full |
| `nautilus-trader` | Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` | existing-full |
| `hftbacktest-cpp` | hftbacktest_cpp | `toolbox/hftbacktest_cpp` | `deep-tool-wiki/hftbacktest_cpp/wiki.md` | `neuro-link/02-KB-main/hftbacktest_cpp/index.md` | existing-full |
| `hftbacktest` | hftbacktest | `deep-tool-wiki/hftbacktest` | `deep-tool-wiki/hftbacktest/wiki.md` | `neuro-link/02-KB-main/hftbacktest/index.md` | existing-full |
| `quantstats-pyfolio` | quantstats / pyfolio | `toolbox/docs/tools/quantstats-pyfolio.md` | `deep-tool-wiki/quantstats-pyfolio/wiki.md` | `neuro-link/02-KB-main/quantstats-pyfolio/index.md` | partial |
| `pandas-ta` | pandas-ta | `toolbox/docs/tools/pandas-ta.md` | `deep-tool-wiki/pandas-ta/wiki.md` | `neuro-link/02-KB-main/pandas-ta/index.md` | partial |

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Tool Coverage And Public Sources

Context7 and Auggie were requested through the `docs-dual-lookup` workflow but
their MCP tools were not available when this map was drafted, so API-level claims
should be rechecked against the licensed fork / current docs before relied upon.

| Tool | Role in this family | Primary local source | Public source checked | Notes |
|---|---|---|---|---|
| `vectorbt.pro` | Vectorized strategy research, indicator factories, portfolio sweeps, walk-forward style validation, research-to-execution handoff | `deep-tool-wiki/vectorbtpro/wiki.md`, `toolbox/docs/tools/vectorbtpro.md`, `toolbox/docs/tools/vectorbtpro.ontology.md` | `https://vectorbt.pro/`, `https://vectorbt.pro/features/indicators/` | Treat as paid/private. Avoid hard API promises unless checked against the licensed fork. |
| `hftbacktest` | L2 replay, queue-position simulation, feed/order latency, market-making research, accelerated parameter sweeps | `deep-tool-wiki/hftbacktest/wiki.md` | `https://hftbacktest.readthedocs.io/`, `https://hftbacktest.readthedocs.io/en/v1.8.4/latency_models.html`, `https://hft.readthedocs.io/en/latest/order_fill.html` | Best fit when bar-level execution is too coarse. |
| `hftbacktest_cpp` | CME futures MBO simulator, C++ fill/latency modeling, future Python bindings | `deep-tool-wiki/hftbacktest_cpp/wiki.md`, `toolbox/hftbacktest_cpp/README.md` | No stronger public source found beyond repo-local docs | Mark Python-binding claims as future/coming unless verified in tree. |
| `pandas-ta` / `pandas-ta-classic` | Technical indicator feature generation and formula parity checks | `toolbox/docs/tools/pandas-ta.md`, `toolbox/docs/tools/pandas-ta.ontology.md` | `https://pypi.org/project/pandas-ta-classic/`, `https://xgboosted.github.io/pandas-ta-classic/` | Prefer explicit no-lookahead settings for indicators with known leak risk. |
| `quantstats` | Return-series analytics and HTML tear sheets | `toolbox/docs/tools/quantstats-pyfolio.md`, `toolbox/docs/tools/quantstats-pyfolio.ontology.md` | `https://github.com/ranaroussi/quantstats` | Use after returns are clean. It is not an execution simulator. |

## Skill Family Edges

- To `execution-ui-ops`: pass only validated research outputs with explicit data provenance and execution assumptions.
- To `nautilus_trader`: translate only after deciding that event-driven execution semantics are required.
- To data-feed skills: request Tardis, Databento, exchange CSV, or Parquet catalog inputs before modeling fills.
- To optimization skills: escalate parameter sweeps only after a one-symbol smoke run proves the pipeline.

## Promotion Checklist

- Re-run Context7 and Auggie lookups for any exact API examples before relying on them.
- Add repo-specific command snippets only after confirming the active venv and pinned versions.
- Add artifact naming conventions once the wider skillset decides where generated research reports should land.

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.
