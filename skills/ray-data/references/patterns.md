# Ray Data Patterns & Performance

Common production patterns, tuning knobs, and reference benchmarks.

## Batch inference

Use a callable class so the model loads once per worker (in `__init__`) rather
than once per batch:

```python
import ray

class BatchInference:
    def __init__(self):
        self.model = load_model()  # loaded once per worker

    def __call__(self, batch):
        predictions = self.model(batch["input"])
        return {"prediction": predictions}

ds = ray.data.read_parquet("s3://data/")
predictions = ds.map_batches(
    BatchInference,
    batch_size=32,
    num_gpus=1,           # one GPU per worker
    concurrency=4,        # number of worker actors
)
predictions.write_parquet("s3://output/")
```

## Multi-step preprocessing pipeline

Chained transforms fuse into a single streamed execution plan:

```python
ds = (
    ray.data.read_parquet("s3://raw/")
    .map_batches(clean_data)
    .map_batches(tokenize)
    .map_batches(augment)
    .write_parquet("s3://processed/")
)
```

## Performance tuning

### Repartition
```python
ds = ds.repartition(100)  # ~match block count to total cluster cores
```

### Batch size
Larger batches amortize per-call overhead and speed up vectorized ops; balance
against worker memory.
```python
ds.map_batches(process_fn, batch_size=10000)  # vs batch_size=100
```

### Tips
1. Prefer `map_batches` over `map` — 10-100x faster (vectorized).
2. Use `num_gpus`/`concurrency` on `map_batches` for GPU and actor pooling.
3. Stream large datasets with `iter_batches`; never `take_all()` on big data.
4. Cache expensive preprocessing to Parquet, then read in training.

## Reference benchmarks

Indicative only — actual numbers depend on hardware, I/O, and transform cost.

**Scaling (100GB processing):**
- 1 node (16 cores): ~30 min
- 4 nodes (64 cores): ~8 min
- 16 nodes (256 cores): ~2 min

**GPU acceleration (image preprocessing):**
- CPU only: ~1,000 images/sec
- 1 GPU: ~5,000 images/sec
- 4 GPUs: ~18,000 images/sec

## Production users

- Pinterest — last-mile data processing for model training
- ByteDance — offline inference with multi-modal LLMs
- Spotify — ML platform batch inference
