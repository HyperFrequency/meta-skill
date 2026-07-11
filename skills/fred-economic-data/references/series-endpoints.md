# FRED Series Endpoints

The `fred/series/*` family: series metadata, the observations you actually chart, and
the search/discovery variants keyed on a series. All URLs are under
`https://api.stlouisfed.org/`. See `api-basics.md` for `file_type`, real-time
params, pagination, and error handling.

| Endpoint | Purpose |
|----------|---------|
| `fred/series` | Series metadata |
| `fred/series/observations` | Data values (the workhorse) |
| `fred/series/categories` | Categories a series belongs to |
| `fred/series/release` | Release a series belongs to |
| `fred/series/search` | Full-text / series-id search |
| `fred/series/search/tags` | Tags matching a search |
| `fred/series/search/related_tags` | Tags related to a search + tag set |
| `fred/series/tags` | Tags on a series |
| `fred/series/updates` | Recently updated series |
| `fred/series/vintagedates` | Revision (vintage) dates for a series |

---

## fred/series — metadata

Required: `api_key`, `series_id`. Optional: `file_type`, `realtime_start`,
`realtime_end`.

Response `seriess[0]` fields include `id`, `title`, `observation_start`,
`observation_end`, `frequency`, `units`, `seasonal_adjustment`, `last_updated`,
`popularity` (0-100), and `notes`.

```python
meta = fred_get("fred/series", series_id="GNPCA")["seriess"][0]
print(meta["title"], meta["units"], meta["observation_start"])
```

---

## fred/series/observations — data values (most used)

Required: `api_key`, `series_id`.

Key optional parameters:

| Parameter | Default | Notes |
|-----------|---------|-------|
| `file_type` | `xml` | use `json`/`csv`/`xlsx` |
| `observation_start` | `1776-07-04` | filter start (YYYY-MM-DD) |
| `observation_end` | `9999-12-31` | filter end |
| `limit` | `100000` | 1–100000 |
| `offset` | `0` | pagination |
| `sort_order` | `asc` | `asc`/`desc` |
| `units` | `lin` | transformation — see `api-basics.md` |
| `frequency` | none | down-sample — see `api-basics.md` |
| `aggregation_method` | `avg` | `avg`/`sum`/`eop` |
| `realtime_start` / `realtime_end` | today | ALFRED vintage window |
| `vintage_dates` | none | comma-separated specific vintages |
| `output_type` | `1` | 1 = observations by real-time period (default) |

```python
obs = fred_get(
    "fred/series/observations",
    series_id="GDP", observation_start="2020-01-01", units="pch",
)
series = {o["date"]: float(o["value"]) for o in obs["observations"]
          if o["value"] != "."}
```

Each observation carries `date`, `value` (string, `"."` if missing), and its
`realtime_start`/`realtime_end`. The envelope carries `count`, `offset`, `limit`.

---

## fred/series/search — find series by keyword

Required: `api_key`. Optional highlights:

| Parameter | Default | Notes |
|-----------|---------|-------|
| `search_text` | — | keywords |
| `search_type` | `full_text` | `full_text` or `series_id` |
| `limit` | `1000` | 1–1000 |
| `order_by` | `search_rank` | also `popularity`, `title`, `frequency`, `last_updated`, `observation_start/end`, `units`, ... |
| `sort_order` | varies | `asc`/`desc` |
| `filter_variable` | — | `frequency`, `units`, or `seasonal_adjustment` |
| `filter_value` | — | value for the filter |
| `tag_names` | — | semicolon-delimited, require these tags |
| `exclude_tag_names` | — | semicolon-delimited, exclude |

```python
hits = fred_get(
    "fred/series/search",
    search_text="consumer price index", limit=10,
    filter_variable="frequency", filter_value="Monthly",
    order_by="popularity", sort_order="desc",
)
for s in hits["seriess"]:
    print(s["id"], "-", s["title"])
```

`fred/series/search/tags` and `fred/series/search/related_tags` return the tag cloud
for a search (params `series_search_text`, plus `tag_names`, `tag_group_id`,
`tag_search_text`, `exclude_tag_names`) — use them to refine a broad query.

---

## fred/series/tags — tags on one series

Required: `api_key`, `series_id`. Optional: `order_by`
(`series_count`|`popularity`|`created`|`name`|`group_id`), `sort_order`. Returns
each tag's `name`, `group_id`, and `series_count`.

---

## fred/series/categories and fred/series/release

Both require `api_key` + `series_id`. `categories` returns the category nodes a
series sits under (`id`, `name`, `parent_id`); `release` returns the parent release
(`id`, `name`, `press_release`, `link`). Use these to walk from a known series back
up to its release calendar or sibling series (see `discovery-endpoints.md`).

---

## fred/series/updates — what changed recently

Required: `api_key`. Optional: `limit` (≤1000), `offset`, `filter_value`
(`macro`|`regional`|`all`), `start_time`/`end_time` (`YYYYMMDDHhmm`). **Results are
restricted to series updated in the last two weeks** — use it to detect fresh data,
not for historical crawls.

---

## fred/series/vintagedates — revision history

Required: `api_key`, `series_id`. Optional: `realtime_start` (default `1776-07-04`),
`realtime_end` (default `9999-12-31`), `limit` (≤10000), `offset`, `sort_order`.
Returns a flat `vintage_dates` array — every date the series was revised. Feed these
into `observations` (`realtime_start`/`realtime_end` or `vintage_dates`) to
reconstruct point-in-time snapshots.

```python
vints = fred_get("fred/series/vintagedates", series_id="GDP")["vintage_dates"]
first_reported = vints[0]   # earliest known publication
```
