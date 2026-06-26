---
name: lucidflow
description: Create diagrams and push to Lucidchart. Routes to the best specialized skill based on diagram type. Use when asked to create any visual diagram, flowchart, ERD, or documentation diagram.
---

# LucidFlow — Diagram Router

Create professional diagrams and push them directly to Lucidchart. This skill routes to the best specialized sub-skill based on what diagram type the user needs.

## Diagram Type Router

| User Asks For | Use Skill | Why |
|--------------|-----------|-----|
| Flow between systems, sequence diagram, API interaction | `/lucid-flow` | Color-coded shapes per system, edge-driven layout |
| API changes, impact analysis, migration tracking | `/lucid-changes` | Color-coded category tables |
| Database schema, ERD, data model | `/lucid-erd` | UML Class shapes as entities with relationships |
| API documentation, endpoint reference | `/lucid-endpoints` | Structured tables per service |

## How It Works

Each skill generates **Lucid Standard Import JSON** and pushes directly to Lucidchart via `mcp__LucidChart__lucid_create_diagram_from_specification`. Lucid's assisted layout arranges shapes based on edge connections — producing clean, readable diagrams automatically.

## Critical Design Rules

These rules are baked into every skill. They come from extensive testing of what produces the best results with Lucid's assisted layout engine.

### DO
- Use **flat color-coded shapes** with `<b>System Name</b><br>Description`
- Use **tables** for structured data (they're fixed-size, immune to layout changes)
- Use **smart lines** (no `position` on endpoints) — let Lucid route edges
- Use **`elbow`** line type for all edges
- Use **2px stroke** on shapes and lines for visual weight
- Use **`#2C3E50`** fill for table headers (auto white text)
- Use **legend as single-row table** for color key
- Use **HTML** in shapes: `<b>`, `<i>`, `<br>` all work
- Keep edge labels **short** (1-4 words)

### DO NOT
- Use **swim lanes** or any container type — assisted layout pulls shapes out
- Use **rectangleContainer** — children get rearranged
- Use **pixel-perfect positioning** — assisted layout overrides everything
- Use **small shapes** (< 100px) — they get compressed
- Put **HTML** in table cells — renders literally
- Use **long edge labels** — they overlap shapes

## Color Palette

| Purpose | Fill | Stroke |
|---------|------|--------|
| Frontend/Client | `#FADBD8` | `#E8607C` |
| Backend API | `#D6EAF8` | `#3498DB` |
| External Service | `#D5F5E3` | `#27AE60` |
| Database/Cache | `#E8DAEF` | `#9B59B6` |
| Message Queue | `#FDEBD0` | `#E67E22` |
| Decision | `#F9E79F` | `#F1C40F` |
| Success | `#ABEBC6` | `#27AE60` |
| Error | `#F5B7B1` | `#E74C3C` |
| Dark header | `#2C3E50` | — |

## Quick Start

If the user asks to create a diagram, identify the type and invoke the matching skill. If unclear, ask which type they need.
