# Paper Mechanics Audit

Portions adapted from openscience (Apache-2.0).

A systematic pass over presentation details that human reviewers frequently
catch but automated reviews often miss: tables that state trends instead of
numbers, figures illegible at print size, undefined notation, and redundant
structure. Run this after the Stage 5 figure/data review; it catches mechanics
that the section-by-section pass does not.

Score each row Pass or Fail against the manuscript. A Fail is usually a **minor**
comment (clarity/presentation) unless it obscures the result itself — a table
reporting "Higher" with no numbers, or a figure whose data is unreadable, can
rise to a **major** comment because it blocks evaluation of the claims.

## Table Audit

| Check | Pass | Fail |
|-------|------|------|
| Numeric values | Has actual numbers | Uses "Higher", "Better", "↑" in place of values |
| Column headers | Clear, complete | Ambiguous abbreviations |
| Units specified | All units shown | Missing units |
| Significant figures | Appropriate precision | Excessive or insufficient |
| Caption completeness | Self-explanatory | Requires text to interpret |

## Figure Audit

| Check | Pass | Fail |
|-------|------|------|
| Legibility | Readable at 100% zoom | Tiny text, blurry lines |
| Axis labels | Present with units | Missing or unclear |
| Legend placement | Within figure, not over data | Overlapping data |
| Resolution | Print quality (300+ dpi) | Pixelated |
| Color scheme | Colorblind-friendly | Red-green only |

## Notation Audit

| Check | Pass | Fail |
|-------|------|------|
| Variable definitions | Defined before use | Used without definition |
| Consistency | Same symbol = same meaning | Reused symbols for different quantities |
| Standard notation | Follows field conventions | Idiosyncratic choices |

## Structure Audit

| Check | Pass | Fail |
|-------|------|------|
| Section redundancy | Each section has unique content | Repeated information |
| Cross-references | Figures/tables referenced in text | Orphan figures |
| Citation completeness | All claims supported | Unsupported assertions |

## Checklist Snippet

When finalizing, confirm the high-value mechanics:

- [ ] Tables contain numeric values (not just "Higher"/"Better"/arrows)
- [ ] Figures legible at 100% zoom, axes labeled with units
- [ ] Variables defined before first use; symbols used consistently
- [ ] No section redundancy; every figure/table is referenced in the text
- [ ] Every quantitative claim is supported by a citation or the paper's own data
