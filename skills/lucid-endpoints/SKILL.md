---
name: lucid-endpoints
description: Create API endpoint documentation tables in Lucidchart. Use when asked to document API endpoints, service integrations, or external API specifications.
---

# Lucid Endpoints — API Documentation Tables

Create professional API endpoint documentation tables and push them to Lucidchart.

## When to Use

- User wants to document external API endpoints (Twilio, Stripe, etc.)
- User needs to list internal API routes
- User asks to create endpoint reference tables
- User wants an API documentation page

## Process

1. **Understand the APIs**: Ask about endpoints, methods, environments, parameters
2. **Group by service**: Each API or group gets its own table
3. **Build Standard Import JSON**: Follow the rules below
4. **Push to Lucidchart**: Use `mcp__LucidChart__lucid_create_diagram_from_specification`

## Standard Import Structure

```json
{
  "version": 1,
  "pages": [{
    "id": "page-endpoints",
    "title": "API Endpoints",
    "shapes": [ ...tables ],
    "lines": []
  }]
}
```

## Service Endpoint Table

```json
{
  "id": "api-verify",
  "type": "table",
  "boundingBox": {"x": 30, "y": 30, "w": 1100, "h": 200},
  "rowCount": 5,
  "colCount": 3,
  "cells": [
    {"xPosition": 0, "yPosition": 0, "text": "Service Name - Endpoint", "style": {"fill": {"type": "color", "color": "#2C3E50"}}, "mergeCellsRight": 2},
    {"xPosition": 0, "yPosition": 1, "text": "Base URL", "style": {"fill": {"type": "color", "color": "#EBF5FB"}}},
    {"xPosition": 1, "yPosition": 1, "text": "Staging/UAT"},
    {"xPosition": 2, "yPosition": 1, "text": "https://api.example.com"},
    {"xPosition": 0, "yPosition": 2, "text": "Endpoint", "style": {"fill": {"type": "color", "color": "#EBF5FB"}}},
    {"xPosition": 1, "yPosition": 2, "text": "All Environments"},
    {"xPosition": 2, "yPosition": 2, "text": "POST /v2/resource"},
    {"xPosition": 0, "yPosition": 3, "text": "Description", "style": {"fill": {"type": "color", "color": "#EBF5FB"}}},
    {"xPosition": 1, "yPosition": 3, "text": "What the endpoint does", "mergeCellsRight": 1},
    {"xPosition": 0, "yPosition": 4, "text": "Parameters", "style": {"fill": {"type": "color", "color": "#EBF5FB"}}},
    {"xPosition": 1, "yPosition": 4, "text": "param1: description\nparam2: description", "mergeCellsRight": 1}
  ]
}
```

### Table Rules
- **Width**: 1100px for all tables
- **Row height**: ~40px per row
- **Table height**: `rowCount * 40`
- **Spacing**: 30px gap between stacked tables
- **Title row**: `#2C3E50` fill, `mergeCellsRight: 2` for full width
- **Label cells**: `#EBF5FB` fill
- **Description/Parameters rows**: `mergeCellsRight: 1` for wide content

### Table Stacking
```
Table 1: y = 30
Table 2: y = 30 + table1_height + 30
Table 3: y = 30 + table1_height + 30 + table2_height + 30
```

## Route List Table (Alternative)

For listing many internal routes:

```json
{
  "id": "routes",
  "type": "table",
  "boundingBox": {"x": 30, "y": 30, "w": 1100, "h": 400},
  "rowCount": 10,
  "colCount": 4,
  "cells": [
    {"xPosition": 0, "yPosition": 0, "text": "Method", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 1, "yPosition": 0, "text": "Endpoint", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 2, "yPosition": 0, "text": "Description", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 3, "yPosition": 0, "text": "Auth", "style": {"fill": {"type": "color", "color": "#2C3E50"}}},
    {"xPosition": 0, "yPosition": 1, "text": "POST", "style": {"fill": {"type": "color", "color": "#D6EAF8"}}},
    {"xPosition": 1, "yPosition": 1, "text": "/api/v1/register"},
    {"xPosition": 2, "yPosition": 1, "text": "User registration"},
    {"xPosition": 3, "yPosition": 1, "text": "Public"}
  ]
}
```

### Method Color Coding (optional)

| Method | Cell Fill |
|--------|----------|
| GET | `#D5F5E3` |
| POST | `#D6EAF8` |
| PUT/PATCH | `#FDEBD0` |
| DELETE | `#FADBD8` |

## Checklist

- [ ] All tables 1100px wide
- [ ] Title rows `#2C3E50` with `mergeCellsRight`
- [ ] Label cells `#EBF5FB`
- [ ] Tables stacked with 30px gaps
- [ ] Endpoints include HTTP method
- [ ] Description rows use `mergeCellsRight`
- [ ] All IDs unique
