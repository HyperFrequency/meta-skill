---
name: ml-hypothesis-design
version: 0.1.0
description: Design testable ML hypotheses for quant strategies with statistical rigor. Use when formulating null vs alternative hypotheses for trading signals, computing required statistical power before research, applying multiple-testing corrections (Bonferroni, FDR, Deflated Sharpe Ratio), or preregistering a research plan. Triggers on phrases like "is this signal real", "how many backtests can I run", "deflate this Sharpe", "preregister this study", "what's the null", "minimum backtest length", or "how do I avoid p-hacking". For exploratory ideation use scientific-brainstorming; for general hypothesis formulation use hypothesis-generation; for evaluating models after the fact use model-evaluation.
allowed-tools: Read Write Edit Bash
---

# ML Hypothesis Design for Quant Strategies

## Overview

Quant ML research has a hard adversary that bench science doesn't: **the data is public, the search space is enormous, and a researcher who tries 1,000 strategies will find a "significant" one by chance alone**. The field is littered with backtests that passed every conventional test but failed live.

This skill is the discipline that prevents that. It treats every trading signal as a hypothesis that must be specified *before* you look at the result, with a null model, a power calculation, and a multiple-testing budget. It refuses to let a researcher quote a raw Sharpe ratio without saying how many trials it survived.

## When to Use This Skill

Use this skill when:

- About to launch a new research program and need to define what "this works" means before running a backtest
- Comparing N candidate strategies and need to decide which (if any) cleared a multiple-testing corrected threshold
- Reporting a strategy's performance and need to deflate its Sharpe for selection bias
- Deciding how long a backtest must run to detect a target Sharpe at desired power
- Writing a preregistration document or research log entry
- Reviewing someone else's claim that a strategy "worked"

Do **not** use this for: exploratory data analysis where you have no prior hypothesis (use `scientific-brainstorming` first), or pure model evaluation after a hypothesis is already specified (use `model-evaluation`).

## Core Framework

### Step 1 — State the hypothesis as a falsifiable claim

Every quant hypothesis must have these four components, written down *before* the backtest runs:

1. **Population / universe.** Which instruments, what frequency, what date range? "S&P 500 constituents as of 2010-01-01, daily close-to-close, 2010-2020 in-sample, 2020-2024 out-of-sample."
2. **Signal definition.** Exactly how the feature is computed. Pseudocode, not English. If you can't write the code without the data in front of you, the hypothesis isn't specified.
3. **Null model H0.** What does "this signal doesn't work" look like? The most common nulls: (a) Sharpe = 0 after costs, (b) Sharpe equals the benchmark (e.g. SPY buy-and-hold), (c) returns are indistinguishable from a random-sign permutation of the same feature.
4. **Alternative H1.** A specific effect size you'd commit to detecting. Not "this strategy works" but "annualized Sharpe ≥ 0.8 net of 5 bps round-trip cost". Without a target effect size you cannot compute power.

**Decision rule.** State what result will make you abandon the hypothesis. If your decision rule is "ship if profitable", you have no hypothesis — you have a wish.

### Step 2 — Compute statistical power before running the backtest

The Sharpe ratio has a known sampling distribution. The standard error under the null SR = 0 is approximately:

```
SE(SR) ≈ sqrt((1 + 0.5 * SR^2) / N)
```

where `N` is the number of observations (e.g. trading days). For a normal-returns approximation (Lo, 2002), to detect a Sharpe of 0.8 at 80% power and 5% significance you need roughly `N ≥ ((z_α + z_β) / SR_target)^2 ≈ (1.65 + 0.84)^2 / 0.64 ≈ 9.7` years of daily data — and that is the *power requirement under the null*, not the trial-adjusted requirement.

**Minimum Backtest Length (MinBTL)** from Bailey & Lopez de Prado (2014) generalizes this for `N_trials` candidate strategies. The intuition: if you tried more strategies, you need a longer backtest for the best one to be credible.

### Step 3 — Budget for multiple testing *before* you start

If you will examine `N` candidate strategies, fix the multiple-testing correction in advance:

- **Bonferroni** (controls family-wise error at level α): require each test's p-value < α / N. Conservative; suitable when N is small and false positives are catastrophic.
- **Benjamini-Hochberg FDR** (controls false discovery rate at q): less conservative, suitable for screening when you expect a few real signals among many.
- **Deflated Sharpe Ratio** (Bailey & Lopez de Prado 2014): adjusts the observed Sharpe for the number of trials, the variance across those trials, the skewness and kurtosis of returns, and the sample length. This is the strongest correction for quant research and is what should be reported.

The non-negotiable rule: **the trial count `N` includes every variant you considered, not just the one you're reporting.** Hyperparameter sweeps count. Universe variants count. Failed experiments count.

### Step 4 — Preregister

Write down — in a timestamped artifact (a markdown file in version control, an Obsidian note with a date stamp, anything immutable) — the entire plan before you have a result:

- The four hypothesis components from Step 1
- The N_trials budget and chosen correction
- The exact metric being optimized (e.g. "out-of-sample Sharpe over 2020-2024")
- The decision rule for ship/no-ship
- Any data transformations and the order they will be applied
- The walk-forward / cross-validation scheme (delegate detail to `model-evaluation`)

After the result is in, write the diff: what you actually did vs the preregistration, and why.

### Step 5 — Report deflated metrics, not raw

When publishing a result, the reported headline metric is the Deflated Sharpe and the probability of overfitting (PBO), not the raw Sharpe. Raw metrics go in an appendix.

## Code Snippets

Reference implementations (Deflated Sharpe Ratio, Minimum Backtest Length,
Bonferroni strategy sweep) live in
[`references/code_snippets.md`](references/code_snippets.md). They mirror the
`mlfinlab` `BacktestStatistics` API — prefer that library in production.

## Common Pitfalls

1. **Counting only the "final" strategy in the trial budget.** Every hyperparameter you tuned, every universe you tested, every alternative spec — they all count. If you don't know N, assume the worst case.
2. **Selecting in-sample, evaluating in-sample.** If you used 2010-2020 to pick the best variant, the 2010-2020 Sharpe is meaningless. You need a truly held-out period (see `model-evaluation` for purged + embargoed CV).
3. **Quoting raw Sharpe in the abstract, deflated Sharpe in the appendix.** This is backwards. The headline number is the corrected one. If you can't say it with a deflated metric, you don't have a result.
4. **Assuming Gaussian returns when computing significance.** Returns have skew and excess kurtosis; this inflates the standard error of the Sharpe. Use the Mertens (2002) correction (included in the DSR snippet).
5. **Treating "passes preregistration" as "is real".** Preregistration prevents the worst form of cherry-picking, but doesn't guarantee causal validity, robustness to regime change, or that the signal will survive in live trading. It's necessary, not sufficient.
6. **Hypothesizing after the result is known (HARKing).** If you see a pattern in the data and then write a hypothesis to "test" it on the same data, you have circular reasoning. Either get fresh data, or commit and run.

## Tooling References

This skill defines methodology. Operationalize it with:

- **`scikit-learn`** skill — for the underlying model fitting; pair with this skill's preregistration step.
- **`model-evaluation`** skill (sister skill) — for purged/embargoed CV, walk-forward, and PBO computation.
- **`feature-engineering`** skill (sister skill) — for leakage-safe feature pipelines that don't undermine your hypothesis.
- **`vectorbt`** skill — for running the backtest sweep that produces the `n_trials` number you'll deflate against.
- **`tearsheet-generator`** skill — for the final report; include both raw and deflated metrics.
- **`quant-analyst`** skill — for higher-level workflow when this is one phase of a larger research project.

## References

Full bibliography — primary/adjacent libraries, deep-dive doc pages, academic
papers, tutorials, and benchmark datasets — is in
[`references/bibliography.md`](references/bibliography.md). Load-bearing anchors:

- **`mlfinlab`** ([GitHub](https://github.com/hudson-and-thames/mlfinlab)) — reference implementation of Lopez de Prado's AFML algorithms (`BacktestStatistics`, PBO, CSCV); the operational backbone.
- **`scipy.stats`** + **`statsmodels.stats.multitest`** — power calculations and Bonferroni / Holm / FDR-BH corrections.
- **Bailey & López de Prado (2014)**, "The Deflated Sharpe Ratio" — the headline metric this skill enforces.
- **López de Prado (2018)**, *Advances in Financial Machine Learning*, ch. 11-14 — overfitting, DSR, PBO.

Links last cross-checked 2026-05-20.
