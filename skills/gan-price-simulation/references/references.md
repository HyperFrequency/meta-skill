# References

## Primary library
- [eriklindernoren/PyTorch-GAN](https://github.com/eriklindernoren/PyTorch-GAN) — the reference repository for vanilla GAN, DCGAN, WGAN, WGAN-GP, CGAN, CycleGAN; the patterns this skill ports
- [eriklindernoren/Keras-GAN](https://github.com/eriklindernoren/Keras-GAN) — same algorithms in Keras; useful for cross-framework reading
- [jsyoon0823/TimeGAN](https://github.com/jsyoon0823/TimeGAN) — the original TimeGAN repo (TF 1.x); read for the three-phase training schedule
- [ydataai/ydata-synthetic](https://github.com/ydataai/ydata-synthetic) — maintained Python library that wraps TimeGAN + several other generators; PyTorch-friendly
- [birdx0810/timegan-pytorch](https://github.com/birdx0810/timegan-pytorch) — unofficial PyTorch port of TimeGAN; read the code before trusting outputs
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — for the hand-rolled training loops

## Deep-dive docs (specific pages worth bookmarking)
- [PyTorch `torch.nn.BCEWithLogitsLoss`](https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html) — the numerically-stable replacement for `BCELoss` + sigmoid; should be the default
- [PyTorch `torch.optim.Adam`](https://pytorch.org/docs/stable/generated/torch.optim.Adam.html) — covers the `betas=(0.5, 0.999)` recipe; the lone optimizer config most GAN papers settle on
- [PyTorch-GAN: WGAN-GP implementation](https://github.com/eriklindernoren/PyTorch-GAN/blob/master/implementations/wgan_gp/wgan_gp.py) — the gradient-penalty trick worth copying line for line when vanilla BCE training is unstable
- [TimeGAN supplementary material (van der Schaar lab)](https://www.vanderschaar-lab.com/papers/NIPS2019_TGAN_Supplementary.pdf) — the math of the embedder/recovery/supervisor losses; the gap between the paper and the code
- [statsmodels `tsa.stattools.acf`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.acf.html) — used in the evaluation checklist; computes ACF and confidence bands

## Adjacent / alternative libraries
- [Synthcity](https://github.com/vanderschaarlab/synthcity) — the van der Schaar lab's broader synthetic data library; TimeGAN, DoppelGANger, GoggleGAN under one API
- [PyTorch Lightning Bolts](https://github.com/Lightning-Universe/lightning-bolts) — pre-built `LitGAN` / `LitDCGAN` modules
- [HuggingFace diffusers](https://github.com/huggingface/diffusers) — denoising diffusion alternative to GANs; more stable, higher-quality samples; relevant when GAN training keeps failing
- [PyOD's `MO_GAAL`](https://github.com/yzhao062/pyod/blob/master/pyod/models/mo_gaal.py) — multi-generator GAN repurposed as anomaly detector; pairs with `autoencoder-anomaly-detection` skill
- [DoppelGANger](https://github.com/fjxmlzn/DoppelGANger) — purpose-built for time series with metadata; an alternative to TimeGAN when conditional generation matters

## Academic papers
- Goodfellow, I., Pouget-Abadie, J., Mirza, M., Xu, B., Warde-Farley, D., Ozair, S., Courville, A., & Bengio, Y. (2014). "Generative Adversarial Nets." *NeurIPS 2014*. [arXiv:1406.2661](https://arxiv.org/abs/1406.2661) — the original GAN paper.
- Radford, A., Metz, L., & Chintala, S. (2016). "Unsupervised Representation Learning with Deep Convolutional Generative Adversarial Networks (DCGAN)." *ICLR 2016*. [arXiv:1511.06434](https://arxiv.org/abs/1511.06434) — the `lr=2e-4, betas=(0.5, 0.999)` recipe + architectural guidelines.
- Salimans, T., Goodfellow, I., Zaremba, W., Cheung, V., Radford, A., & Chen, X. (2016). "Improved Techniques for Training GANs." *NeurIPS 2016*. [arXiv:1606.03498](https://arxiv.org/abs/1606.03498) — instance noise, feature matching, minibatch discrimination, virtual batch norm.
- Arjovsky, M., Chintala, S., & Bottou, L. (2017). "Wasserstein GAN." [arXiv:1701.07875](https://arxiv.org/abs/1701.07875) — the loss change that single-handedly fixes most vanilla-GAN instability.
- Gulrajani, I., Ahmed, F., Arjovsky, M., Dumoulin, V., & Courville, A. (2017). "Improved Training of Wasserstein GANs." *NeurIPS 2017*. [arXiv:1704.00028](https://arxiv.org/abs/1704.00028) — WGAN-GP; the gradient penalty variant that's the practical default now.
- Yoon, J., Jarrett, D., & van der Schaar, M. (2019). "Time-series Generative Adversarial Networks." *NeurIPS 2019*. [NIPS paper page](https://papers.nips.cc/paper/8789-time-series-generative-adversarial-networks) — TimeGAN; the embedder/recovery/supervisor architecture.
- Heusel, M., Ramsauer, H., Unterthiner, T., Nessler, B., & Hochreiter, S. (2017). "GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium." *NeurIPS 2017*. [arXiv:1706.08500](https://arxiv.org/abs/1706.08500) — TTUR + FID metric; the standard convergence-acceleration trick.

## Tutorials & write-ups
- [PyTorch DCGAN tutorial](https://pytorch.org/tutorials/beginner/dcgan_faces_tutorial.html) — the official walkthrough this skill's minimal example follows
- [Machine Learning for Trading (Jansen) — synthetic time series with GANs](https://stefan-jansen.github.io/machine-learning-for-trading/21_gans_for_synthetic_time_series/) — Stefan Jansen's chapter showing TimeGAN on financial returns end to end
- [TimeGAN reproducibility study (Hagner et al.)](https://arxiv.org/abs/2102.12001) — independent reproduction; useful failure-mode catalogue

## Standard datasets / benchmarks
- Stock daily returns from `yfinance` (any ticker, 5+ years) — the standard reproducibility setup; train on years 1-3, evaluate marginal moments and ACF on years 4-5
- Sines + autoregressive synthetic data from the TimeGAN repo — the "definitely works" sanity check
- UCI HEPMASS / energy / quark-gluon datasets — non-finance benchmarks the TimeGAN paper uses; if your model fails on these, the bug is implementation not data

## Last cross-checked
2026-05-20 — via Context7 `/pytorch/pytorch` + WebSearch verification of all paper arXiv IDs / NeurIPS URLs.
