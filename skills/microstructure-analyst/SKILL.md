---
name: microstructure-analyst
description: >
  Operational tick + L2/L3 microstructure analyst: ingest raw tape, reconstruct
  order books from snapshot+delta feeds, compute INDICATORS (VPIN, OFI,
  micro-price, Kyle's lambda, Lee-Ready, BVC, Hawkes), detect
  spoofing/layering/quote-stuffing, and wire signals into HFT backtests or live
  nodes. Triggers on "L2 orderbook", "tick/tape data backtest", "HFT", "order
  flow", "OB imbalance", "spoofing detection", "quote stuffing",
  "MAE-exhaustion entry timing". Fire even without those words on "classify
  trade sign", "reconstruct the book from snapshot+delta", "drive a Nautilus
  backtest from L2". DON'T use for microstructure THEORY ("why does VPIN work",
  use microstructure-analysis), cross-framework ports (strategy-translator),
  event-driven engine internals (nautilus-trader), vectorized sweeps (vectorbt),
  tearsheets/MAE (tearsheet-generator), PBO/purged-CV (model-evaluation),
  walk-forward epochs (adaptive-wfo-epoch), or daily-bar strategies where
  microstructure features are noise (use vectorbt directly).
version: "1.0.0"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill, Agent
license: HyperFrequency original (citations to external academic + library work)
---

# Microstructure Analyst

This skill turns a Claude Code session into a working market-microstructure
analyst. Where the sibling `microstructure-analysis` skill is the *conceptual*
framework ("what is OFI, what does VPIN mean"), this one is the *operational*
toolkit: how to ingest 50 GB of compressed Tardis tape, reconstruct a Binance
L2 book from snapshot + delta, compute VPIN / OFI / micro-price / OB imbalance
correctly, detect spoofing live, and wire the resulting signals into a
NautilusTrader / vectorbt / hftbacktest backtest or a Hyperliquid live node.

**This file is a router.** Each section is a short orientation plus a pointer
to a `references/` file that holds the full code, math, and pitfalls. Read the
pointer file before implementing — do not reconstruct kernels from memory.

---

## When to use

- The user has tick or L2 data in hand (Tardis `.csv.gz`, Polygon flat files,
  Databento DBN, Nautilus `OrderBookDeltas` parquet, raw exchange JSON capture)
  and wants to compute features, validate the book, resample to volume bars,
  train a model, or run a backtest.
- The user asks for a specific microstructure indicator (VPIN, OFI, micro-price,
  Roll spread, queue-position estimate, OB imbalance, Hawkes intensity).
- The user is debugging a backtest whose fills don't match live and suspects
  microstructure (queue position, latency, sweep timing).
- The user wants to detect spoofing / layering / quote-stuffing live and
  throttle execution when toxicity spikes.
- The user is building an HFT / market-making strategy and needs to choose
  between Nautilus, hftbacktest, or vectorbt as the backtest engine, or to
  drive `BacktestEngine` from L2 deltas with realistic `LatencyModel` / `FillModel`.

Do **not** use this skill for: daily-bar strategies (microstructure features
are noise at that horizon — use `vectorbt` directly); pure conceptual questions
about *why* a microstructure indicator works (route to `microstructure-analysis`);
or cross-framework strategy ports (route to `strategy-translator`).

---

## Required tooling — the unified gateway contract

Every documentation lookup, code-graph query, AST parse, and knowledge-graph
analysis routes through the **unified mcp2cli gateway** described in the
`neuro-harness` skill. Do not hand-roll API recommendations from training data:
the Nautilus / hftbacktest / Polars / DuckDB / Databento APIs change between
minor versions, and a wrong import path that compiles silently and produces
plausible-looking numbers is the worst failure mode for a microstructure pipeline.

| Task | Use | Why |
| --- | --- | --- |
| Confirm current API surface of `nautilus_trader.backtest.*`, `hftbacktest`, `tardis-machine`, `databento`, `polars`, `duckdb` | `docs-dual-lookup` skill (Context7 + Auggie in parallel) | Catches API drift between SDK versions. |
| Parse a source strategy or research-paper code listing | `tree-sitter` skill via `mcp2cli tree-sitter parse\|query` | Reliable AST nodes; required for Pine v5/v6. |
| Locate symbols / cross-references in an existing strategy codebase | `mcp2cli gitnexus` or the `gitnexus-exploring` skill | Code-graph beats grep when an OFI impl has 30 call sites. |
| Validate academic citations (Lee-Ready 1991, Kyle 1985, Cont-Kukanov-Stoikov 2014, Easley-LdP-O'Hara 2012/2016, Stoikov 2018, Bacry-Mastromatteo-Muzy 2015) | `paper-lookup` / `research-lookup` skills, then `WebFetch` of the DOI | Every citation here is re-verified; check new ones the same way. |
| Knowledge-graph / topical-gap analysis on a paper corpus | `mcp2cli infranodus` or the `infranodus` skill (LOCAL OSS engine only) | Per `project_infranodus_local_only.md` — never default to infranodus.com. |

If `neuro-harness` is unreachable (no compose stack, sandboxed runtime), say so
and degrade in this order: Context7 directly → WebFetch on the framework's docs
site → training-data recall, flagged with the source tier on each claim.

---

## Pipeline overview

```
Raw venue feed                Catalog                Indicator                 Strategy / Backtest / Live
─────────────────             ──────                 ─────────                 ──────────────────────────
Tardis .csv.gz   ─┐
Polygon flat     ─┼─► ingest ─► validate ─► store ─► VPIN / OFI / OB-imb ─► sample to bars ─► vectorbt
Databento DBN    ─┤   (Polars  (seq nums,  (parquet  micro-price, NVWAP,                       └─► ML
Binance WS JSON  ─┤   chunked   crossed    DuckDB,   TPS, Roll, Hawkes,
Hyperliquid WS   ─┤   reads,    book,      Nautilus  spoofing detector
NT parquet       ─┘   PDP)      gaps,      catalog)  └─► live throttle ─► Nautilus TradingNode
                                aggressor)                                  on Hyperliquid / Binance
```

The pipeline is **deliberately one-way and append-only** at the catalog layer.
If you find you need to mutate stored ticks, the bug is upstream — fix the
ingest validator instead.

---

## Section map — where the detail lives

| Section | Covers | Reference file |
| --- | --- | --- |
| **A — Tape ingestion** | Sources (Tardis/Polygon/Databento/CCXT/Nautilus); lazy multi-GB reads (Polars/DuckDB); `ts_event` vs `ts_init` vs wall-clock; trade-sign classification (Lee-Ready, BVC, aggressor flag); matched-pair dedup | [`references/ingestion-and-reconstruction.md`](references/ingestion-and-reconstruction.md) (Section A) |
| **B — L2/L3 reconstruction** | Which level you need; snapshot+delta `OrderBookL2`; consistency validators (no-cross, seq monotonicity, snapshot reconcile, price grid); reconnect-replay protocol; storage formats; Nautilus `OrderBookDeltas` integration | [`references/ingestion-and-reconstruction.md`](references/ingestion-and-reconstruction.md) (Section B) |
| **C — Indicators** | VPIN, NVWAP/VWAP, OB imbalance + Stoikov micro-price, OFI (Cont-Kukanov-Stoikov), spoofing/layering/quote-stuffing detection, TPS regime, spread dynamics (Roll/effective/realized), Hawkes intensity — each with kernel + interpretation + pitfalls | [`references/indicators.md`](references/indicators.md) |
| **D — Backtest setup** | vectorbt (volume bars first); Nautilus `BacktestEngine` from L2 deltas (`LatencyModel`/`FillModel`/`BookType`); hftbacktest queue-position fidelity; latency- and fill-model selection tables | [`references/backtest-and-live.md`](references/backtest-and-live.md) (Section D) |
| **E — Live trading** | In-memory book + indicator engine wiring; live toxicity throttle (`MicrostructureThrottle`); round-trip latency monitoring | [`references/backtest-and-live.md`](references/backtest-and-live.md) (Section E) |
| **G — MAE-exhaustion timing** | Entry-timing throttle: six-signal exhaustion model, presets, three integration levels, indicative results | [`references/mae-exhaustion.md`](references/mae-exhaustion.md) |
| **Pitfalls + citations** | The 10 consolidated pitfalls (P1–P10) and the full verified bibliography | [`references/pitfalls-and-citations.md`](references/pitfalls-and-citations.md) |

### Runnable Python helpers (already wired)

| File | Class | Purpose |
| --- | --- | --- |
| [`references/features.py`](references/features.py) | `OrderFlowFeatures`, `OrderFlowSnapshot` | 33 L2-derived features per bar (imbalance, spread, depth, microprice, wall detection) |
| [`references/exhaustion.py`](references/exhaustion.py) | `ExhaustionDetector`, `ExhaustionType` | Six-signal weighted exhaustion model (Section G) |
| [`references/mae_strategy.py`](references/mae_strategy.py) | `MAEOptimizedStrategy`, `MAEStrategyConfig` | NautilusTrader base strategy with entry state machine + MAE logging |
| [`references/resource-map.md`](references/resource-map.md) | — | Data-path conventions, extract → backtest → compare CLI flow, troubleshooting |

`exhaustion.py` and `mae_strategy.py` import from `features.py`, so keep the
three co-located.

---

## Section F — Pre-built helpers + ecosystem cross-links

### F.1 In-repo sibling skills (route here, don't reimplement)

| Skill | What it owns | Used in |
| --- | --- | --- |
| `nautilus-trader` | Venue wiring (Binance, Hyperliquid); `BacktestEngine`; `TradingNode`; Hyperliquid SDK patch; the canonical live-trading wiring file. The execution-mechanics owner. | Section D/E |
| `tardis-data-agent` | Tardis ingestion, manifest tracking, daily front-fill, CSV → parquet, validation. The historical-data owner. | Section A |
| `tearsheet-generator` | Performance + risk reporting (quantstats-rs); MAE/leverage. The output owner. | Final stage of any backtest |
| `vectorbt` | Vectorised signal backtests, parameter sweeps, walk-forward. The bar-level backtest owner. | Section D |
| `microstructure-analysis` | The *conceptual* framework — layered model, Lee-Ready/OFI/VPIN intuition. Sibling + dependency. | Throughout |
| `microstructure-feature-engineering` (when present) | Leakage-safe feature extraction; triple-barrier labelling for tick-rate signals. | Handing features to ML |
| `strategy-translator` | Cross-framework strategy ports (vectorbt ↔ Nautilus ↔ Pine ↔ Rust). | Porting a strategy |
| `model-evaluation` | Purged + embargoed CV for HF financial ML. | Tick-rate model eval |

### F.2 External libraries (caveats in `references/pitfalls-and-citations.md`)

`mlfinlab` (BVC/fracdiff/triple-barrier/Kyle's lambda — research license only),
`hftbacktest` (HyperFrequency fork; book-level HFT backtester),
`tick` (Hawkes / point processes), `databento` (schema-typed L1/L2/L3),
`polars` + `duckdb` (lazy reads / predicate pushdown),
`sortedcontainers` (research-grade L2 book).

### F.3 What this skill deliberately doesn't cover

- ML model architectures on microstructure features → `lstm-forecast`,
  `lightgbm`, `catboost`, `cnn-pattern-recognition`, `autoencoder-anomaly-detection`.
- Walk-forward optimisation / triple-barrier labelling → `adaptive-wfo-epoch`,
  `feature-engineering`.
- Multi-venue arbitrage execution / routing → `nautilus-trader`.
- Pine Script ports of microstructure ideas → `strategy-translator`.
