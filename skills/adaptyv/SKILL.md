---
name: adaptyv
version: 0.1.0
description: >-
  Adaptyv is a cloud wet-lab that runs automated protein assays — binding (BLI
  kinetics), expression yield, thermostability, and enzyme activity — so you can
  experimentally validate computationally designed proteins instead of trusting
  predictions. Use when you have candidate protein or antibody sequences and need
  real measurements: submitting sequences via API, tracking experiment status
  (webhook or polling), downloading structured kinetic/expression/stability
  results, or computationally pre-screening and redesigning sequences (NetSolP,
  SoluProt, SolubleMPNN, ESM likelihood, ipTM, hydrophobic-exposure) so you only
  pay to test candidates that will actually express. Do NOT use for pure in-silico
  structure/binder prediction with no wet-lab intent, for small-molecule or
  non-protein assays, for generic ML training, or when you need results in
  minutes — turnaround is on the order of weeks.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "N/A — Adaptyv is a proprietary hosted wet-lab service; the pre-screening tools referenced carry their own licenses (ESM MIT, ProteinMPNN/SolubleMPNN MIT, NetSolP/SoluProt academic web services)"
---

# Adaptyv — Cloud Wet-Lab Protein Validation

## Overview

Adaptyv Bio runs a fully automated cloud laboratory: submit protein sequences and it
expresses, purifies, and assays them, returning quantitative wet-lab measurements. It
closes the loop for computational protein design — a model proposes sequences, Adaptyv
tells you which ones actually fold, express, bind, and stay stable. Turnaround is on the
order of weeks (the upstream source quotes ~21 days), and the service targets
high-throughput, ML-driven campaigns where you screen many variants per round.

This skill is a router. It gives you the design→validate loop, the assay menu, and the API
surface at a glance, and delegates depth to `references/`.

Adaptyv is a commercial, third-party service that has run its API in an alpha/beta phase.
Treat the endpoint shapes in this skill as illustrative and confirm the live API with the
vendor before building against it — see [references/api.md](references/api.md).

## When to Use This Skill

- You have designed or mutated protein/antibody sequences and need experimental validation, not just predictions.
- You want binding (BLI kinetics: KD/kon/koff), expression yield, thermostability (Tm), or enzyme-activity (kcat/KM) measurements.
- You need to submit an experiment via API, poll or webhook its status, and download structured results.
- You run iterative design rounds and want to computationally pre-screen candidates (solubility, expressibility, interface confidence) so wet-lab budget only goes to sequences likely to express.
- You are wiring Adaptyv results back into a model-in-the-loop autoresearch pipeline.

## When NOT to Use This Skill

- You only need in-silico structure or binder prediction with no wet-lab intent — use structure/design tools directly (discover models via `hugging-science`).
- Your target is not a protein expressible from sequence (small molecules, nucleic-acid-only assays, cell-based phenotypic screens).
- You need results in minutes or hours — Adaptyv turnaround is weeks.
- You just want to train or fine-tune an ML model — this is wet-lab validation, not compute.

## Setup

The API is access-gated (request access from the vendor). Authenticate with a bearer token
supplied via environment variable — never hard-code or commit it.

```bash
export ADAPTYV_API_KEY="…"          # request access from Adaptyv; keep out of version control
uv pip install requests python-dotenv
```

```bash
# Verify it is set without printing the value
python -c "import os; assert os.getenv('ADAPTYV_API_KEY'), 'ADAPTYV_API_KEY not set'"
```

Auth scheme, base URL, and endpoint detail — with the alpha/beta caveat — live in
[references/api.md](references/api.md).

## The design → validate loop

The value here is the loop, not any single call. Wet-lab cycles are slow and metered, so
front-load computation:

1. Generate/mutate candidate sequences with your design model.
2. **Pre-screen in silico** — filter for solubility/expressibility and interface confidence; redesign the borderline ones. Cheap, and it kills likely failures before they cost lab time. See [references/sequence-optimization.md](references/sequence-optimization.md).
3. **Submit the survivors** as a batch experiment; always include a wild-type / known-good control.
4. **Track** via webhook (preferred) or polling.
5. **Download, rank, iterate** — feed the measurements back into the next design round.

## Capability Map

| Area | What it covers | Reference |
| --- | --- | --- |
| **Assay menu** | Binding (BLI), expression, thermostability, enzyme activity — parameters, workflows, sample needs, timelines, combining assays | [references/experiments.md](references/experiments.md) |
| **API surface** | Auth, endpoints (create/status/list/results, targets, credits), webhooks, errors, rate limits, stability caveats | [references/api.md](references/api.md) |
| **Pre-submission optimization** | Solubility/expression screening and redesign (NetSolP, SoluProt, SolubleMPNN, ESM likelihood, ipTM, hydrophobic exposure), staged pipeline | [references/sequence-optimization.md](references/sequence-optimization.md) |
| **Code recipes** | Submit single/batch, webhook vs poll, download + parse binding/expression results into DataFrames, retry/backoff, FASTA validation | [references/examples.md](references/examples.md) |

## Assay menu at a glance

- **Binding (BLI)** → label-free kinetics: KD, kon, koff, with confidence/R².
- **Expression** → yield (mg/L), soluble fraction, purity across host systems (E. coli, mammalian, yeast, insect).
- **Thermostability** → melting temperature Tm, aggregation temperature, reversibility (DSF / CD).
- **Enzyme activity** → kcat, KM, kcat/KM, IC50, specific activity (Michaelis-Menten fitting).

Match assays to the goal (affinity vs manufacturability vs formulation stability). Run them
sequentially to filter cheaply first, or in parallel for the fastest turnaround. Result
schemas and per-stage timelines: [references/experiments.md](references/experiments.md).

## Pre-submission optimization (short version)

The common failure modes are unpaired cysteines (spurious disulfides), long hydrophobic
patches (aggregation), and poor predicted solubility. Address them before you submit:

- **Fast filter** — solubility prediction (NetSolP / SoluProt) to drop obvious losers.
- **Redesign** — SolubleMPNN to propose more soluble sequences while preserving structure; keep functional residues fixed.
- **Sanity-rank** — ESM sequence likelihood to avoid unnatural mutations; interface confidence (ipTM from AlphaFold-Multimer) for binders; solvent-accessible hydrophobic exposure for aggregation risk.

These are separate third-party tools with their own installs and licenses — do not assume
one package covers them. Capability descriptions, an accurate ESM scoring example, and a
staged pipeline are in
[references/sequence-optimization.md](references/sequence-optimization.md). Pull ESM and
design-model weights via `hugging-science`.

## Notes on API stability

- The platform has run in alpha/beta; not every lab capability is exposed via API, and endpoint/payload shapes may change. Confirm against current vendor docs.
- Prefer webhooks over long polling — experiments take weeks, not seconds.
- Validate FASTA locally, batch submissions, watch the credit balance, and use idempotent retry-with-backoff (a rate limit is enforced). See [references/examples.md](references/examples.md).
