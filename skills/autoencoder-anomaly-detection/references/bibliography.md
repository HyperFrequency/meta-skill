# References & bibliography

## Primary library
- [PyOD on GitHub](https://github.com/yzhao062/pyod) — upstream repo, issues, releases (v2.0+)
- [PyOD documentation](https://pyod.readthedocs.io/en/latest/) — pinned to v2.x for the snippets in this skill
- [PyOD examples directory](https://github.com/yzhao062/pyod/tree/master/examples) — `auto_encoder_example.py`, `vae_example.py`, `mo_gaal_example.py` — drop-in templates
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — for the hand-rolled section

## Deep-dive docs (specific pages worth bookmarking)
- [`AutoEncoder` model docs](https://pyod.readthedocs.io/en/latest/pyod.models.html#module-pyod.models.auto_encoder) — `hidden_neuron_list`, `epoch_num`, `dropout_rate`, `contamination`
- [`VAE` model docs](https://pyod.readthedocs.io/en/latest/pyod.models.html#module-pyod.models.vae) — `encoder_neuron_list`, `decoder_neuron_list`, `latent_dim`, `beta`; KL + reconstruction loss
- [`MO_GAAL` model docs](https://pyod.readthedocs.io/en/latest/pyod.models.html#module-pyod.models.mo_gaal) — `k` sub-generators against mode collapse; `lr_d` / `lr_g`
- [`AutoEncoder` source](https://github.com/yzhao062/pyod/blob/master/pyod/models/auto_encoder.py) — authoritative signature; API drifted v1 → v2
- [PyOD utility module](https://pyod.readthedocs.io/en/latest/pyod.utils.html) — `generate_data`, `evaluate_print` helpers
- [PyOD benchmarking guide](https://pyod.readthedocs.io/en/latest/benchmark.html) — `precision_n_scores` and standard ROC / AUPR / P@N evaluation

## Adjacent / alternative libraries
- [anomalib](https://github.com/openvinotoolkit/anomalib) — production-grade industrial anomaly detection; PaDiM, PatchCore, EfficientAD; same recon-error paradigm
- [TensorFlow autoencoder tutorial](https://www.tensorflow.org/tutorials/generative/autoencoder) — Keras-native AE anomaly detection
- [Alibi Detect](https://github.com/SeldonIO/alibi-detect) — anomaly + drift detection with VAE / Mahalanobis / KS test
- [DeepOD](https://github.com/xuhongzuo/DeepOD) — deep OD; broader algorithm coverage than PyOD's deep models alone
- [SUOD](https://github.com/yzhao062/SUOD) — ensemble PyOD detectors at scale

## Academic papers
- Kingma, D. P., & Welling, M. (2014). "Auto-Encoding Variational Bayes." *ICLR 2014*. [arXiv:1312.6114](https://arxiv.org/abs/1312.6114) — the VAE paper; the loss `VAE` implements.
- Liu, Y., et al. (2019). "Generative Adversarial Active Learning for Unsupervised Outlier Detection." *IEEE TKDE* 32(8), 1517-1528. [DOI: 10.1109/TKDE.2019.2905606](https://doi.org/10.1109/TKDE.2019.2905606) — the MO-GAAL / SO-GAAL paper.
- Sakurada, M., & Yairi, T. (2014). "Anomaly Detection Using Autoencoders with Nonlinear Dimensionality Reduction." *Proc. MLSDA 2014*. [DOI: 10.1145/2689746.2689747](https://doi.org/10.1145/2689746.2689747) — early AE-based anomaly detection.
- Zhao, Y., Nasrullah, Z., & Li, Z. (2019). "PyOD: A Python Toolbox for Scalable Outlier Detection." *JMLR* 20(96), 1-7. [JMLR](https://www.jmlr.org/papers/v20/19-011.html) — the PyOD library paper.
- Aggarwal, C. C. (2017). *Outlier Analysis* (2nd ed.). Springer. [DOI: 10.1007/978-3-319-47578-3](https://doi.org/10.1007/978-3-319-47578-3) — Ch. 3 (deep autoencoder section) is the textbook reference PyOD cites.
- Bengio, Y., et al. (2013). "Generalized Denoising Auto-Encoders as Generative Models." *NeurIPS 2013*. [arXiv:1305.6663](https://arxiv.org/abs/1305.6663) — the denoising trick.

## Tutorials & write-ups
- [Keras autoencoder anomaly detection (time series)](https://keras.io/examples/timeseries/timeseries_anomaly_detection/) — hand-rolled reference for time series
- [PyOD Compare All Models notebook](https://github.com/yzhao062/pyod/blob/master/notebooks/Compare%20All%20Models.ipynb) — AE vs IsolationForest / LOF / OCSVM
- [Anomaly Detection Resources (Zhao curated list)](https://github.com/yzhao062/anomaly-detection-resources) — broader bibliography PyOD draws from

## Standard datasets / benchmarks
- ODDS benchmark — [odds.cs.stonybrook.edu](http://odds.cs.stonybrook.edu/) — most-cited multivariate evaluation set
- KDD'99 / NSL-KDD — network intrusion detection; standard "deep AE works" benchmark
- Yahoo S5 time-series anomaly benchmark — [research.yahoo.com](https://yahooresearch.tumblr.com/post/114590420346/a-benchmark-dataset-for-time-series-anomaly) — labeled real + synthetic anomalies; closest to financial time-series setup

## Last cross-checked
- 2026-06-29 — PyOD v2.0+ `AutoEncoder` / `VAE` / `MO_GAAL` `__init__` signatures verified against upstream `master` source.
- 2026-05-20 — via Context7 `/yzhao062/pyod` (1252 snippets, High, benchmark 90.6) + WebSearch verification of all paper DOIs/arXiv IDs.
