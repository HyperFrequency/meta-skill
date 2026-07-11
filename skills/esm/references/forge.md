# Forge API Reference

Forge is EvolutionaryScale's hosted inference platform. Use it when you need
models that are not distributed as open weights (7B / 98B ESM3, `esmc-6b`), have
no local GPU, or want to fan out many generations concurrently. The Forge client
implements the same `ESM3InferenceClient` interface as the local model, so
generation code written against a local model runs unchanged against Forge.

## Setup

Get a token from https://forge.evolutionaryscale.ai. **Never hard-code it** —
read it from the environment or a secrets manager.

```python
import os
from esm.sdk.forge import ESM3ForgeInferenceClient
from esm.sdk.api import ESMProtein, GenerationConfig

client = ESM3ForgeInferenceClient(
    model="esm3-medium-2024-08",
    url="https://forge.evolutionaryscale.ai",
    token=os.environ["ESM_API_KEY"],
)

result = client.generate(
    ESMProtein(sequence="MPRT___KEND"),
    GenerationConfig(track="sequence", num_steps=8),
)
```

An analogous `ESMCForgeInferenceClient` serves ESM C embedding models
(including `esmc-6b`) with the same `encode` + `logits` flow as the local ESM C
model — see `esmc-embeddings.md`.

## Models

| Model ID | Params | Use |
|----------|--------|-----|
| `esm3-small-2024-08` | 1.4B | Fast prototyping |
| `esm3-medium-2024-08` | 7B | Production default |
| `esm3-large-2024-03` | 98B | Highest quality |
| `esm3-medium-multimer-2024-09` | 7B | Complexes (experimental) |

Model IDs are versioned by date and change over time; confirm the current list
from the Forge dashboard.

## Concurrency

For many independent generations, dispatch the synchronous `generate` calls
across threads with `asyncio` and bound the fan-out with a semaphore to respect
rate limits. This wraps the confirmed synchronous API and does not depend on any
particular async method name.

```python
import asyncio

async def generate_all(client, proteins, config, max_concurrent=8):
    limiter = asyncio.Semaphore(max_concurrent)

    async def one(protein):
        async with limiter:
            return await asyncio.to_thread(client.generate, protein, config)

    return await asyncio.gather(*(one(p) for p in proteins))

proteins = [ESMProtein(sequence=f"MPRT{'_' * 50}KEND") for _ in range(100)]
config = GenerationConfig(track="sequence", num_steps=25)
results = asyncio.run(generate_all(client, proteins, config))
```

If your installed SDK exposes native async batch helpers, prefer them; check the
`esm.sdk.forge` module for the version you have installed rather than assuming a
specific class or method name.

## Rate limits and retries

Forge enforces per-account request/concurrency limits and returns HTTP 429 when
exceeded. Wrap calls in exponential backoff:

```python
import time
from requests.exceptions import HTTPError

def generate_with_retry(client, protein, config, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.generate(protein, config)
        except HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)   # backoff
                continue
            raise
    raise RuntimeError("max retries exceeded")
```

Common status codes: `401` invalid token, `429` rate limited, `500` transient
server error (safe to retry). Also handle `ConnectionError` and `Timeout`.

## Checkpoint long batch jobs

For large batches, persist completed results incrementally so an interruption
does not force a full re-run — skip inputs already present in the checkpoint and
save every N items.

```python
import pickle, os

def run_checkpointed(client, proteins, config, path="checkpoint.pkl", every=10):
    done = pickle.load(open(path, "rb")) if os.path.exists(path) else {}
    for i, protein in enumerate(proteins):
        if i in done:
            continue
        done[i] = client.generate(protein, config)
        if i % every == 0:
            pickle.dump(done, open(path, "wb"))
    pickle.dump(done, open(path, "wb"))
    return done
```

## Cost control

- Prototype on `esm3-small-2024-08`; reserve `esm3-large-2024-03` for final runs.
- Cache results keyed on `(sequence, str(config))` — identical requests are
  deterministic wastes of quota.
- Sort and group work by sequence length to reduce padding overhead.

## Dedicated infrastructure

For data-residency or unbounded-throughput needs, ESM3 can be deployed on AWS
SageMaker (marketplace endpoint or Batch Transform) so inference stays inside
your own account. Contact EvolutionaryScale for enterprise licensing.
