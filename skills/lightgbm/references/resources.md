# LightGBM — References & Further Reading

## Primary library
- [microsoft/LightGBM](https://github.com/microsoft/LightGBM) — upstream repo (issues, releases, C++ / Python / R / CLI all live here)
- [LightGBM docs (latest)](https://lightgbm.readthedocs.io/en/latest/) — cross-checked against the latest channel
- [Installation guide](https://lightgbm.readthedocs.io/en/latest/Installation-Guide.html) — covers wheel install, OpenCL GPU build, CUDA build, MPI build
- [`examples/` directory](https://github.com/microsoft/LightGBM/tree/master/examples) — runnable Python / R / C / CLI examples
- [Release notes](https://github.com/microsoft/LightGBM/releases) — read before pinning across 3.x → 4.x (categorical handling defaults shifted)

## Deep-dive docs (specific pages worth bookmarking)
- [Python API reference](https://lightgbm.readthedocs.io/en/latest/Python-API.html) — `Dataset`, `train`, `Booster`, callbacks, plotting
- [Python intro tutorial](https://lightgbm.readthedocs.io/en/latest/Python-Intro.html) — minimal working pattern (train/eval/predict)
- [sklearn API (`LGBMClassifier`, `LGBMRegressor`, `LGBMRanker`)](https://lightgbm.readthedocs.io/en/latest/Python-API.html#scikit-learn-api) — the API most production code uses
- [Parameters reference](https://lightgbm.readthedocs.io/en/latest/Parameters.html) — exhaustive list (`num_leaves`, `min_data_in_leaf`, `feature_fraction`, `bagging_fraction`, etc.)
- [Parameters tuning guide](https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html) — practical advice — "better accuracy" / "faster speed" / "deal with over-fitting" branches
- [GPU tutorial](https://lightgbm.readthedocs.io/en/latest/GPU-Tutorial.html) — OpenCL GPU build; covers per-board tuning
- [CUDA build](https://lightgbm.readthedocs.io/en/latest/GPU-Performance.html) — `device_type=cuda` separate from OpenCL; better on modern NVIDIA boards
- [Distributed Learning](https://lightgbm.readthedocs.io/en/latest/Parallel-Learning-Guide.html) — feature/data/voting parallel via MPI, Dask, Spark, Ray
- [Advanced Topics](https://lightgbm.readthedocs.io/en/latest/Advanced-Topics.html) — categorical-feature handling, monotonic / interaction constraints, custom objective, missing-value semantics
- [Features overview](https://lightgbm.readthedocs.io/en/latest/Features.html) — leaf-wise (vs level-wise) tree growth, GOSS, EFB — the algorithmic choices that distinguish it from XGBoost

## Adjacent / alternative libraries
- `xgboost` — see [`xgboost` skill](../../xgboost/SKILL.md) — broader ecosystem, more mature distributed story
- `catboost` — see [`catboost` skill](../../catboost/SKILL.md) — strongest defaults, best categorical handling, symmetric-tree predictor is fastest at inference
- [scikit-learn `HistGradientBoostingClassifier` / `Regressor`](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting) — inspired by LightGBM, no extra install
- [`treelite`](https://github.com/dmlc/treelite) — compile LightGBM trees to native code for low-latency serving

## Academic papers
- Ke, G., Meng, Q., Finley, T. et al. (2017). "LightGBM: A Highly Efficient Gradient Boosting Decision Tree." *NeurIPS 2017*. [paper PDF](https://proceedings.neurips.cc/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf) — introduces GOSS (gradient-based one-side sampling) and EFB (exclusive feature bundling), the two reasons LightGBM beats vanilla GBDT on speed
- Friedman, J. H. (2001). "Greedy Function Approximation: A Gradient Boosting Machine." *Annals of Statistics* 29(5), 1189–1232. [doi:10.1214/aos/1013203451](https://doi.org/10.1214/aos/1013203451) — the GBM foundation

## Tutorials & write-ups
- [Microsoft Research blog on GOSS + EFB](https://www.microsoft.com/en-us/research/blog/lightgbm-3-now-available/) — accessible summary of the speed claims
- [LightGBM in Kaggle Learn](https://www.kaggle.com/learn/intermediate-machine-learning) — practical tuning patterns common in Kaggle quant comps

## Last cross-checked
2026-05-20 — via Context7 `/lightgbm-org/lightgbm` + upstream docs at `lightgbm.readthedocs.io/en/latest/`; Auggie not indexed for this repo.
