# Chunking, Sharding, Compression, and Performance

The three levers that decide Zarr performance are **chunk shape**, **sharding**, and
**codec choice**. Get chunk shape right first — it dominates everything else.

## Sizing a Chunk

Target roughly **1-10 MB uncompressed per chunk**. Too small and per-chunk metadata and
decode overhead dominate; too large and every read pulls in data you didn't ask for and
must fit a whole chunk in memory to (de)compress.

```
bytes_per_chunk = product(chunk_shape) * itemsize
```

For `float32` (4 bytes): 1 MB ≈ 262,144 elements.

| Target | 2-D chunk | 3-D chunk |
|--------|-----------|-----------|
| ~1 MB  | (512, 512)      | (64, 64, 64) ≈ 1 MB |
| ~8 MB  | (1024, 1024) ≈ 4 MB | (128, 128, 128) ≈ 8 MB |
| ~16 MB | (2048, 1024) ≈ 8 MB | (64, 256, 256) ≈ 16 MB |

## Aligning Chunks with Access Patterns

A read fetches and decompresses **every chunk it overlaps**, so the chunk grid must
match how you slice. This matters far more than raw chunk size.

```python
# Frequent row reads (index the first axis) -> make chunks span columns
chunks=(10, 10_000)

# Frequent column reads (index the second axis) -> make chunks span rows
chunks=(10_000, 10)

# Random / mixed access -> balanced square chunks
chunks=(1_000, 1_000)

# Time series appended and read one step at a time -> one step per chunk
chunks=(1, 720, 1_440)     # shape (time, lat, lon)

# Isotropic 3-D volumes accessed from any direction -> cubic chunks
chunks=(64, 64, 64)
```

Concrete cost: for a `(200, 200, 200)` array, reading a slab along the first axis is
tens of times faster with chunks `(200, 200, 1)` than with `(1, 200, 200)`, because the
first layout keeps each slab contiguous within few chunks while the second forces a read
of essentially every chunk.

## Sharding (v3)

A well-chosen chunk size sometimes implies millions of chunks, and one-file-per-chunk
stores buckle under that many objects (filesystem inode pressure, per-object cloud
request cost, block-size waste). Sharding groups many chunks into a single storage
object while keeping the chunk as the read/decode unit.

```python
z = zarr.create_array(
    store="data/big.zarr",
    shape=(100_000, 100_000),
    chunks=(256, 256),      # still the granularity of a read
    shards=(4096, 4096),    # one object holds a 16x16 grid of chunks
    dtype="float32",
)
```

`shards` must be a whole-number multiple of `chunks` along each axis. A whole shard is
assembled in memory before it is written, so keep shard size within available RAM.

## Compression / Codec Choice

Set compression with `compressors=` (see `api-reference.md` for the full codec list).

```python
# Fast, interactive: minimize CPU
compressors=zarr.codecs.BloscCodec(cname="lz4", clevel=1)

# Balanced default for numeric scientific data
compressors=zarr.codecs.BloscCodec(cname="zstd", clevel=5,
                                    shuffle=zarr.codecs.BloscShuffle.shuffle)

# Maximum ratio, cold/archival data
compressors=zarr.codecs.GzipCodec(level=9)

# No compression (already-compressed or incompressible data)
compressors=None
```

Guidance:

- **Blosc** (meta-compressor) is fast and the usual default; `zstd` inside it gives a
  strong ratio/speed balance, `lz4` maximizes speed.
- The **shuffle** filter (byte or bit shuffle) markedly improves ratio on numeric data
  by grouping like-significance bytes before compression.
- **Gzip** wins ratio but is CPU-heavy; reserve it for data written once and read rarely.
- Always confirm with `z.info_complete()` before committing at scale — the right codec
  depends on your data's entropy, not on defaults.

## Cloud Storage Tuning

- **Consolidate metadata**: `zarr.consolidate_metadata(store)` then
  `zarr.open_consolidated(store)` — turns N per-array metadata GETs into one. Biggest
  single win on high-latency object stores.
- **Larger chunks on the cloud**: request latency, not bandwidth, dominates. Chunks of
  ~5-100 MB amortize per-request overhead better than the 1 MB local sweet spot.
- **Shard** to cut object count and per-object request cost.
- **Parallelize** reads/writes with `dask` so many chunk requests overlap in flight.

## Diagnosing a Slow Array

```python
print(z.info)              # are chunks a sane size? is compression on?
print(z.info_complete())   # real stored size and compression ratio
print(z.chunks, z.shards)  # do they match the access pattern?
```

Checklist when a workload is slow:

1. **Chunk shape misaligned** with the slicing direction — the most common cause. Rewrite
   the array with chunks aligned to how you actually read it.
2. **Chunks too small** — merge toward 1-10 MB (local) or larger (cloud).
3. **Loading the whole array** (`z[:]`) instead of streaming — iterate chunk-aligned:

   ```python
   for i in range(0, z.shape[0], z.chunks[0]):
       block = z[i:i + z.chunks[0], :]
       process(block)
   ```
   or hand it to `dask` (`da.from_zarr(...).mean().compute()`) for automatic chunked,
   out-of-core execution.
4. **Cloud latency** — consolidate metadata, enlarge chunks, shard, parallelize.
5. **Codec mismatch** — an over-aggressive codec can make CPU the bottleneck; try a
   faster Blosc setting and re-measure.
