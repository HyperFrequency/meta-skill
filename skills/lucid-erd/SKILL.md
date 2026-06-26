---
name: lucid-erd
description: Create an Entity Relationship Diagram in Lucidchart. Use when asked to document database schema, table relationships, data models, or database changes.
---

# Lucid ERD — Entity Relationship Diagram

Create professional ERD diagrams using UML Class shapes and push them to Lucidchart.

## When to Use

- User wants to document database tables and relationships
- User needs a data model diagram
- User asks to visualize schema changes (new/modified/deleted tables)
- User wants an ERD page for a design document

## Process

1. **Understand the schema**: Ask about tables, fields, relationships, what's new/changed
2. **Classify tables**: Existing (white), New (green), Modified (blue), Deleted (red)
3. **Map relationships**: Identify FK relationships and cardinality
4. **Build Standard Import JSON**: Follow the rules below
5. **Push to Lucidchart**: Use `mcp__LucidChart__lucid_create_diagram_from_specification`

## Standard Import Structure

```json
{
  "version": 1,
  "pages": [{
    "id": "page-erd",
    "title": "ERD",
    "shapes": [
      { "legend table" },
      ...uml_class_entities,
      ...notes
    ],
    "lines": [ ...relationships ]
  }]
}
```

## Legend Table

```json
{
  "id": "legend",
  "type": "table",
  "boundingBox": {"x": 30, "y": 30, "w": 600, "h": 35},
  "rowCount": 1,
  "colCount": 8,
  "cells": [
    {"xPosition": 0, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#FFFFFF"}}},
    {"xPosition": 1, "yPosition": 0, "text": "Existing Table"},
    {"xPosition": 2, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#D5F5E3"}}},
    {"xPosition": 3, "yPosition": 0, "text": "New Table"},
    {"xPosition": 4, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#D6EAF8"}}},
    {"xPosition": 5, "yPosition": 0, "text": "Modified Table"},
    {"xPosition": 6, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#FADBD8"}}},
    {"xPosition": 7, "yPosition": 0, "text": "Deleted Table"}
  ]
}
```

## Entity (UML Class)

```json
{
  "id": "table_name",
  "type": "umlClass",
  "boundingBox": {"x": 30, "y": 90, "w": 270, "h": 380},
  "title": "table_name",
  "properties": [
    "PK id: int",
    "FK partner_id: int",
    "name: varchar(255)",
    "created_at: timestamp"
  ],
  "methods": [],
  "style": {
    "fill": {"type": "color", "color": "<status_fill>"},
    "stroke": {"color": "<status_stroke>", "width": 1, "style": "solid"}
  }
}
```

### Entity Sizing
- **Width**: 270px (consistent)
- **Height**: `80 + (num_fields * 22)`, minimum 200px
- **Max fields**: 20 (truncate with note if more)

### Entity Colors

| Status | Fill | Stroke | Width |
|--------|------|--------|-------|
| Existing | `#FFFFFF` | `#000000` | 1 |
| New | `#D5F5E3` | `#2ECC71` | 2 |
| Modified | `#D6EAF8` | `#3498DB` | 2 |
| Deleted | `#FADBD8` | `#E74C3C` | 2 |

### Field Format

```
"PK id: int"                    — Primary key
"FK,UK2 program_id: int"        — Foreign + unique key
"FK customer_id: int"           — Foreign key
"UK email_hash: varchar(32)"    — Unique key
"name: varchar(255)"            — Regular field
"status: enum(active,inactive)" — Enum
"created_at: timestamp"         — Timestamp
"data: json"                    — JSON
```

Format: `[KEY_MARKERS] field_name: type`

### Methods Array
- Usually empty `[]`
- Use for unique constraints: `["UK (program_id, segment_id)"]`

## Entity Layout

Horizontal row, 40px gap:
```
Entity 1: x = 30
Entity 2: x = 340 (30 + 270 + 40)
Entity 3: x = 650
Entity 4: x = 960
```

Second row if needed: `y = first_row_y + tallest_entity + 60`

## Relationship Lines

```json
{
  "id": "rel-users-programs",
  "lineType": "elbow",
  "endpoint1": {
    "type": "shapeEndpoint",
    "style": "oneOrMore",
    "shapeId": "users",
    "position": {"x": 1, "y": 0.15}
  },
  "endpoint2": {
    "type": "shapeEndpoint",
    "style": "one",
    "shapeId": "program_registrations",
    "position": {"x": 0, "y": 0.15}
  },
  "stroke": {"color": "#000000", "width": 1, "style": "solid"}
}
```

### Cardinality Styles

| Relationship | endpoint1 | endpoint2 |
|-------------|-----------|-----------|
| One-to-Many | `oneOrMore` | `one` |
| One-to-One | `one` | `one` |
| Many-to-Many | `oneOrMore` | `oneOrMore` |
| Zero-or-More | `zeroOrMore` | `one` |

### Relationship Rules
- Use `position` on **BOTH** endpoints (x: 0/1 for left/right, y: 0.1-0.9)
- Adjacent entities: connect left-to-right
- Non-adjacent: use smart lines (omit position)
- Stroke: `#000000`, width 1, solid
- No labels on relationship lines

## Notes (Optional)

```json
{
  "id": "note-1",
  "type": "note",
  "boundingBox": {"x": 30, "y": 550, "w": 300, "h": 80},
  "text": "Context about a table or field",
  "style": {"fill": {"type": "color", "color": "#FFFDE7"}, "stroke": {"color": "#F1C40F", "width": 1, "style": "solid"}}
}
```

## Checklist

- [ ] Legend table with status colors
- [ ] All entities use `umlClass` type
- [ ] Width consistent (270px)
- [ ] Height calculated from field count
- [ ] Fields formatted as `KEY field_name: type`
- [ ] Colors match status
- [ ] Relationships use correct cardinality
- [ ] Position set on BOTH endpoints
- [ ] Entity IDs = table names (snake_case)
- [ ] All IDs unique
