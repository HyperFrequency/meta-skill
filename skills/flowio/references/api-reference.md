# FlowIO API Reference

FlowIO reads and writes Flow Cytometry Standard (FCS) files (versions 2.0, 3.0,
3.1). NumPy is the only runtime dependency. Python 3.9+.

> Signature note: the exact keyword names below reflect current FlowIO (1.x).
> If an import or keyword raises `TypeError`/`AttributeError`, check your
> installed version with `import flowio; flowio.__version__` — older releases
> (<1.0) accepted a filename where 1.x expects a file handle. Do not assume a
> signature that fails; introspect with `help(flowio.create_fcs)`.

## `FlowData` — reading FCS files

The primary class. Parses HEADER, TEXT, DATA, and (if present) ANALYSIS.

```python
FlowData(
    filename_or_handle,
    ignore_offset_error=False,
    ignore_offset_discrepancy=False,
    use_header_offsets=False,
    only_text=False,
    nextdata_offset=None,
    null_channel_list=None,
)
```

### Constructor parameters

| Parameter | Type | Purpose |
| --- | --- | --- |
| `filename_or_handle` | str / Path / file object | The `.fcs` file to read. |
| `ignore_offset_error` | bool | Suppress offset errors entirely (default False). |
| `ignore_offset_discrepancy` | bool | Tolerate HEADER-vs-TEXT byte-offset mismatch (default False). |
| `use_header_offsets` | bool | Trust HEADER offsets over TEXT offsets (default False). |
| `only_text` | bool | Parse only the TEXT segment; skip DATA/ANALYSIS. Much lower memory. |
| `nextdata_offset` | int | Byte offset to seek a specific dataset in a multi-dataset file. |
| `null_channel_list` | list[str] | PnN labels of empty channels to exclude during parse. |

### Attributes

**File**

- `version` — FCS version string (`'2.0'`, `'3.0'`, `'3.1'`).
- `name` — file name.
- `file_size` — size in bytes.
- `header` — dict of HEADER-segment offsets.
- `data_type` — DATA format: `'I'` int, `'F'` float, `'D'` double, `'A'` ASCII.

**Channels**

- `channel_count` — number of channels (columns).
- `channels` — dict mapping channel number → channel info.
- `pnn_labels` — list of PnN short names (e.g. `'FSC-A'`).
- `pns_labels` — list of PnS descriptive stain names (e.g. `'Forward Scatter'`).
- `pnr_values` — list of PnR range/max values.
- `scatter_indices` — column indices of scatter channels (FSC, SSC).
- `fluoro_indices` — column indices of fluorescence channels.
- `time_index` — column index of the time channel, or `None`.
- `null_channels` — indices flagged as empty/null.

**Events and metadata**

- `event_count` — number of events (rows).
- `events` — raw DATA segment as bytes (pre-decode).
- `text` — dict of all TEXT-segment keyword/value pairs.
- `analysis` — dict of ANALYSIS-segment keywords, if present (else empty/None).

### Methods

#### `as_array(preprocess=True)`

Return the DATA segment as a 2-D NumPy array of shape
`(event_count, channel_count)`.

- `preprocess=True` (default): apply gain (`PnG`), log amplification (`PnE`),
  and time scaling — see **Preprocessing** below.
- `preprocess=False`: return channel values as stored, with no transforms.
  **Use this before re-exporting**, so transforms are not applied twice.

```python
flow = FlowData("sample.fcs")
events = flow.as_array()                   # preprocessed
raw    = flow.as_array(preprocess=False)   # untouched
```

#### `write_fcs(filename, metadata=None)`

Round-trip the loaded object out to a new **FCS 3.1** file, optionally
overriding/adding TEXT keywords. Convenience wrapper over `create_fcs`.

```python
flow = FlowData("sample.fcs")
flow.write_fcs("copy.fcs", metadata={"$SRC": "modified"})
```

## `create_fcs(...)` — writing FCS files

Build a new FCS 3.1 file from a NumPy array. Writes single-precision float DATA.

```python
create_fcs(
    file_handle,          # OPEN binary file object (open(path, "wb")), not a path
    event_data,           # FLATTENED 1-D array/list, row-major (event 0's channels, then event 1's, …)
    channel_names,        # list[str] of PnN short names
    opt_channel_names=None,   # list[str] of PnS descriptive names
    metadata_dict=None,       # dict of extra TEXT-segment keywords
)
```

`event_data` is a **flattened 1-D** sequence, *not* a 2-D matrix. Passing a 2-D
ndarray raises `TypeError: only 0-dimensional arrays can be converted to Python
scalars`. Flatten an `(events × channels)` array first — `arr.flatten()` uses
C/row-major order, which is what FlowIO expects. FlowIO infers the event count
as `len(event_data) / len(channel_names)`, so `len(event_data)` must be an exact
multiple of `len(channel_names)`.

```python
import numpy as np
from flowio import create_fcs

events = np.random.rand(5_000, 3) * 1000     # 2-D (events × channels)
with open("out.fcs", "wb") as fh:
    create_fcs(fh, events.flatten(),         # flatten to 1-D
               channel_names=["FSC-A", "SSC-A", "FL1-A"],
               opt_channel_names=["Forward Scatter", "Side Scatter", "GFP"],
               metadata_dict={"$SRC": "python", "$DATE": "09-JUL-2026"})
```

`channel_names` length must equal the per-event channel count (the original
`arr.shape[1]` before flattening). When `opt_channel_names` is given it must
match that length too.

## `read_multiple_data_sets(...)` — multi-dataset files

Some FCS files chain several datasets through the `$NEXTDATA` keyword. Loading
such a file with the plain `FlowData` constructor raises `MultipleDataSetsError`.

```python
read_multiple_data_sets(
    filename_or_handle,
    ignore_offset_error=False,
    ignore_offset_discrepancy=False,
    use_header_offsets=False,
    only_text=False,
)
```

Returns a `list[FlowData]`, one per dataset.

```python
from flowio import read_multiple_data_sets

datasets = read_multiple_data_sets("multi.fcs")
for i, ds in enumerate(datasets):
    print(i, ds.event_count, ds.pnn_labels)
```

To seek a single dataset instead, pass `nextdata_offset=` to `FlowData` (offset 0
for the first; read `int(flow.text["$NEXTDATA"])` to find the next).

## Exceptions

| Exception | Raised when | Handling |
| --- | --- | --- |
| `FlowIOException` | Base class for FlowIO errors. | Catch as a catch-all. |
| `FCSParsingError` | General parse failure. | Retry with `ignore_offset_error=True`. |
| `DataOffsetDiscrepancyError` | HEADER and TEXT disagree on DATA offsets. | Retry with `ignore_offset_discrepancy=True` or `use_header_offsets=True`. |
| `MultipleDataSetsError` | File holds >1 dataset. | Use `read_multiple_data_sets()`. |
| `FlowIOWarning` | Non-fatal issue. | Inspect; usually safe. |
| `PnEWarning` | Invalid `PnE` values during file creation. | Check amplification metadata. |

```python
from flowio import FlowData, FCSParsingError, DataOffsetDiscrepancyError, MultipleDataSetsError

try:
    flow = FlowData("sample.fcs")
except MultipleDataSetsError:
    from flowio import read_multiple_data_sets
    datasets = read_multiple_data_sets("sample.fcs")
except DataOffsetDiscrepancyError:
    flow = FlowData("sample.fcs", ignore_offset_discrepancy=True)
except FCSParsingError:
    flow = FlowData("sample.fcs", ignore_offset_error=True)
```

## FCS file structure

Every FCS file has four segments:

1. **HEADER** — FCS version plus byte offsets to the other segments.
2. **TEXT** — delimiter-separated key/value metadata (the `$`-keywords).
3. **DATA** — raw events, encoded per `$DATATYPE` and `$BYTEORD`.
4. **ANALYSIS** (optional) — results written by acquisition/analysis software.

## Common TEXT-segment keywords

| Keyword | Meaning |
| --- | --- |
| `$PAR` | Number of parameters (channels). |
| `$TOT` | Total number of events. |
| `$MODE` | Data mode (`L` = list mode, most common). |
| `$DATATYPE` | `I` int, `F` float, `D` double, `A` ASCII. |
| `$BYTEORD` | Byte order — `1,2,3,4` little-endian, `4,3,2,1` big-endian. |
| `$NEXTDATA` | Offset to the next dataset (`0` if single). |
| `$BEGINDATA` / `$ENDDATA` | DATA-segment byte offsets. |
| `$BEGINANALYSIS` / `$ENDANALYSIS` | ANALYSIS-segment byte offsets. |
| `$DATE`, `$BTIM`, `$ETIM` | Acquisition date and begin/end times. |
| `$CYT`, `$INST`, `$SRC` | Cytometer, institution, and sample source. |
| `PnN` | Short name for parameter *n* (e.g. `FSC-A`). |
| `PnS` | Descriptive stain name for parameter *n*. |
| `PnR` | Range (max value) for parameter *n*. |
| `PnG` | Gain (amplification) for parameter *n*. |
| `PnE` | Log amplification for parameter *n*, format `"a,b"`. |

## Preprocessing (`as_array(preprocess=True)`)

Applied per channel, in this order:

1. **Log amplification** — `PnE` is `"decades,log0"`. If `decades > 0`,
   `value = log0 * 10 ** (decades * raw_value / PnR)`, where `PnR` is the
   channel range. (If `log0` is stored as `0`, FlowIO substitutes `1.0` per the
   FCS standard.)
2. **Gain** — if `PnG` is set and `!= 1.0`, `value = value / PnG`.
3. **Time scaling** — convert the time channel to consistent units.

Note the `/ PnR` division and that `log0` (the second `PnE` value) is the outer
multiplier while `decades` (the first) drives the exponent — a common point of
confusion. Pass `preprocess=False` to skip all three. Re-exporting preprocessed
data and then reading it back with `preprocess=True` double-applies transforms —
always round-trip with raw data.
