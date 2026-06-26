---
name: lucid-changes
description: Create a color-coded API changes/impact table in Lucidchart. Use when asked to document code changes, API modifications, database migrations, or feature impact analysis.
---

# Lucid Changes — Impact Analysis Table

Create professional color-coded change tracking tables and push them to Lucidchart.

## When to Use

- User wants to document API changes for a feature
- User needs an impact analysis table
- User wants to track database migrations, endpoint changes, or code modifications
- User asks to create a changes page for a design document

## Process

1. **Understand the changes**: Ask what systems/areas are affected
2. **Categorize**: Map each change to a category
3. **Build Standard Import JSON**: Follow the rules below
4. **Push to Lucidchart**: Use `mcp__LucidChart__lucid_create_diagram_from_specification`

## Category Colors

| Category | Fill | Use For |
|----------|------|---------|
| General changes | `#FDEBD0` | Migrations, seeds, configs |
| Admin routes | `#D6EAF8` | Admin panel endpoints |
| Member routes | `#D5F5E3` | Member-facing API endpoints |
| Application routes | `#FADBD8` | Internal app logic |
| External systems | `#E8DAEF` | Third-party integrations |

## Standard Import Structure

```json
{
  "version": 1,
  "pages": [{
    "id": "page-changes",
    "title": "API Changes",
    "shapes": [
      { "legend table" },
      { "main data table" }
    ],
    "lines": []
  }]
}
```

## Legend Table

```json
{
  "id": "legend",
  "type": "table",
  "boundingBox": {"x": 30, "y": 30, "w": 1100, "h": 35},
  "rowCount": 1,
  "colCount": 10,
  "cells": [
    {"xPosition": 0, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#FDEBD0"}}},
    {"xPosition": 1, "yPosition": 0, "text": "General changes"},
    {"xPosition": 2, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#D6EAF8"}}},
    {"xPosition": 3, "yPosition": 0, "text": "Admin routes"},
    {"xPosition": 4, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#D5F5E3"}}},
    {"xPosition": 5, "yPosition": 0, "text": "Member routes"},
    {"xPosition": 6, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#FADBD8"}}},
    {"xPosition": 7, "yPosition": 0, "text": "Application routes"},
    {"xPosition": 8, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#E8DAEF"}}},
    {"xPosition": 9, "yPosition": 0, "text": "External systems"}
  ]
}
```

## Main Table

```json
{
  "id": "main-table",
  "type": "table",
  "boundingBox": {"x": 30, "y": 85, "w": 1100, "h": 650},
  "rowCount": 13,
  "colCount": 3,
  "cells": [
    {"xPosition": 0, "yPosition": 0, "text": "Action", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 1, "yPosition": 0, "text": "Notes", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 2, "yPosition": 0, "text": "Endpoints To Update", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 0, "yPosition": 1, "text": "Change description", "style": {"fill": {"type": "color", "color": "<category_color>"}}},
    {"xPosition": 1, "yPosition": 1, "text": "Implementation notes", "style": {"fill": {"type": "color", "color": "<category_color>"}}},
    {"xPosition": 2, "yPosition": 1, "text": "POST /endpoint", "style": {"fill": {"type": "color", "color": "<category_color>"}}}
  ]
}
```

### Table Rules
- **Width**: always 1100px
- **Height**: calculate to fill page (~650px or `rowCount * 50`)
- **Header row**: `#2C3E50` fill (auto white text)
- **Data rows**: ALL 3 cells get the same category color
- **Row ordering**: group by category (General → Admin → Member → Application → External)

### Column Content
- **Action**: Start with verb ("Add", "Update", "Remove", "Create")
- **Notes**: 1-2 sentence technical explanation
- **Endpoints**: `METHOD /path` format, or "Migration"/"Seed" for DB changes

### Alternative Columns
- Database changes: `Action | Table | Fields`
- Config changes: `Action | Component | Configuration Key`
- UI changes: `Action | Screen/Component | Description`

## Checklist

- [ ] Legend table 1100px wide, single row
- [ ] Main table 1100px wide
- [ ] Header row `#2C3E50` (auto white text)
- [ ] ALL cells in each row have category color set
- [ ] Rows grouped by category
- [ ] Actions start with verbs
- [ ] No HTML in table cells
- [ ] All IDs unique
