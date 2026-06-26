---
name: lucid-flow
description: Create a color-coded flow diagram in Lucidchart. Use when asked to create flow diagrams, sequence flows, process diagrams, or any multi-system interaction flow.
---

# Lucid Flow — Color-Coded Flow Diagram

Create professional flow diagrams with color-coded shapes per system/actor and push them to Lucidchart.

## When to Use

- User describes a process flow involving multiple systems/actors
- User asks for a sequence diagram, interaction flow, or process diagram
- User wants to visualize API calls between services
- User asks to document a registration, login, checkout, or any multi-step flow

## Process

1. **Understand the flow**: Ask about systems involved, steps, decisions, error paths
2. **Assign colors**: Each system/actor gets a unique color pair (fill + stroke)
3. **Map the steps**: List every step, which system it belongs to, and connections
4. **Build Standard Import JSON**: Follow the rules below exactly
5. **Push to Lucidchart**: Use `mcp__LucidChart__lucid_create_diagram_from_specification`

## Key Design Principle

**NO swim lanes or containers.** Use flat color-coded shapes with bold system labels. Each shape includes `<b>System Name</b><br>Action description` so ownership is visible in the shape itself. Assisted layout arranges shapes based on edge connections.

## Standard Import Structure

```json
{
  "version": 1,
  "pages": [{
    "id": "page-flow",
    "title": "Flow Title",
    "shapes": [ ...shapes, { legend_table } ],
    "lines": [ ...edges ]
  }]
}
```

## System Colors

| System Type | Fill | Stroke |
|------------|------|--------|
| Frontend/Client | `#FADBD8` | `#E8607C` |
| Backend API | `#D6EAF8` | `#3498DB` |
| External Service | `#D5F5E3` | `#27AE60` |
| Database/Cache | `#E8DAEF` | `#9B59B6` |
| Message Queue | `#FDEBD0` | `#E67E22` |

## Shape Specs

### Process (action step)
```json
{
  "id": "step-id",
  "type": "process",
  "boundingBox": {"x": 50, "y": 50, "w": 260, "h": 55},
  "text": "<b>System Name</b><br>Action description\nOptional second line",
  "style": {"fill": {"type": "color", "color": "<fill>"}, "stroke": {"color": "<stroke>", "width": 2, "style": "solid"}}
}
```
- **260 x 55 px** | Always include `<b>System</b><br>` prefix | **2px stroke**

### Decision
```json
{
  "id": "decision-id",
  "type": "decision",
  "boundingBox": {"x": 460, "y": 170, "w": 140, "h": 90},
  "text": "Question\ntext?",
  "style": {"fill": {"type": "color", "color": "#F9E79F"}, "stroke": {"color": "#F1C40F", "width": 2, "style": "solid"}}
}
```
- **140 x 90 px** | ALWAYS yellow | No system prefix | **2px stroke**

### Terminator (end state)
```json
{
  "id": "end-id",
  "type": "terminator",
  "boundingBox": {"x": 460, "y": 660, "w": 200, "h": 40},
  "text": "Result description",
  "style": {"fill": {"type": "color", "color": "#ABEBC6"}, "stroke": {"color": "#27AE60", "width": 2, "style": "solid"}}
}
```
- **140-260 x 40 px** | Success=green, Error=red | **2px stroke**

## Edge Specs

```json
{
  "id": "e1",
  "lineType": "elbow",
  "endpoint1": {"type": "shapeEndpoint", "style": "none", "shapeId": "source-id"},
  "endpoint2": {"type": "shapeEndpoint", "style": "arrow", "shapeId": "target-id"},
  "stroke": {"color": "#333333", "width": 2, "style": "solid"},
  "text": [{"text": "Label", "position": 0.5, "side": "top"}]
}
```

### Critical Edge Rules
- **Always smart lines** — NO `position` on endpoints
- **Always `elbow`** line type
- **2px stroke** on all lines
- Normal flow: `#333333` solid
- Success: `#27AE60` solid, label "Yes"/"Valid"
- Error: `#E74C3C` dashed, label "No"/"Invalid"
- Skip/neutral: `#999999` dashed
- Retry: `#F39C12` dashed, label "No - retry"
- Labels: **1-4 words max** | `POST /register` | `OK 200` | `Yes`/`No`

## Legend Table

```json
{
  "id": "legend",
  "type": "table",
  "boundingBox": {"x": 750, "y": 600, "w": 300, "h": 35},
  "rowCount": 1,
  "colCount": 6,
  "cells": [
    {"xPosition": 0, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#FADBD8"}}},
    {"xPosition": 1, "yPosition": 0, "text": "Membersite"},
    {"xPosition": 2, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#D6EAF8"}}},
    {"xPosition": 3, "yPosition": 0, "text": "API"},
    {"xPosition": 4, "yPosition": 0, "text": " ", "style": {"fill": {"type": "color", "color": "#D5F5E3"}}},
    {"xPosition": 5, "yPosition": 0, "text": "Twilio"}
  ]
}
```
Adjust cell count and labels to match the systems in the diagram.

## Flow Design Tips

1. **Happy path first** — main success flow, then add error branches
2. **Edge order matters** — list edges in flow order, assisted layout uses this for column arrangement
3. **Max 15 shapes** per page — split larger flows into sub-flows
4. **Decisions always have 2 exits** — Yes/No, Valid/Invalid
5. **Omit label** when the connection is obvious

## Checklist

- [ ] Every process has `<b>System</b><br>` prefix
- [ ] Colors consistent per system
- [ ] Decisions always yellow, no system prefix
- [ ] All edges use smart lines (no position)
- [ ] Edge labels short (1-4 words)
- [ ] Success=solid green, Error=dashed red
- [ ] Legend table present
- [ ] All IDs unique
- [ ] Max ~15 shapes
