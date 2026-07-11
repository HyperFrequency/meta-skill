# Fetching PDE Datasets

Two practical sources for PDEBench-style data: **HuggingFace Hub** (fast CDN, when
a mirror of the file you need exists) and **DaRUS** (the University of Stuttgart
data repository — the authoritative PDEBench host, covering the datasets no HF
mirror has). Try HF first for speed; fall back to DaRUS for completeness.

## HuggingFace Hub

`hf_hub_download` returns a local path to a single cached file. Confirm the exact
`repo_id` and `filename` on the Hub before hard-coding them — dataset repos get
renamed and reorganized, and not every PDEBench subset is mirrored there.

```python
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="pdebench/Advection",              # verify on huggingface.co first
    filename="1D_Advection_Sols_beta1.0.hdf5",
    repo_type="dataset",                       # required: it is a dataset, not a model
    cache_dir="/tmp/hf_cache",
)
```

- `repo_type="dataset"` is mandatory; omitting it makes the Hub look under models
  and raise a not-found error.
- A missing/renamed repo raises early — treat any `RepositoryNotFoundError` /
  `EntryNotFoundError` as the signal to switch to DaRUS, not to retry.
- For gated or rate-limited access, set `HF_TOKEN` in the environment; anonymous
  pulls are rate-limited.

## DaRUS (aria2c)

DaRUS serves files by numeric file ID over a stable REST path. Downloads are large
(often tens of GB), so use `aria2c` with many parallel connections rather than a
single-stream `requests.get`.

```python
import subprocess

file_id = 123456                               # resolve this first (see below)
filename = "1D_CFD_Rand_Eta1e-8.hdf5"
url = f"https://darus.uni-stuttgart.de/api/access/datafile/{file_id}"

subprocess.run(
    [
        "aria2c",
        "-x", "16",                            # 16 connections per download
        "-s", "16",                            # split into 16 segments
        "--max-connection-per-server=16",
        "--min-split-size=10M",
        "--timeout=600",
        "--max-tries=5",
        "-d", "/tmp",                          # output dir
        "-o", filename,                        # output filename
        url,
    ],
    check=True,
    timeout=3600,
)
```

Install `aria2`:

- Debian/Ubuntu: `apt install aria2`
- macOS: `brew install aria2`
- Modal image: `.apt_install("aria2")`

## Resolving DaRUS file IDs

PDEBench publishes a CSV mapping every dataset to its DaRUS URL, path, and md5.
Fetch it and grep for the dataset you want to recover the file ID embedded in the
`api/access/datafile/<id>` URL:

```python
import urllib.request

csv_url = (
    "https://raw.githubusercontent.com/pdebench/PDEBench/main/"
    "pdebench/data_download/pdebench_data_urls.csv"
)
rows = urllib.request.urlopen(csv_url).read().decode()
for line in rows.splitlines():
    if "1D_CFD" in line:                       # substring of the target dataset
        print(line)                            # filename, URL (with file_id), path, md5
```

The `md5` column lets you verify integrity after download; a mismatch means a
truncated or corrupted pull — delete and re-fetch.

## Coverage notes

- **On HF (fast path):** the advection / Burgers-style 1-D subsets are commonly
  mirrored. Verify the exact repo before relying on it.
- **DaRUS-only (no HF mirror in practice):** reaction-diffusion and 1-D
  compressible-flow (CFD) subsets typically must come from DaRUS.
- Data placement on both hosts changes over time — the durable strategy is "try
  HF, fall back to DaRUS via the CSV", not a fixed list of repo IDs.
