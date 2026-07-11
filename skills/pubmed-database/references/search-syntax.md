# PubMed Search Syntax and Field Tags

The precision of a PubMed search is decided by the query string. This reference covers Boolean
logic, field tags, phrase/wildcard/proximity search, MeSH, Automatic Term Mapping, filters, and
troubleshooting.

## Boolean operators

Write operators in **uppercase**; PubMed evaluates left to right, so parenthesize to control order.

| Operator | Effect | Example |
| --- | --- | --- |
| `AND` | all terms present (implied between concepts) | `diabetes AND hypertension` |
| `OR` | at least one term — use for synonyms | `heart attack OR myocardial infarction` |
| `NOT` | exclude a term (use sparingly — drops relevant hits) | `cancer NOT lung` |

```
(heart attack OR myocardial infarction) AND treatment
```

## Phrase, wildcard, proximity

- **Phrase:** quote to search words in order and bypass term mapping — `"kidney allograft"`,
  `"machine learning"`.
- **Wildcard `*`:** zero-or-more characters; needs **≥ 4 leading characters**, cannot lead a term.
  `vaccin*` → vaccine, vaccination, vaccinate; `pediatr*` → pediatric, pediatrics.
- **Proximity:** terms within N words, only in Title, Title/Abstract, and Affiliation fields —
  `"vitamin C"[Title:~3]`, `"breast cancer screening"[tiab:~5]`.

## Field tags — `term[tag]`

### Author

| Tag | Field | Example |
| --- | --- | --- |
| `[au]` | Author (last name + initials) | `smith ja[au]` |
| `[1au]` | First author | `jones m[1au]` |
| `[lastau]` | Last author | `wilson k[lastau]` |
| `[fau]` | Full author name (2002+) | `smith john a[fau]` |

Corporate authors search as authors: `world health organization[au]`.

### Title / abstract

| Tag | Field | Example |
| --- | --- | --- |
| `[ti]` | Title | `diabetes[ti]` |
| `[ab]` | Abstract | `treatment[ab]` |
| `[tiab]` | Title/Abstract (most-used for recall) | `cancer screening[tiab]` |
| `[tw]` | Text word (title, abstract, and more) | `cardiovascular[tw]` |

### Journal

| Tag | Field | Example |
| --- | --- | --- |
| `[ta]` | Journal title abbreviation | `Science[ta]` |
| `[jour]` | Journal | `New England Journal of Medicine[jour]` |
| `[issn]` | ISSN | `0028-4793[issn]` |

### Date

| Tag | Field | Example |
| --- | --- | --- |
| `[dp]` | Publication date | `2023[dp]` |
| `[edat]` | Entrez date | `2023/01/15[edat]` |
| `[crdt]` | Create date | `2023[crdt]` |
| `[mhda]` | MeSH date | `2023[mhda]` |

Ranges use a colon: `2020:2023[dp]`, `2023/01/01:2023/06/30[dp]`.

### MeSH and subheadings

| Tag | Field | Example |
| --- | --- | --- |
| `[mh]` / `[mesh]` | MeSH term (auto-includes narrower terms) | `diabetes mellitus[mh]` |
| `[majr]` | MeSH major topic (main focus only) | `hypertension[majr]` |
| `[sh]` | MeSH subheading | `therapy[sh]` |

Attach a subheading with `/`: `diabetes mellitus/therapy[mh]`. Common subheadings:
`/diagnosis`, `/drug therapy`, `/epidemiology`, `/etiology`, `/prevention & control`, `/therapy`.

### Publication type

`[pt]` — filter by study design. Common values: Clinical Trial, Randomized Controlled Trial,
Meta-Analysis, Systematic Review, Review, Case Reports, Guideline, Practice Guideline, Letter,
Editorial. Example: `cancer AND systematic review[pt]`.

### Other useful fields

| Tag | Field | | Tag | Field |
| --- | --- | --- | --- | --- |
| `[la]` | Language | | `[pmid]` | PubMed ID |
| `[affil]` | Affiliation | | `[pmc]` | PMC ID |
| `[doi]` | DOI | | `[nm]` | Substance name |
| `[gr]` | Grant number | | `[ps]` | Personal name as subject |
| `[vi]` | Volume | | `[ip]` | Issue |
| `[pg]` | Pagination | | `[sb]` | Subset (e.g. `free full text[sb]`) |

## Automatic Term Mapping (ATM)

An untagged term is expanded in order against: (1) the MeSH translation table, (2) the journal
table, (3) the author index, then (4) searched as text. This boosts recall but can silently
change what you searched. **Bypass ATM** with quotes (`"breast cancer"`) or a field tag
(`breast cancer[tiab]`). **View the translation** in Advanced Search → Search Details.

## Filters and limits

Article type (Clinical Trial, Meta-Analysis, RCT, Review, Systematic Review); text availability
(Free full text, Full text, Abstract); publication date (last 1/5/10 years, custom); species
(Humans, Animals); sex; age group (Infant, Child, Adolescent, Adult, Aged, 80+); language.
Clinical Queries provide pre-built hedges for Therapy/Diagnosis/Etiology/Prognosis (narrow/broad)
and Medical Genetics.

## Search history (web Advanced Search)

Holds up to 100 searches, expires after ~8 hours of inactivity. Combine with `#` references:

```
#1  diabetes mellitus[mh]
#2  cardiovascular diseases[mh]
#3  #1 AND #2 AND risk factors[tiab]
```

## Special characters

| Char | Purpose | Example |
| --- | --- | --- |
| `*` | wildcard | `colo*r` |
| `" "` | phrase | `"breast cancer"` |
| `( )` | group | `(A OR B) AND C` |
| `:` | range | `2020:2023[dp]` |
| `/` | MeSH subheading | `diabetes/therapy[mh]` |

## Troubleshooting

- **Too many results:** add specific terms, tag fields, restrict date, add a `[pt]` filter, AND another concept.
- **Too few results:** drop restrictive terms, OR in synonyms, remove tags, widen the date range, remove filters.
- **No results:** run `espell.fcgi` to check spelling, try alternate terminology, remove tags, confirm you are on PubMed (not PMC).
- **Unexpected results:** open Search Details to see the ATM translation; tag/quote terms to suppress unwanted expansion.
