# Denario API Reference

All examples assume `from denario import Denario, Journal`.

## `Denario(project_dir)`

The orchestrator. One instance owns one research project directory; every stage reads and
writes artifacts there.

| Parameter     | Type  | Meaning                                                        |
| ------------- | ----- | ------------------------------------------------------------- |
| `project_dir` | `str` | Directory where all inputs and generated artifacts are stored. |

```python
den = Denario(project_dir="./my_research")
```

> Per-stage LLM/model selection is configured through environment/upstream config and
> varies by version. Confirm the exact constructor keyword against upstream docs before
> depending on a specific model-routing argument; do not assume one.

## Stage methods

Each generative stage has a `get_*` (produce automatically) and a `set_*` (supply your own)
form. `get_*` methods persist their output into `project_dir` and return nothing you need
to capture; read the written artifact to inspect the result.

### `set_data_description(description: str)`

Establishes the research context — dataset(s), format, size, available tools, domain, goals,
and known data-quality caveats. This is the foundation every later stage builds on; richer
input yields better ideas and methods.

```python
den.set_data_description("""
Dataset: 10 years of daily temperature from 50 stations, CSV [date, station_id, temp, humidity]
Tools: pandas, scipy, sklearn, matplotlib, seaborn
Domain: climatology
Interests: warming trends, seasonality, regional variation
Caveats: missing data in 2015; station 23 has calibration issues
""")
```

### `get_idea()`

Generates a hypothesis / research question from the data description. Writes the idea
artifact (e.g. `idea.md`). Requires a data description first.

### `set_idea(idea: str)`

Supply your own research question, skipping automated idea generation.

```python
den.set_idea("Analyze the impact of El Niño events on regional temperature anomalies")
```

### `get_method()`

Designs a methodology (analytical approach, statistical methods, validation strategy,
expected outputs) from the idea + data description. Writes `methodology.md`. Requires an
idea.

### `set_method(method: str | Path)`

Supply a methodology as a string or a path to a markdown file.

```python
den.set_method("methodology.md")
den.set_method("1. STL decomposition\n2. Pearson correlation\n3. Mann-Kendall trend test")
```

### `get_results()`

The compute stage: the execution agent writes and runs analysis code, producing statistics,
tables, and figures, then writes `results.md` and `figures/`. Requires an idea and a method.
This is the most expensive and longest-running stage.

### `set_results(results: str | Path)`

Supply pre-computed results (string or markdown path) — useful when analysis was done
elsewhere, or when iterating on the paper without re-running compute.

### `get_paper(journal: Journal = None)`

Generates a publication-ready LaTeX manuscript from the accumulated artifacts: `paper.tex`,
embedded figures/tables, a bibliography, and a compiled `paper.pdf` when a TeX toolchain is
available. Requires results. `journal` selects the formatting template; omitting it uses a
generic format.

```python
den.get_paper(journal=Journal.APS)
```

## `Journal` enum

Selects the manuscript formatting template.

| Member        | Format                                                                 |
| ------------- | ---------------------------------------------------------------------- |
| `Journal.APS` | American Physical Society (RevTeX) — Physical Review / PRL and similar. |

Upstream may expose additional members in newer versions; enumerate `Journal` in your
installed version (`list(Journal)`) rather than assuming a fixed set.

## Project directory layout

After a full run, `project_dir` typically contains:

```
project_dir/
├── data_description.txt   # input context
├── idea.md                # generated or provided idea
├── methodology.md         # generated or provided methodology
├── results.md             # generated or provided results
├── figures/               # generated visualizations (figure_*.png)
├── paper.tex              # generated LaTeX source
├── paper.pdf              # compiled PDF (only if LaTeX is installed)
└── logs/                  # agent execution logs
```

All artifacts are markdown/LaTeX — version-control-friendly and auditable. Commit after each
stage to track how the research evolves.

## Stage-ordering errors

Stages have prerequisites; calling one early raises:

```python
den = Denario(project_dir="./p")
den.get_idea()        # error: call set_data_description() first
den.get_results()     # error: needs an idea and a method
den.get_paper()       # error: needs results
```

Either follow the pipeline order or satisfy the prerequisite with the matching `set_*`
method. To refine mid-pipeline, re-set an upstream stage and re-run only the downstream
ones (e.g. `set_method(...)` then `get_results()` then `get_paper(...)`).
