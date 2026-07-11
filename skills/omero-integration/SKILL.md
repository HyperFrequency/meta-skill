---
name: omero-integration
version: 0.1.0
description: >-
  Access and manipulate microscopy images and metadata on an OMERO server from Python
  through the omero-py BlitzGateway. Use when you need to connect to an OMERO server,
  navigate the Project/Dataset/Image and Screen/Plate/Well hierarchies, pull pixel planes
  as NumPy arrays, create or read ROIs, attach tag / key-value / file annotations, store
  measurements in OMERO.tables, or write server-side OMERO.scripts for batch processing and
  high-content screening. Not for local image files with no OMERO server (use tifffile /
  aicsimageio / `bioimage-analysis`), for OME-TIFF / OME-Zarr conversion outside OMERO, or
  for the segmentation and quantification algorithms themselves — this skill is the OMERO
  client and data-management layer, not an image-processing toolkit.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: GPL-2.0-or-later (omero-py)
---

# OMERO Integration

## Overview

OMERO (Open Microscopy Environment Remote Objects) is a client/server platform for storing,
organizing, and analyzing microscopy images plus their metadata. You talk to it from Python
with the `omero-py` package; almost everything runs through a single `BlitzGateway`
connection object that wraps the lower-level Ice services.

This skill is a router. It tells you which capability you need and points you at the
reference file that carries the exact API calls, parameters, and worked examples. Read the
relevant `references/*.md` before writing code — the signatures matter (Ice `rtypes`,
0- vs 1-indexed channels, service cleanup) and are easy to get wrong from memory.

Mental model of the object graph:

```
Project ─< Dataset ─< Image ─ Pixels (5D: X,Y,Z,C,T) ─ Channels
Screen  ─< Plate   ─< Well  ─< WellSample ─ Image        (high-content screening)
Any object ─< Annotations (Tag, MapAnnotation, FileAnnotation, Comment, ...)
Image ─< ROI ─< Shape (Rectangle, Ellipse, Polygon, Mask, Point, Line)
```

## When to Use This Skill

Use this skill when the work touches an OMERO server, specifically to:

- Connect / authenticate and manage sessions, groups, and secure connections → `references/connection.md`
- Browse or query Projects, Datasets, Images, or screening Plates/Wells → `references/data-access.md`
- Read raw pixel planes/tiles as NumPy, render images, or create derived images → `references/pixels-rendering.md`
- Create, read, or measure ROIs and their intensity statistics → `references/rois.md`
- Add or retrieve tags, key-value pairs, file attachments, or comments → `references/metadata.md`
- Store or query structured measurements in OMERO.tables (HDF5-backed) → `references/tables.md`
- Package analysis as a server-side OMERO.script with a client UI → `references/scripts.md`
- Handle permissions, filesets, deletion, cross-group queries, admin/service access → `references/advanced.md`

## When NOT to Use This Skill

- **No OMERO server involved.** For local TIFF/OME-TIFF/CZI/ND2 files, use `tifffile`,
  `aicsimageio`, or `bioimage-analysis`. OMERO is a networked repository, not a file reader.
- **You want the analysis algorithm itself** (segmentation, tracking, deconvolution,
  feature extraction). Pull the pixels here, then hand the NumPy arrays to `bioimage-analysis`
  or `histolab`; store the results back via `references/tables.md`.
- **Format conversion outside OMERO** (OME-TIFF ↔ OME-Zarr, Bio-Formats CLI). That is a
  `bioformats2raw` / `raw2ometiff` job, not an omero-py task.
- **A different data platform.** For non-imaging LIMS/registry work see
  `benchling-integration` or `lamindb`; for DICOM medical imaging see `pydicom` /
  `clinical-imaging`.

## Installation and Quick Start

```bash
uv pip install omero-py    # pulls in zeroc-ice; needs Python 3.7+ and network access to the server
```

Requirements: a reachable OMERO server (host, port — default `4064`), valid credentials, and
`zeroc-ice` 3.6+ (installed as a dependency). Always prefer the context-manager form so the
connection is closed even on error:

```python
from omero.gateway import BlitzGateway

with BlitzGateway(username, password, host=host, port=4064, secure=True) as conn:
    print("Connected as", conn.getUser().getName())
    for project in conn.getObjects("Project"):
        print(project.getId(), project.getName())
    # conn.connect() and conn.close() are handled by the context manager
```

Credential hygiene: never hardcode passwords. Read them from environment variables
(`OMERO_USER`, `OMERO_PASSWORD`, `OMERO_HOST`) or a config file. See `references/connection.md`.

## Cross-Cutting Rules (read before any write operation)

These bite everyone at least once — keep them in mind regardless of which capability you use:

- **Ice `rtypes` are mandatory for model objects.** Wrap raw values: `rdouble(50)`, `rint(0)`,
  `rstring("label")`. Assigning a bare Python `int`/`float` to a model field fails or silently
  misbehaves. Unwrap with `.getValue()` (or `.val`) when reading.
- **`.getObject()` returns `None` when not found or not readable.** Check before use — a missing
  object is often a group-context issue, not a bad ID (see below).
- **Group context governs visibility.** OMERO data is scoped to groups. If an object "isn't
  there", set `conn.SERVICE_OPTS.setOmeroGroup('-1')` to search across all your groups, then
  switch to the object's real group for further work. Details in `references/connection.md`
  and `references/advanced.md`.
- **Channels are 0-indexed for pixel access, 1-indexed for rendering.** `pixels.getPlane(z, c, t)`
  uses `c=0..N-1`; `image.setActiveChannels([1, 2])` uses 1-based indices. Mixing these up is a
  classic bug — see `references/pixels-rendering.md`.
- **Close what you open.** Tables, `RawFileStore`, and `ThumbnailStore` hold server resources
  and must be `.close()`d. The `BlitzGateway` context manager only closes the connection.
- **Deletes are asynchronous.** `conn.deleteObjects(...)` returns a handle; pass `wait=True` or
  monitor a callback (`references/advanced.md`) before assuming completion.

## Typical Workflows

**Retrieve and analyze images** — connect (`references/connection.md`) → find the dataset and
images (`references/data-access.md`) → read planes as NumPy (`references/pixels-rendering.md`)
→ run your analysis → write results to a table (`references/tables.md`) or file annotation
(`references/metadata.md`).

**Batch ROI quantification** — for each image, `roiService.findByImage(...)` to get shapes
(`references/rois.md`) → `getShapeStatsRestricted(...)` for per-channel intensity stats →
persist rows to an OMERO.table keyed by `ImageColumn`/`RoiColumn` (`references/tables.md`).

**Ship a reusable pipeline** — wrap the logic in an OMERO.script with typed parameters and a
client UI, run it server-side to avoid pixel transfer, and return the created image/table/file
to the user (`references/scripts.md`).

## References

- `references/connection.md` — connections, sessions, secure transport, group context, admin `suConn`.
- `references/data-access.md` — hierarchy navigation, `getObjects` filters/pagination, screening plates/wells, image dimensions.
- `references/pixels-rendering.md` — pixel planes/tiles/hypercubes, histograms, rendering settings, projections, `createImageFromNumpySeq`, physical pixel sizes.
- `references/rois.md` — all shape types, RGBA encoding, masks, retrieval/parsing, `getShapeStatsRestricted`, edit/delete.
- `references/metadata.md` — tag/map/file/comment/numeric annotations, namespaces, linking, download, bulk operations.
- `references/tables.md` — OMERO.tables column types, create/append/read, `getWhereList` queries, linking tables to objects.
- `references/scripts.md` — OMERO.scripts structure, parameter types, inputs/outputs, deployment and CLI upload/launch.
- `references/advanced.md` — permissions model, filesets/original files, deletion with callbacks, cross-group queries, services, event context.

## Additional Resources

- OMERO Python guide: https://omero.readthedocs.io/en/stable/developers/Python.html
- OMERO data model: https://omero.readthedocs.io/en/stable/developers/Model.html
- Community forum: https://forum.image.sc/tag/omero
