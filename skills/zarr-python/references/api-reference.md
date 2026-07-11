# Zarr v3 API Reference

Concise lookup for zarr-python 3.x. Everything here targets the v3 API (`import zarr`).
Where v2 differed, the v2 form is called out so you don't paste stale snippets.

## Installation

```bash
uv pip install "zarr>=3"
uv pip install s3fs    # S3 backend (via fsspec)
uv pip install gcsfs   # Google Cloud Storage backend
```

Requires Python 3.11+. Cloud backends are optional and pulled in on demand.

## Array Creation

### `zarr.create_array` — explicit control (preferred)

```python
zarr.create_array(
    store,                 # path str, Store, or cloud URL ("s3://...")
    *,
    shape,                 # tuple, e.g. (10_000, 10_000)
    dtype="float64",
    chunks="auto",         # tuple or "auto"
    shards=None,           # tuple to enable sharding, or None
    filters="auto",        # array->array codecs
    compressors="auto",    # byte->byte codecs; None disables compression
    serializer="auto",     # array->bytes codec
    fill_value=0,
    order="C",
    attributes=None,       # dict of JSON-serializable user metadata
    dimension_names=None,
    storage_options=None,  # dict passed to fsspec for URL stores
    overwrite=False,
    zarr_format=3,         # 3 (default) or 2 for legacy interop
)
```

`chunks="auto"` lets Zarr pick a reasonable chunk shape; specify it explicitly for any
performance-sensitive array (see `performance.md`).

### Convenience constructors

```python
zarr.zeros(shape=(1000, 1000), chunks=(100, 100), dtype="f4", store="z.zarr")
zarr.ones((5000, 5000), chunks=(500, 500))          # store omitted -> MemoryStore
zarr.full((1000, 1000), fill_value=42, chunks=(100, 100))
zarr.array(np.arange(10_000).reshape(100, 100), chunks=(10, 10), store="a.zarr")
zarr.zeros_like(z)                                   # match shape/chunks/dtype of z
```

`empty` / `empty_like`, `ones_like`, `full_like` follow the same pattern. `empty`
allocates without initializing values — read only cells you have written.

### Opening

```python
zarr.open_array("data.zarr", mode="r")    # read-only, must exist
zarr.open_array("data.zarr", mode="r+")   # read/write, must exist
zarr.open_array("data.zarr", mode="a", shape=..., chunks=..., dtype=...)  # create-or-open
zarr.open("data.zarr")                     # auto-detect: returns Array OR Group
```

**Mode semantics:** `r` read-only (must exist), `r+` read/write (must exist), `a`
read/write create-if-missing (default), `w` create/overwrite, `w-` create/fail-if-exists.

## Reading and Writing

Basic indexing mirrors NumPy and returns NumPy arrays on read:

```python
z[:] = 42                                   # write whole array
z[0, :] = np.arange(z.shape[1])             # write a row
z[10:20, 50:60] = np.random.random((10, 10))
row = z[5, :]                               # read -> ndarray
block = z[0:100, 0:100]
```

### Advanced indexing

```python
z.vindex[[0, 5, 10], [2, 8, 15]]   # vectorized point / coordinate selection
z.oindex[0:10, [5, 10, 15]]        # orthogonal (outer-product) selection
z.blocks[0, 0]                     # whole-chunk selection by chunk index
z.blocks[0:2, 0:2]                 # first 2x2 block of chunks
```

`blocks` indexing is the cheapest way to iterate an array chunk-aligned — each access
maps to exactly one chunk, avoiding read-modify-write across chunk boundaries.

### Resize and append

```python
z.resize((15_000, 15_000))     # v3 takes a SHAPE TUPLE (v2 used z.resize(15000, 15000))
z.append(np.random.random((1000, z.shape[1])), axis=0)   # grow along an axis
```

Resizing only edits metadata; existing chunks are untouched and new region reads as
`fill_value` until written.

## Codecs

Import from `zarr.codecs`. In v3, a pipeline is `filters` (array→array) → `serializer`
(array→bytes) → `compressors` (byte→byte).

```python
zarr.codecs.BloscCodec(cname="zstd", clevel=5, shuffle=zarr.codecs.BloscShuffle.shuffle)
zarr.codecs.GzipCodec(level=6)          # level 0-9
zarr.codecs.ZstdCodec(level=3)          # level 1-22
zarr.codecs.BytesCodec()                # serializer: raw array bytes, no compression
zarr.codecs.Crc32cCodec()               # checksum
zarr.codecs.ShardingCodec(...)          # low-level sharding (usually set via shards=)
zarr.codecs.TransposeCodec(order=...)   # reorder axes before serialization
```

`BloscCodec.cname` accepts `"blosclz"`, `"lz4"`, `"lz4hc"`, `"zstd"`, `"zlib"` (and
`"snappy"` where the build supports it). `shuffle` accepts the `BloscShuffle` enum
(`noshuffle`, `shuffle`, `bitshuffle`) or the matching strings.

> v2 note: v2 used `compressor=` with a single numcodecs codec and a `codecs=` list.
> v3's high-level knob is `compressors=` (plural, byte→byte). Passing `compressors=None`
> writes uncompressed chunks.

## Attributes

Arbitrary JSON-serializable metadata rides with the array or group:

```python
z.attrs["units"] = "K"
z.attrs["description"] = "2m air temperature"
z.attrs["version"] = 2.1
print(dict(z.attrs))
del z.attrs["version"]
```

Values must be JSON-serializable (str, number, bool, None, list, dict). Attributes
persist in the metadata document and reload on open.

## Array Properties and Info

```python
z.shape          # (10000, 10000)
z.chunks         # (1000, 1000)
z.shards         # shard shape, or None if not sharded
z.dtype          # dtype('float32')
z.size           # total number of elements
z.nbytes         # uncompressed size in bytes
z.nchunks        # number of chunks
z.cdata_shape    # array shape measured in chunks

print(z.info)              # cheap: dtype, shape, chunks, shards, codecs
print(z.info_complete())   # scans store for ACTUAL stored (compressed) bytes
```

`z.info` is metadata-only and instant; `z.info_complete()` walks the store to report
real on-disk size and compression ratio, so it costs I/O — use it deliberately.

## Data Type Strings

```
i1 i2 i4 i8      signed integers   (8/16/32/64-bit)
u1 u2 u4 u8      unsigned integers
f2 f4 f8         floats            (half/single/double)
c8 c16           complex
bool             boolean
S10              fixed-length bytes (10 bytes)
U10              fixed-length unicode (10 chars)
```

NumPy dtype objects and long names (`"float32"`) work too.

## Error Handling

```python
try:
    z = zarr.open_array("missing.zarr", mode="r")
except FileNotFoundError:
    ...  # store/array does not exist in a read mode
```

Opening a non-existent store in a read mode raises `FileNotFoundError`. Zarr also
exposes validation errors under `zarr.errors` (e.g. metadata/type validation and
"already contains an array/group" conditions) — catch the specific class only when you
have confirmed its name against the installed version, since the v3 error hierarchy
differs from v2's (`PathNotFoundError` and friends are gone).
