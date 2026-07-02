---
name: auto-ML-FE-HFT
version: 0.1.0
description: Guided, opinionated router for AutoML, automated feature extraction, and HFT-specific indicators on price-feed data. Use when the user has tick / bar / L2 data and asks "what model should I train", "which features should I extract", "should I use deep learning here", "run AutoML on this price series", or names any of `h2o`, `autogluon`, `flaml`, `tpot`, `pycaret`, `tsfresh`, `featuretools`, `autofeat`, `mlfinlab`, `pandas-ta`, `ta-lib`, `finta`. Covers framework selection (H2O AutoML, AutoGluon, FLAML, TPOT, PyCaret), automated feature extraction (tsfresh, featuretools, autofeat), HFT indicator catalogue (realized vol, OFI, VPIN, Kyle's lambda, Hasbrouck, Hawkes, Roll, Amihud), pattern recognition (CNN, Transformer, anomaly, regime clustering, TDA), per-scenario NN recipes, and a decision tree for when DL beats boosting. Do NOT use for pure microstructure derivation, hand-tuning one learner, hypothesis design, or post-fit evaluation rigour — those have dedicated sibling skills.
allowed-tools: Read, Write, Edit, Bash, Skill
license: HyperFrequency original
metadata:
    skill-author: HyperFrequency
    style: opinionated playbook with code
---

# Auto-ML + Automated Feature Extraction + HFT Indicator Catalogue

Opinionated walkthrough for "I have a price feed, what do I model and how". Picks an AutoML framework, runs automated FE on tick/bar/L2 data, surfaces the right HFT indicators, and tells you when DL is worth the GPU and when a boosted tree dominates. Grounded against canonical references and cross-linked to sibling skills rather than duplicating their math.

This SKILL.md is a **router**: it routes you to one of six reference files in `references/`. Sections labelled **Recommendation** are author's call; **Fact** cites a paper.

## When to use

Use when you have tick / bar / L2 data and need to pick model class + feature set in one pass; want AutoML rather than hand-tuning; want automated feature extraction over raw tape; need a sober opinion on whether DL will beat XGBoost/LightGBM/CatBoost; need an HFT indicator catalogue with code; or want pattern-recognition in an automated pipeline.

Do **not** use for: pure microstructure derivation (`microstructure-analysis`); hand-tuning one learner (`xgboost` / `lightgbm` / `catboost` / `cnn-pattern-recognition`); hypothesis design (`ml-hypothesis-design` first); post-fit evaluation rigour (`model-evaluation`).

## Required tooling — gateway contract

Standard neuro-harness toolchain: Python 3.11+ in a `uv`-managed venv (pin via `uv-mcp`), Pandas/NumPy/pyarrow + parquet, scikit-learn 1.4+, Optuna for manual tuning, SHAP for interpretability (use the `shap` skill), and one of MLflow or W&B for tracking (don't mix).

Every production artefact must include: (1) a pinned lockfile (`uv pip compile`), (2) seeded randomness (`random_state=42` everywhere), (3) the feature matrix as parquet with a hash-stamped filename, (4) a Markdown experiment summary alongside the model artefact (see `references/discipline-example-references.md` §G).

## Routing map — load the reference you need

Read the matching file under `references/` for the full detail and runnable code. Don't read all six; pick by task.

| If the task is…                                                              | Read this reference |
|------------------------------------------------------------------------------|---------------------|
| Pick / run an AutoML framework (H2O, AutoGluon, FLAML, TPOT, PyCaret) + matrix | [`references/automl-frameworks.md`](references/automl-frameworks.md) |
| Automated feature extraction (tsfresh, featuretools, autofeat), indicator libs (ta-lib/pandas-ta/finta/mlfinlab), feature selection (BorutaPy/mRMR/SHAP) | [`references/feature-extraction.md`](references/feature-extraction.md) |
| HFT indicator catalogue with code (realized vol+bipower, spreads, trade-sign ACF, Roll, Amihud, realized skew/kurt) + cross-links (VPIN, OFI, Kyle, Hasbrouck, Hawkes) | [`references/hft-indicators.md`](references/hft-indicators.md) |
| Pattern recognition (CNN charts, Transformer sequences, anomaly detection, regime clustering, TDA) | [`references/pattern-recognition.md`](references/pattern-recognition.md) |
| Per-scenario NN training recipes (E.1–E.10) and the **DL-vs-boosting decision tree** (Q1–Q8) | [`references/nn-training-and-dl-decision.md`](references/nn-training-and-dl-decision.md) |
| Documentation discipline (preregistration, eval rigor, experiment summary, reproducibility), the **end-to-end worked example**, common pitfalls, full bibliography | [`references/discipline-example-references.md`](references/discipline-example-references.md) |

## The 30-second decision

1. **Have ≤1M tabular rows?** → Boosting (XGBoost / LightGBM / CatBoost). Skip DL. Spend time on features (Borisov 2022; Shwartz-Ziv 2021). Heavy categoricals (symbol/venue) → **CatBoost**.
2. **Want a fast AutoML baseline?** → FLAML (≤5 min CPU), then H2O AutoML / AutoGluon for the production candidate. The leader is almost always a boosted tree → hand off to the `catboost`/`lightgbm`/`xgboost` skill.
3. **Need features over raw tape?** → tsfresh (univariate price), featuretools (relational/multi-venue panels), autofeat (non-linear interactions); microstructure columns come from `microstructure-analysis`. Prune with mRMR → BorutaPy.
4. **Tempted by deep learning?** → Walk the Q1–Q8 decision tree in `references/nn-training-and-dl-decision.md`. Default to boosting; earn the right to use DL with a quantified accuracy gap.
5. **Always** preregister the hypothesis, do walk-forward OOS (`model-evaluation`), and commit the experiment summary.

## Cross-linked sibling skills

`microstructure-analysis` (OFI/VPIN/Kyle/trade classification), `feature-engineering` (leakage-safe pipelines, triple-barrier), `xgboost`/`lightgbm`/`catboost`, `cnn-pattern-recognition`, `wavelet-decomposition`, `markov-regime-detection`, `autoencoder-anomaly-detection`, `model-evaluation` (walk-forward, PBO, DSR), `ml-hypothesis-design`, `deep-q-learning`/`policy-gradients`, `garch-volatility`, `tearsheet-generator`, `uv-mcp`. Hawkes is owned by `microstructure-analyst` §C.Hawkes and `microstructure-feature-engineering` — no standalone `hawkes-process` skill.
