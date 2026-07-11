# FRED Discovery & Navigation Endpoints

How to find series when you don't already know the ID: browse the category tree,
follow releases and their publication calendars, filter by tags, or start from a
data-producing source. All URLs under `https://api.stlouisfed.org/`. Shared
mechanics (`file_type`, pagination, real-time params) are in `api-basics.md`.

Four families here: **Categories**, **Releases**, **Tags**, **Sources**.

---

## Categories — the hierarchy

FRED organizes series in a tree rooted at `category_id=0`.

| Endpoint | Purpose | Required |
|----------|---------|----------|
| `fred/category` | One category node | `api_key` (+ `category_id`, default 0) |
| `fred/category/children` | Child categories | `api_key` (+ `category_id`) |
| `fred/category/related` | One-way related categories (rare) | `api_key`, `category_id` |
| `fred/category/series` | Series in a category | `api_key`, `category_id` |
| `fred/category/tags` | Tags on a category | `api_key`, `category_id` |
| `fred/category/related_tags` | Related tags in a category | `api_key`, `category_id`, `tag_names` |

`fred/category/series` accepts the same filtering as series search: `limit` (≤1000),
`offset`, `order_by` (`series_id`, `popularity`, `title`, `frequency`, ...),
`sort_order`, `filter_variable`/`filter_value`, `tag_names`, `exclude_tag_names`.

```python
# Most popular monthly series in "Trade Balance" (category 125)
series = fred_get(
    "fred/category/series",
    category_id=125, filter_variable="frequency", filter_value="Monthly",
    order_by="popularity", sort_order="desc", limit=10,
)["seriess"]
```

Walk the tree by recursing `fred/category/children` from `category_id=0`.

**Common category IDs:** 0 root · 32991 Money, Banking & Finance · 10 Population,
Employment & Labor · 32992 National Accounts · 1 Production & Business Activity ·
32455 Prices · 32263 International Data · 3008 U.S. Regional Data · 33060 Academic
Data · 53 GDP · 33490 Interest Rates · 32145 Exchange Rates · 12 Consumer Price
Indexes · 2 Unemployment.

---

## Releases — publications and their calendars

A *release* is a data publication (e.g. GDP, the Employment Situation, CPI) with
scheduled dates and many member series.

| Endpoint | Purpose | Required |
|----------|---------|----------|
| `fred/releases` | All releases | `api_key` |
| `fred/releases/dates` | Release dates across all releases | `api_key` |
| `fred/release` | One release | `api_key`, `release_id` |
| `fred/release/dates` | Dates for one release | `api_key`, `release_id` |
| `fred/release/series` | Series in a release | `api_key`, `release_id` |
| `fred/release/sources` | Sources feeding a release | `api_key`, `release_id` |
| `fred/release/tags` | Tags on a release | `api_key`, `release_id` |
| `fred/release/related_tags` | Related tags | `api_key`, `release_id`, `tag_names` |
| `fred/release/tables` | Hierarchical release table tree | `api_key`, `release_id` |

`fred/releases/dates` is the release calendar. Filter by `realtime_start`/
`realtime_end`, sort with `order_by` (`release_date`|`release_id`|`release_name`),
and set `include_release_dates_with_no_data=true` to include scheduled-but-unpublished
dates. Note these are *source publication* dates, which can differ slightly from when
data lands on FRED.

```python
cal = fred_get(
    "fred/releases/dates",
    realtime_start="2026-07-10", realtime_end="2026-07-24",
    order_by="release_date", sort_order="asc",
    include_release_dates_with_no_data="true",
)["release_dates"]
```

`fred/release/tables` returns a nested `elements` map (`element_id`, `parent_id`,
`series_id`, `name`, `level`, `children`) mirroring the printed release table;
pass `include_observation_values=true` and `observation_date` to attach values.

**Common release IDs:** 53 GDP · 50 Employment Situation · 10 CPI · 13 G.17
Industrial Production · 21 H.6 Money Stock · 51 International Transactions · 9
Advance Retail Sales.

---

## Tags — cross-cutting filters

Tags are the most powerful discovery axis: intersect several to pin down exactly
the series you want. See `api-basics.md` for the eight tag groups.

| Endpoint | Purpose | Required |
|----------|---------|----------|
| `fred/tags` | All tags (filterable) | `api_key` |
| `fred/related_tags` | Tags co-occurring with a tag set | `api_key`, `tag_names` |
| `fred/tags/series` | Series matching **all** given tags | `api_key`, `tag_names` |

Common optional params across all three: `tag_group_id`, `search_text`,
`exclude_tag_names`, `limit` (≤1000), `offset`, `order_by`
(`series_count`|`popularity`|`name`|`created`|`group_id`), `sort_order`.

`tag_names` is **semicolon-delimited** and `fred/tags/series` requires a series to
match *every* tag (logical AND) — narrow aggressively:

```python
# Quarterly, USA GDP series, most popular first
series = fred_get(
    "fred/tags/series",
    tag_names="gdp;quarterly;usa", order_by="popularity", sort_order="desc",
)["seriess"]

# What tags commonly co-occur with "unemployment rate" geographically?
geo = fred_get(
    "fred/related_tags",
    tag_names="unemployment rate", tag_group_id="geo",
    order_by="series_count", sort_order="desc",
)["tags"]
```

Discovery loop: `fred/tags?search_text=<topic>` → take the top tag →
`fred/related_tags` to expand → `fred/tags/series` with the chosen intersection.

---

## Sources — data-producing agencies

A *source* is the agency behind the data (BLS, BEA, Census, the Fed Board, OECD,
IMF, ...).

| Endpoint | Purpose | Required |
|----------|---------|----------|
| `fred/sources` | All sources | `api_key` |
| `fred/source` | One source | `api_key`, `source_id` |
| `fred/source/releases` | Releases from a source | `api_key`, `source_id` |

```python
fed_releases = fred_get("fred/source/releases", source_id=1, order_by="name")["releases"]
```

**Common source IDs:** 1 Federal Reserve Board · 3 Philadelphia Fed · 4 St. Louis
Fed · 18 Bureau of Economic Analysis · 19 Census Bureau · 22 Bureau of Labor
Statistics · 31 NBER · 40 IMF · 41 World Bank · 47 OECD · 57 S&P Dow Jones Indices ·
44 University of Michigan.

To enumerate everything an agency publishes: `fred/source` (name) →
`fred/source/releases` → `fred/release/series` for each release.
