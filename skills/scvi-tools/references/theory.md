# Theoretical foundations

Why scvi-tools models look the way they do: variational inference, the VAE, count
likelihoods, the batch-correction formulation, and the Bayesian DE machinery.

## Variational inference and the ELBO

We want the posterior `p(z | x)` — latent cell state `z` given counts `x` — but it
is intractable. Variational inference posits a tractable family `q(z | x)` and
fits it by maximizing the Evidence Lower Bound:

```
ELBO = E_q[ log p(x | z) ]  −  KL( q(z | x) || p(z) )
       └ reconstruction ┘      └ regularization ┘
```

The reconstruction term rewards generating data like the observations; the KL
term pulls the latent toward the prior `p(z) = N(0, I)`. Maximizing the ELBO is
equivalent to minimizing `KL(q || p(z|x))`. This scales to millions of cells and
yields uncertainty, unlike exact Bayesian inference.

## The variational autoencoder

```
x ──[encoder qφ]──► z ──[decoder pθ]──► x̂
```

- **Encoder** `q(z|x)` outputs the mean and variance of the latent Gaussian.
- **Decoder** `p(x|z)` outputs the parameters of a *count* likelihood.
- **Reparameterization** `z = μ + σ ⊙ ε`, `ε ~ N(0,I)`, lets gradients flow
  through the stochastic sample so the whole thing trains by SGD (Adam,
  lr ≈ 1e-3), typically 200-500 epochs with KL annealing and early stopping.

**Amortized inference** is the key scalability trick: one encoder network is
shared across all cells (fixed parameter count regardless of cell number), rather
than per-cell latent variables. This also enables fast inference on new/query
cells.

## Count likelihoods

Single-cell counts are integer and overdispersed, so the decoder emits a count
distribution, not a Gaussian:

- **Negative binomial (NB)**: `x ~ NB(μ, θ)`, variance `μ + μ²/θ`. Overdispersion
  via dispersion `θ`. The common default.
- **Zero-inflated NB (ZINB)**: `π·δ₀ + (1−π)·NB(μ, θ)`. Adds dropout probability
  `π` for a technical zero mass. Fits very sparse 10x data; NB is often preferred
  when data are less sparse.
- **Poisson**: `x ~ Poisson(μ)`, variance = mean. Simple and fast; used for ATAC
  fragment counts (PoissonVI).

## Batch correction

Technical variation (runs, protocols, labs) confounds biology. scvi-tools encodes
batch `s` as a covariate and threads it through the **decoder**, not the latent:

```
encoder:  q(z | x, s)     decoder:  p(x | z, s)
```

The latent `z` becomes batch-invariant (biology) while `s` explains technical
effects at reconstruction time. Continuous covariates (percent-mito, library
size) are standardized; categorical covariates (batch, donor) are one-hot encoded
and either concatenated to `z` or deeply injected at multiple decoder layers.
This same conditioning enables **counterfactuals** — re-decode `z` under a
different `s` (e.g. "this cell in another batch").

## Transfer learning (scArches)

A reference model's encoder learns general cellular structure. For a query,
freeze the shared weights and add/fine-tune a small set of query-specific nodes.
This maps new data onto the reference latent without recomputing the reference or
forgetting it — enabling few-shot analysis of rare types and atlas-scale
annotation.

## Multi-resolution modeling (MrVI)

Hierarchical latent: a sample-level effect `ρ_s ~ N(0, I)` and a cell-level
`z_i ~ N(ρ_{s(i)}, σ²)`. This disentangles shared from sample-specific variation
so you can compare samples (disease vs healthy, donor effects) at cell
resolution.

## Bayesian differential expression

Rather than compare point estimates, scvi-tools contrasts posterior expression
distributions:

- Sample `μ_A ~ p(μ | x_A)` and `μ_B ~ p(μ | x_B)`; the log fold-change
  `β = log μ_B − log μ_A` gets a full posterior, quantifying uncertainty.
- **Bayes factor** ranks evidence for DE: BF > 3 moderate, > 10 strong, > 100
  decisive.
- **False Discovery Proportion (FDP)** control: rank genes by evidence and take
  the largest set with posterior expected FDP ≤ α — fully Bayesian, no p-value
  thresholds or pseudocounts.

See `differential-expression.md` for the practical API.

## How scVI compares

- **vs PCA** — nonlinear and probabilistic, models counts natively (PCA is
  linear and Gaussian).
- **vs t-SNE / UMAP** — a full generative model, not just a 2-D embedding;
  supports DE, imputation, counterfactuals. (You still run UMAP *on* the scVI
  latent for visualization.)
- **vs Harmony** — Harmony corrects PCA coordinates post-hoc; scVI is a VAE that
  handles counts and yields a generative model.
- **vs Seurat integration** — anchor-based alignment vs probabilistic modeling;
  scVI provides uncertainty and scales to many batches.

## Key references

- Lopez et al. 2018 — "Deep generative modeling for single-cell transcriptomics"
  (scVI).
- Xu et al. 2021 — "Probabilistic harmonization and annotation of single-cell
  transcriptomics" (scANVI).
- Boyeau et al. 2019 — differential expression in single cells.
- Gayoso et al. 2022 — "A Python library for probabilistic analysis of
  single-cell omics data" (the scvi-tools framework).
