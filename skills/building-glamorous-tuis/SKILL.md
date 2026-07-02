---
name: building-glamorous-tuis
version: 0.1.0
description: >-
  Build terminal UIs with Charmbracelet (Bubble Tea, Lip Gloss, Gum). Use when:
  Go TUI, shell prompts/spinners, "make CLI prettier", adaptive layouts, async
  rendering, focus state machines, sparklines, heatmaps, kanban boards, SSH apps.
  Not for: piped/non-interactive output, CI/CD pipelines, or a single trivial
  prompt (use plain text, flags/env vars, or fmt.Scanf instead).
---

# Building Glamorous TUIs with Charmbracelet

## Quick Router — Start Here

| I need to... | Use | Reference |
|--------------|-----|-----------|
| **Add prompts/spinners to a shell script** | Gum (no Go) | [Shell Scripts](references/shell-scripts.md) |
| **Build a Go TUI** | Bubble Tea + Lip Gloss | [Go TUI](references/go-tui.md) |
| **Build a production-grade Go TUI** | Above + elite patterns | [Production Architecture](references/production-architecture.md) |
| **Serve a TUI over SSH** | Wish + Bubble Tea | [Infrastructure](references/infrastructure.md) |
| **Record a terminal demo** | VHS | [Shell Scripts](references/shell-scripts.md#vhs-terminal-recording) |
| **Find a Bubbles component** | list, table, viewport, spinner, progress... | [Component Catalog](references/component-catalog.md) |
| **Get a copy-paste pattern** | Layouts, forms, animation, testing | [Quick Reference](references/QUICK-REFERENCE.md) / [Advanced Patterns](references/advanced-patterns.md) |

---

## Decision Guide

```
Is it a shell script?
├─ Yes → Use Gum
│        Need recording? → VHS
│        Need AI? → Mods
│
└─ No (Go application)
   │
   ├─ Just styled output? → Lip Gloss only
   ├─ Simple prompts/forms? → Huh standalone
   ├─ Full interactive TUI? → Bubble Tea + Bubbles + Lip Gloss
   │  │
   │  └─ Production-grade?  → Also add elite patterns:
   │     (multi-view, data-    two-phase async, immutable snapshots,
   │      dense, must be       adaptive layout, focus state machine,
   │      fast & polished)     semantic theming, pre-computed styles
   │                           → See Production Architecture reference
   │
   └─ Need SSH access? → Wish + Bubble Tea
```

---

## Shell Scripts (No Go Required)

```bash
brew install gum  # One-time install
```

```bash
# Input
NAME=$(gum input --placeholder "Your name")

# Selection
COLOR=$(gum choose "red" "green" "blue")

# Fuzzy filter from stdin
BRANCH=$(git branch | gum filter)

# Confirmation
gum confirm "Continue?" && echo "yes"

# Spinner
gum spin --title "Working..." -- long-command

# Styled output
gum style --border rounded --padding "1 2" "Hello"
```

**[Full Gum Reference →](references/shell-scripts.md#gum-the-essential-tool)**
**[VHS Recording →](references/shell-scripts.md#vhs-terminal-recording)**
**[Mods AI →](references/shell-scripts.md#mods-ai-in-terminal)**

---

## Go Applications

```bash
go get github.com/charmbracelet/bubbletea github.com/charmbracelet/lipgloss
```

### Minimal TUI (Copy & Run)

```go
package main

import (
    "fmt"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
)

var highlight = lipgloss.NewStyle().Foreground(lipgloss.Color("212")).Bold(true)

type model struct {
    items  []string
    cursor int
}

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "q", "ctrl+c":
            return m, tea.Quit
        case "up", "k":
            if m.cursor > 0 { m.cursor-- }
        case "down", "j":
            if m.cursor < len(m.items)-1 { m.cursor++ }
        case "enter":
            fmt.Printf("Selected: %s\n", m.items[m.cursor])
            return m, tea.Quit
        }
    }
    return m, nil
}

func (m model) View() string {
    s := ""
    for i, item := range m.items {
        if i == m.cursor {
            s += highlight.Render("▸ "+item) + "\n"
        } else {
            s += "  " + item + "\n"
        }
    }
    return s + "\n(↑/↓ move, enter select, q quit)"
}

func main() {
    m := model{items: []string{"Option A", "Option B", "Option C"}}
    tea.NewProgram(m).Run()
}
```

### Library Cheat Sheet

| Need | Library | Example |
|------|---------|---------|
| TUI framework | `bubbletea` | `tea.NewProgram(model).Run()` |
| Components | `bubbles` | `list.New()`, `textinput.New()` |
| Styling | `lipgloss` | `style.Foreground(lipgloss.Color("212"))` |
| Forms | `huh` | `huh.NewInput().Title("Name").Run()` |
| Markdown | `glamour` | `glamour.Render(md, "dark")` |
| Animation | `harmonica` | `harmonica.NewSpring()` |

**[Full Go TUI Guide →](references/go-tui.md)**
**[All Bubbles Components →](references/component-catalog.md)**
**[Layout & Animation Patterns →](references/advanced-patterns.md)**

---

## SSH Apps (Infrastructure)

```go
s, _ := wish.NewServer(
    wish.WithAddress(":2222"),
    wish.WithHostKeyPath(".ssh/key"),
    wish.WithMiddleware(
        bubbletea.Middleware(handler),
        logging.Middleware(),
    ),
)
s.ListenAndServe()
```

Connect: `ssh localhost -p 2222`

**[Full Infrastructure Guide →](references/infrastructure.md)**

---

## Production TUI Architecture (Elite Patterns)

Beyond basic Bubble Tea: patterns that make TUIs feel fast, polished, and professional.
Match your symptom to a category, then jump to the full symptom→pattern→code table
in [Production Architecture](references/production-architecture.md).

| If your TUI is... | Look for patterns like | Section |
|-------------------|------------------------|---------|
| **slow or janky** | two-phase async, immutable snapshots, pre-computed styles, `strings.Builder`, cached markdown, object pooling, viewport virtualization | [Performance](references/production-architecture.md#two-phase-async-architecture) |
| **breaking on different terminals** | adaptive layout breakpoints, `AdaptiveColor` semantic theming, deterministic stable sorting, dynamic status bar | [Layout](references/production-architecture.md#adaptive-layout-engine) |
| **a messy multi-view app** | focus state machine, breadcrumbs, focus restoration, stale-message detection, `tea.Batch`, goroutine error recovery | [Multi-View](references/production-architecture.md#multi-view-focus-state-machine) |
| **lacking data viz** | Unicode sparklines, perceptual heatmaps, ASCII graph renderer, age/border color coding | [Data Viz](references/production-architecture.md#data-visualization-sparklines--heatmaps) |
| **not polished enough** | vim combos, debounced search, composite filter, rich delegates, clipboard, multi-tier help, kanban, tree nav, editor dispatch, persistent state, env prefs | [Polish](references/production-architecture.md#vim-key-combo-tracking) |

**[Full Production Architecture Guide (all patterns + code) →](references/production-architecture.md)**

---

## Pre-Flight Checklist (Every TUI)

- [ ] Handle `tea.WindowSizeMsg` — resize all components
- [ ] Handle `ctrl+c` — cleanup, restore terminal state
- [ ] Detect piped stdin/stdout — fall back to plain text
- [ ] Test on 80×24 minimum terminal
- [ ] Provide `--no-tui` / `NO_TUI` escape hatch
- [ ] Test with both light AND dark backgrounds
- [ ] Test with `NO_COLOR=1` and `TERM=dumb`

For production TUIs, see the [full checklist](references/production-architecture.md#production-pre-flight-checklist) (16 must-have + 20 polish items).

---

## When NOT to Use Charm

- **Output is piped:** `mytool | grep` → plain text
- **CI/CD:** No terminal → use flags/env vars
- **One simple prompt:** Maybe `fmt.Scanf` is fine

**Escape hatch:**
```go
if !term.IsTerminal(os.Stdin.Fd()) || os.Getenv("NO_TUI") != "" {
    runPlainMode()
    return
}
```

---

## All References

| I need... | Read this |
|-----------|-----------|
| Copy-paste one-liners | [Quick Reference](references/QUICK-REFERENCE.md) |
| Prompts to give Claude for TUI tasks | [Prompts](references/PROMPTS.md) |
| Gum / VHS / Mods / Freeze / Glow | [Shell Scripts](references/shell-scripts.md) |
| Bubble Tea architecture, debugging, anti-patterns | [Go TUI](references/go-tui.md) |
| Bubbles component APIs (list, table, viewport...) | [Component Catalog](references/component-catalog.md) |
| Theming, layouts, animation, Huh forms, testing | [Advanced Patterns](references/advanced-patterns.md) |
| Elite patterns: async, snapshots, focus machines, adaptive layout, sparklines, kanban, trees, caching | [Production Architecture](references/production-architecture.md) |
| Wish SSH server, Soft Serve, teatest | [Infrastructure](references/infrastructure.md) |
