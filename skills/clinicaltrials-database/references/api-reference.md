# ClinicalTrials.gov API v2 — Reference

Public REST API for the U.S. NLM clinical study registry. No authentication.
OpenAPI 3.0. JSON (default) or CSV. Interactive docs and the authoritative field
dictionary live at `https://clinicaltrials.gov/data-api/api`.

- **Base URL:** `https://clinicaltrials.gov/api/v2`
- **Auth:** none
- **Rate limit:** ~50 requests/minute per IP
- **Standards:** ISO 8601 dates, CommonMark Markdown in rich-text fields
- API v2 replaced the classic API (classic retired mid-2024).

## Endpoints

### `GET /studies` — search / list

| Parameter | Type | Description | Example |
| --- | --- | --- | --- |
| `query.cond` | string | Condition/disease (relevance search) | `lung cancer` |
| `query.intr` | string | Intervention/drug/device/procedure | `Pembrolizumab` |
| `query.locn` | string | Location text | `New York` |
| `query.spons` | string | Sponsor or collaborator | `National Cancer Institute` |
| `query.term` | string | General full-text | `breast cancer treatment` |
| `filter.overallStatus` | string | Status enum(s), comma-separated | `RECRUITING,NOT_YET_RECRUITING` |
| `filter.phase` | string | Phase enum(s), comma-separated | `PHASE2,PHASE3` |
| `filter.ids` | string | Restrict to NCT IDs, comma-separated | `NCT04852770,NCT01728545` |
| `filter.geo` | string | Geographic radius function | `distance(39.0,-77.1,50mi)` |
| `filter.advanced` | string | Essie expression over any field | `AREA[MinimumAge]RANGE[18 years, MAX]` |
| `fields` | string | Dot-path field names to return (payload trimming) | `protocolSection.identificationModule.nctId` |
| `sort` | string | Result ordering | `LastUpdatePostDate:desc` |
| `countTotal` | boolean | **Required to populate `totalCount`** | `true` |
| `pageSize` | integer | Results per page (max `1000`) | `100` |
| `pageToken` | string | Value of prior response's `nextPageToken` | `<token>` |
| `format` | string | `json` (default) or `csv` | `csv` |

`query.*` parameters accept advanced search expressions — quoted phrases and
`AND`/`OR`/`NOT` operators. `filter.geo` uses `distance(lat, long, radius)` with a
unit suffix (`mi` or `km`). `filter.advanced` accepts the ClinicalTrials.gov "Essie"
expression syntax (`AREA[Field]`, `RANGE[..]`, `EXPANSION[..]`); consult the interactive
docs for the exact grammar before relying on complex expressions.

### `GET /studies/{NCT_ID}` — single study

| Parameter | Type | Description |
| --- | --- | --- |
| `NCT_ID` (path) | string | e.g. `NCT04852770` |
| `format` | string | `json` (default) or `csv` |
| `fields` | string | Dot-path field names to return |

## Enumerated values

**Overall status** (`filter.overallStatus`) — 14 values. Interventional/observational:
`RECRUITING`, `NOT_YET_RECRUITING`, `ENROLLING_BY_INVITATION`, `ACTIVE_NOT_RECRUITING`,
`SUSPENDED`, `TERMINATED`, `COMPLETED`, `WITHDRAWN`, `UNKNOWN` (recruitment status not
verified in 2+ years — common in older records; do not treat as "closed").
Expanded-access records use five more: `AVAILABLE`, `NO_LONGER_AVAILABLE`,
`TEMPORARILY_NOT_AVAILABLE`, `APPROVED_FOR_MARKETING`, `WITHHELD`.

**Phase** (`filter.phase` / `designModule.phases`):
`EARLY_PHASE1`, `PHASE1`, `PHASE2`, `PHASE3`, `PHASE4`, `NA`.

**Sort keys** (append `:asc` or `:desc`):
`LastUpdatePostDate`, `StudyFirstPostDate`, `StartDate`, `EnrollmentCount`.

## Response shape (`/studies`)

```json
{
  "studies": [
    { "protocolSection": { ... }, "derivedSection": { ... },
      "resultsSection": { ... }, "hasResults": false }
  ],
  "totalCount": 1234,          // only present when countTotal=true
  "nextPageToken": "abc123"    // absent on the last page
}
```

Pagination contract: send `pageToken=<nextPageToken>` on the next request. The
response field is `nextPageToken`; the request parameter is `pageToken`.

## Study modules

### `protocolSection`

| Module | Contents |
| --- | --- |
| `identificationModule` | `nctId`, `briefTitle`, `officialTitle`, `organization` |
| `statusModule` | `overallStatus`, `startDateStruct`, `completionDateStruct`, `lastUpdatePostDateStruct` |
| `sponsorCollaboratorsModule` | `leadSponsor`, `collaborators`, `responsibleParty` |
| `descriptionModule` | `briefSummary`, `detailedDescription` |
| `conditionsModule` | `conditions`, `keywords` |
| `designModule` | `studyType`, `phases`, `enrollmentInfo.count`, design details |
| `armsInterventionsModule` | `armGroups`, `interventions` |
| `outcomesModule` | `primaryOutcomes`, `secondaryOutcomes` |
| `eligibilityModule` | `eligibilityCriteria`, `minimumAge`, `maximumAge`, `sex`, `healthyVolunteers` |
| `contactsLocationsModule` | `centralContacts`, `overallOfficials`, `locations` |
| `referencesModule` | `references`, `seeAlsoLinks` |

### `derivedSection`

`miscInfoModule` (version holder, removed countries), `conditionBrowseModule`
(condition MeSH terms), `interventionBrowseModule` (intervention MeSH terms).

### `resultsSection` (only when `hasResults` is true)

`participantFlowModule`, `baselineCharacteristicsModule`, `outcomeMeasuresModule`,
`adverseEventsModule`.

## Frequently used field paths

| Value | Path |
| --- | --- |
| NCT ID | `protocolSection.identificationModule.nctId` |
| Brief title | `protocolSection.identificationModule.briefTitle` |
| Overall status | `protocolSection.statusModule.overallStatus` |
| Phases | `protocolSection.designModule.phases` |
| Enrollment | `protocolSection.designModule.enrollmentInfo.count` |
| Last update date | `protocolSection.statusModule.lastUpdatePostDateStruct.date` |
| Eligibility text | `protocolSection.eligibilityModule.eligibilityCriteria` |
| Locations | `protocolSection.contactsLocationsModule.locations` |
| Interventions | `protocolSection.armsInterventionsModule.interventions` |

## Data standards

**Dates** are structured objects with a `type` (`ACTUAL` vs `ESTIMATED`):

```json
"lastUpdatePostDateStruct": { "date": "2024-03-15", "type": "ACTUAL" }
```

**Rich text** (`briefSummary`, `detailedDescription`, `eligibilityCriteria`) is
CommonMark Markdown — render or strip accordingly. Many categorical fields are
enumerated rather than free text, so filter on exact enum tokens.

## HTTP status codes

| Code | Meaning | Action |
| --- | --- | --- |
| `200` | OK | proceed |
| `400` | Bad request | fix invalid enum / malformed parameter |
| `404` | Not found | verify the NCT ID |
| `429` | Rate limited | back off (~60 s) and retry |
| `500` | Server error | retry with backoff |

## Migration from the classic API

Key changes vs the retired classic API: enumerated values instead of free text,
ISO 8601 date structs, CommonMark rich text, properly typed numeric fields, and
token-based pagination. Official guide:
`https://clinicaltrials.gov/data-api/about-api/api-migration`.
