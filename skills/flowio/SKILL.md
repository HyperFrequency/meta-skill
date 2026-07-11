---
name: flowio
version: 0.1.0
description: >-
  FlowIO is a minimal-dependency Python library for reading and writing Flow
  Cytometry Standard (FCS) files (versions 2.0, 3.0, and 3.1). Use it to parse
  the HEADER/TEXT/DATA/ANALYSIS segments of an .fcs file, extract events as a
  NumPy array (raw or gain/log/time-preprocessed), read channel labels
  (PnN/PnS/PnR) and instrument metadata, classify scatter/fluorescence/time
  channels, separate multi-dataset files, and write new FCS 3.1 files from
  arrays. Reach for it in backend services, batch pipelines, and preprocessing
  before downstream cytometry analysis or conversion to CSV/DataFrame. Do NOT
  use it for compensation, gating, biexponential/logicle transforms, or
  GatingML/FlowJo workspaces — those belong to FlowKit, which is built on top of
  FlowIO. It is a file I/O layer, not an analysis, statistics, or visualization
  toolkit.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (FlowIO)"
---

# FlowIO

## Overview

FlowIO reads and writes Flow Cytometry Standard (FCS) files with almost no
dependencies beyond NumPy. It parses the four FCS segments — HEADER, TEXT
(metadata keywords), DATA (binary/float/ASCII events), and optional ANALYSIS —
across FCS 2.0, 3.0, and 3.1, and it can synthesize new FCS 3.1 files from a
NumPy array. Because its footprint is tiny, it fits cleanly into web backends,
ingestion pipelines, and validation tooling where the heavier FlowKit stack is
overkill.

This skill is a **router**. It gives you the object model, a quick-start path,
and the boundaries of what FlowIO does, then delegates the full API surface and
worked recipes to `references/`.

## When to Use This Skill

- Parsing `.fcs` files or extracting their TEXT-segment metadata.
- Pulling event data into a NumPy array (raw, or gain/log/time-preprocessed).
- Reading channel names (`PnN` short, `PnS` descriptive) and ranges (`PnR`).
- Classifying channels into scatter / fluorescence / time groups.
- Detecting and splitting FCS files that hold multiple datasets.
- Writing a new FCS 3.1 file from a NumPy array (e.g. after filtering).
- Converting FCS event data to CSV or a pandas DataFrame.
- Batch-scanning a directory of FCS files for a metadata summary.
- Validating or inspecting FCS structure before deeper analysis.

## When NOT to Use This Skill

- **Compensation, gating, or transforms** (logicle, biexponential, hyperlog),
  and **GatingML / FlowJo `.wsp` workspaces** — use **FlowKit**, the higher-level
  library that is built on FlowIO. FlowIO deliberately stops at file I/O.
- **In-place event editing** — FlowIO does not mutate DATA in a loaded file.
  Extract the array, modify it, and write a new file with `create_fcs`.
- **Statistics, clustering, or dimensionality reduction** on the events — take
  the array into `scikit-learn` / `umap-learn`, or hold it in `anndata`.
- **Plotting** (histograms, dot plots, density) — pull the array out and use
  `matplotlib` / `seaborn`.
- **Generic tabular ETL** with no FCS involved — reach for `polars` or pandas.

## Installation

```bash
uv pip install flowio        # or: pip install flowio
```

Requires Python 3.9+. NumPy is the only runtime dependency.

## Quick Start

### Read an FCS file

```python
from flowio import FlowData

flow = FlowData("experiment.fcs")

flow.version        # '2.0' | '3.0' | '3.1'
flow.event_count    # number of events (rows)
flow.channel_count  # number of channels (columns)
flow.pnn_labels     # short channel names, e.g. ['FSC-A', 'SSC-A', 'FL1-A']
flow.pns_labels     # descriptive stain names, e.g. ['Forward Scatter', ...]

events = flow.as_array()                    # (event_count, channel_count), preprocessed
raw    = flow.as_array(preprocess=False)    # no gain/log/time scaling
```

### Write an FCS file from an array

```python
import numpy as np
from flowio import create_fcs

events   = np.random.rand(10_000, 3) * 1000     # 2-D: rows = events, cols = channels
channels = ["FSC-A", "SSC-A", "FL1-A"]

with open("output.fcs", "wb") as fh:
    create_fcs(fh, events.flatten(), channels,   # event_data must be a FLAT 1-D array
               opt_channel_names=["Forward Scatter", "Side Scatter", "FITC"],
               metadata_dict={"$SRC": "generated"})
```

`create_fcs` takes an **open binary file handle** as its first argument (not a
path) and always writes **FCS 3.1** with single-precision float DATA. Its
`event_data` argument must be a **flattened 1-D array** in row-major order
(event 0's channels, then event 1's, …), *not* a 2-D matrix — call `.flatten()`
on an `(events × channels)` array first, or `create_fcs` raises `TypeError`. See
`references/api-reference.md` for the exact signature and every parameter.

## Core Capabilities

Each capability below is a pointer into the references. Read the linked file
before relying on an exact signature — do not guess parameter names.

### Reading and lenient parsing — `references/api-reference.md`
`FlowData(...)` is the primary entry point. Flags handle real-world file damage:
`only_text=True` (metadata only, skip DATA/ANALYSIS — much lower memory),
`ignore_offset_discrepancy=True` / `use_header_offsets=True` /
`ignore_offset_error=True` (HEADER-vs-TEXT byte-offset mismatches), and
`null_channel_list=[...]` (drop known-empty channels during parse).

### Metadata and channel classification — `references/api-reference.md`
`flow.text` is the full TEXT keyword dict (`$DATE`, `$CYT`, `$PAR`, `$TOT`, …).
`flow.analysis` holds the ANALYSIS segment if present. Channels are pre-grouped:
`flow.scatter_indices`, `flow.fluoro_indices`, `flow.time_index`. Per-channel
labels/ranges live in `flow.pnn_labels`, `flow.pns_labels`, `flow.pnr_values`.

### Multi-dataset files — `references/api-reference.md`
Some `.fcs` files chain several datasets via `$NEXTDATA`. Loading one with the
plain constructor raises `MultipleDataSetsError`; call
`read_multiple_data_sets(path)` to get a list of `FlowData` objects, or pass
`nextdata_offset=` to `FlowData` to seek a specific dataset.

### Preprocessing model — `references/api-reference.md`
`as_array(preprocess=True)` applies log amplification
(`PnE = "decades,log0"` with `decades > 0` → `value = log0 * 10 ** (decades * x / PnR)`),
then gain (`PnG` → `value / PnG`), then time scaling. Pass `preprocess=False` to
get untouched channel values — required when you intend to re-export, so you do
not double-apply transforms.

### Writing and re-exporting — `references/recipes.md`
`create_fcs(...)` builds a file from an array; `flow.write_fcs(filename)`
round-trips a loaded object with optional metadata overrides. Recipes cover
filter-then-export, channel extraction, CSV/DataFrame conversion, and batch
directory summaries — all end-to-end.

## Failure Modes and Boundaries

- **Offset discrepancy / parse error** → catch `DataOffsetDiscrepancyError` or
  `FCSParsingError`, then retry with `ignore_offset_discrepancy=True` (or
  `use_header_offsets=True` / `ignore_offset_error=True`). See the exception
  table in `references/api-reference.md`.
- **`MultipleDataSetsError`** → switch to `read_multiple_data_sets()`.
- **Large files** → use `only_text=True` for metadata-only passes; for event
  data, process files one at a time rather than loading a whole directory.
- **Double-transformed data on re-export** → read with `preprocess=False`
  before feeding an array back into `create_fcs`.
- **Unexpected channel count** → inspect `null_channels` / use
  `null_channel_list=` to exclude empty channels.
- **Scope wall** → the moment you need compensation, gating, or a FlowJo
  workspace, stop and move to FlowKit; FlowIO will not do it.

## Related Skills

- `anndata` — hold an events × channels matrix with aligned per-event and
  per-channel metadata for downstream single-cell-style analysis.
- `scikit-learn`, `umap-learn` — clustering / dimensionality reduction on the
  extracted event array.
- `polars` — tabular wrangling of metadata summaries or exported events.
- `matplotlib`, `seaborn` — plotting cytometry distributions from the array.

## Reference Index

- `references/api-reference.md` — `FlowData` constructor flags, attributes, and
  methods; `create_fcs` / `read_multiple_data_sets` signatures; exception
  classes; FCS segment structure; and the common TEXT-keyword table.
- `references/recipes.md` — end-to-end workflows: inspection, batch summary,
  FCS→CSV/DataFrame, filter-and-re-export, channel extraction, modify-and-write.

## Resources

- Documentation: https://flowio.readthedocs.io/
- Source: https://github.com/whitews/FlowIO
- Companion (analysis): https://github.com/whitews/FlowKit
