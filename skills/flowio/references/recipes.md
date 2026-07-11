# FlowIO Recipes

End-to-end workflows built on `FlowData`, `create_fcs`, and
`read_multiple_data_sets`. See `api-reference.md` for signatures. All examples
assume `from flowio import FlowData` (plus other imports shown per recipe).

## Inspect an unknown FCS file

Print structure and channel/metadata summary in one pass.

```python
from flowio import FlowData

flow = FlowData("unknown.fcs")

print(f"{flow.name}  v{flow.version}  {flow.file_size:,} bytes")
print(f"{flow.event_count:,} events x {flow.channel_count} channels")

for i, (pnn, pns) in enumerate(zip(flow.pnn_labels, flow.pns_labels)):
    if i in flow.scatter_indices:
        kind = "scatter"
    elif i in flow.fluoro_indices:
        kind = "fluoro"
    elif i == flow.time_index:
        kind = "time"
    else:
        kind = "other"
    print(f"  [{i}] {pnn:10s} | {pns:28s} | {kind}")

for key in ("$DATE", "$BTIM", "$ETIM", "$CYT", "$INST", "$SRC"):
    print(f"  {key:8s}: {flow.text.get(key, 'N/A')}")
```

## Batch-summarize a directory (metadata only)

Use `only_text=True` so no DATA is decoded — fast and memory-light.

```python
from pathlib import Path
from flowio import FlowData
import pandas as pd

rows = []
for path in Path("data/").glob("*.fcs"):
    try:
        flow = FlowData(str(path), only_text=True)
        rows.append({
            "file": path.name,
            "version": flow.version,
            "events": flow.event_count,
            "channels": flow.channel_count,
            "date": flow.text.get("$DATE", "N/A"),
            "cyt": flow.text.get("$CYT", "N/A"),
        })
    except Exception as exc:                 # keep going past one bad file
        print(f"skip {path.name}: {exc}")

summary = pd.DataFrame(rows)
print(summary)
```

## Convert FCS to CSV / DataFrame

```python
from flowio import FlowData
import pandas as pd

flow = FlowData("sample.fcs")
frame = pd.DataFrame(flow.as_array(), columns=flow.pnn_labels)

frame.attrs["fcs_version"] = flow.version
frame.attrs["instrument"] = flow.text.get("$CYT", "Unknown")

frame.to_csv("sample.csv", index=False)
print(f"wrote {len(frame)} events")
```

## Extract specific channels and compute stats

```python
from flowio import FlowData
import numpy as np

flow = FlowData("sample.fcs")
events = flow.as_array()

fluoro_idx = flow.fluoro_indices
fluoro = events[:, fluoro_idx]
names = [flow.pnn_labels[i] for i in fluoro_idx]

for col, name in enumerate(names):
    data = fluoro[:, col]
    print(f"{name}: mean={data.mean():.1f} "
          f"median={np.median(data):.1f} std={data.std():.1f}")
```

## Filter events and re-export

Read raw (`preprocess=False`), mask, then write a new file. Preserving the
original TEXT dict keeps instrument metadata; override `$SRC` to record the edit.

```python
from flowio import FlowData, create_fcs

flow = FlowData("sample.fcs")
events = flow.as_array(preprocess=False)     # raw, so no double-transform

fsc = 0
mask = events[:, fsc] > 500
kept = events[mask]
print(f"{len(events)} -> {len(kept)} events after threshold")

with open("filtered.fcs", "wb") as fh:
    create_fcs(fh, kept.flatten(),               # create_fcs needs a flat 1-D array
               channel_names=flow.pnn_labels,
               opt_channel_names=flow.pns_labels,
               metadata_dict={**flow.text, "$SRC": "filtered"})
```

## Modify a channel and re-export

FlowIO does not edit DATA in place. Extract → modify the array → `create_fcs`.

```python
from flowio import FlowData, create_fcs

flow = FlowData("original.fcs")
events = flow.as_array(preprocess=False)
events[:, 0] = events[:, 0] * 1.5            # scale first channel

with open("scaled.fcs", "wb") as fh:
    create_fcs(fh, events.flatten(),         # flatten 2-D -> 1-D for create_fcs
               channel_names=flow.pnn_labels,
               opt_channel_names=flow.pns_labels,
               metadata_dict=flow.text)
```

## Process a multi-dataset file

```python
from flowio import read_multiple_data_sets

for i, ds in enumerate(read_multiple_data_sets("multi.fcs")):
    arr = ds.as_array()
    print(f"dataset {i}: {arr.shape}  mean={arr.mean(axis=0)}")
```

## Practices worth keeping

- Use `only_text=True` whenever you do not need event data.
- Wrap file loads in try/except so one corrupt file does not halt a batch.
- On parse failure, escalate flags: `ignore_offset_discrepancy` →
  `use_header_offsets` → `ignore_offset_error`.
- Read with `preprocess=False` before any re-export path.
- Preserve the original `flow.text` when rewriting, and stamp `$SRC` to note
  provenance.
- Validate `channel_count` / `pnn_labels` against expectations before batch
  processing — instruments differ in null-channel handling.
- When downstream analysis needs compensation, gating, or transforms, hand off
  to FlowKit rather than reimplementing them on the FlowIO array.
