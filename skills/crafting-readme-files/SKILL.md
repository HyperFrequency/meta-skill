---
name: crafting-readme-files
version: 1.0.0
description: >-
  Craft professional README.md files for GitHub open source projects.
  Generates hero sections, installation instructions, feature tables, and
  architecture diagrams. Use when creating or revising a README, documenting
  a CLI tool, library, or open source project, or when user asks about
  README structure, badges, or project documentation.
---

# Crafting README.md Files for GitHub

> **Core insight:** A README is a sales pitch, onboarding guide, and reference manual compressed into one document. Lead with value, prove with examples, document with precision.

## Why This Matters

Most READMEs fail because they:
- Bury the value proposition under installation steps
- Explain what the tool IS instead of what problem it SOLVES
- Lack concrete examples (abstract descriptions don't sell)
- Miss the "quick escape hatch" for impatient users (curl one-liner)
- Don't show how it compares to alternatives

Great READMEs convert scanners into users in under 60 seconds.

---

## When To Use / When Not To Use

**Use this skill when:**
- Creating a new `README.md` for a GitHub open source project (CLI, library, app).
- Revising or restructuring an existing README that buries its value proposition.
- The user asks about README structure, section ordering, badges, hero sections,
  comparison tables, or an `AGENTS.md` reference blurb.

**Do NOT use this skill for:**
- Internal/private docs, design specs, RFCs, or wikis — this is tuned for the
  public open source "sales pitch + onboarding + reference" shape.
- API reference docs generated from code (use the doc generator for the language).
- Non-Markdown docs (Sphinx/reStructuredText, Docusaurus site config, man pages).
- Writing the actual code, changelog automation, or release tooling.

**References:** section-by-section copy-paste templates live in
[`references/section-templates.md`](references/section-templates.md) (Core +
Extended). Pull from there once you know which sections the project needs.

---

## THE EXACT PROMPT — README Revision

```
Read the current README.md and dramatically revise it following this structure:

1. Hero section: illustration + badges + one-liner description + curl install
2. TL;DR: "The Problem" + "The Solution" + "Why Use X?" feature table
3. Quick example showing the tool in action (5-10 commands)
4. Design philosophy (3-5 principles with explanations)
5. Comparison table vs alternatives
6. Installation (curl one-liner, package managers, from source)
7. Quick start (numbered steps, copy-paste ready)
8. Command reference (every command with examples)
9. Configuration (full config file example with comments)
10. Architecture diagram (ASCII art showing data flow)
11. Troubleshooting (common errors with fixes)
12. Limitations (honest about what it doesn't do)
13. FAQ (anticipate user questions)

Make it comprehensive but scannable. Use tables for comparisons.
Show, don't tell. Every claim should have a concrete example.
Use ultrathink.
```

---

## Golden Structure

```
1. HERO SECTION (above the fold)
   ├─ Illustration/logo (centered)
   ├─ Badges (CI, license, version)
   ├─ One-liner description
   └─ Quick install (curl | bash)

2. TL;DR (sell the value)
   ├─ The Problem (pain point)
   ├─ The Solution (what this does)
   └─ Why Use X? (feature table)

3. QUICK EXAMPLE (prove it works)
   └─ 5-10 commands showing core workflow

4. REFERENCE SECTIONS
   ├─ Design Philosophy
   ├─ Comparison vs Alternatives
   ├─ Installation (multiple paths)
   ├─ Quick Start
   ├─ Commands
   ├─ Configuration
   └─ Architecture

5. SUPPORT SECTIONS
   ├─ Troubleshooting
   ├─ Limitations
   ├─ FAQ
   ├─ Contributing
   └─ License
```

---

## Section Templates → `references/section-templates.md`

Copy-paste templates for every section live in
[`references/section-templates.md`](references/section-templates.md). Load it
when you are actually writing sections.

- **Core Section Templates**: Hero, TL;DR, Quick Example, Comparison,
  Installation, Command Reference, Architecture, Troubleshooting, Limitations,
  FAQ, and the Badge reference.
- **Extended Section Templates**: Performance, Security, Data Model, API
  Reference, Migration/Upgrade, expanded Contributing, Ecosystem/Integration,
  Environment Variables, Shell Completions, Release Notes, Acknowledgments.

This SKILL.md stays a router (the structure, rules, and anti-patterns); the
reference file carries the bulk markdown.

---

## Critical Rules

1. **Lead with value, not installation** — TL;DR before Quick Start
2. **Curl one-liner above the fold** — Impatient users escape hatch
3. **Every feature claim needs an example** — Show, don't tell
4. **Comparison tables beat prose** — Scannable > readable
5. **Be honest about limitations** — Builds trust, saves support time
6. **Multiple installation paths** — curl, package manager, source
7. **Architecture diagrams for complex tools** — ASCII art is fine
8. **Troubleshooting section is mandatory** — Top 5 errors with fixes

---

## Anti-Patterns (Avoid)

| Anti-Pattern | Why Bad | Fix |
|--------------|---------|-----|
| Installation-first README | Buries value proposition | Lead with TL;DR |
| "This is a tool that..." | Passive, abstract | "Solves X by doing Y" |
| Screenshot-heavy | Breaks, doesn't copy-paste | ASCII + code blocks |
| No examples | Abstract claims don't sell | Every feature → example |
| Hiding limitations | Users discover painfully | Honest Limitations section |
| Single install method | Alienates users | curl + pkg manager + source |
| No troubleshooting | Support burden | Top 5 errors with fixes |
| Outdated badges | Looks abandoned | Remove or keep current |

---

## AGENTS.md Blurb Template

For CLI tools, include a condensed reference block:

```markdown
## tool — Brief Description

One-line description of what it does and key differentiator.

### Core Workflow

```bash
# 1. Initialize
tool init

# 2. Main operation
tool do-thing

# 3. View results
tool show

Key Flags

--flag1    # Description
--flag2    # Description

Storage

- Location 1: path/to/thing
- Location 2: path/to/other

Notes

- Important caveat 1
- Important caveat 2
```
```

This provides AI agents with scannable reference without loading full README.

---

## Checklist

Before publishing:

```
□ Hero section with illustration + badges + one-liner + curl install
□ TL;DR with Problem/Solution/Feature table
□ Quick example (5-10 commands)
□ At least 3 installation methods documented
□ Every command has usage examples
□ Architecture diagram for complex tools
□ Comparison table vs at least 2 alternatives
□ Troubleshooting section (top 5 errors)
□ Honest Limitations section
□ FAQ with 5+ questions
□ All code blocks are copy-paste ready
□ No broken links or badges
□ Consistent terminology throughout
□ Grammar/spelling checked
```

---

## Real-World Examples

Study these READMEs for patterns:

| Project | Notable Pattern |
|---------|-----------------|
| [xf](https://github.com/Dicklesworthstone/xf) | Comprehensive CLI docs, search deep-dives |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | Benchmarks, comparison tables |
| [bat](https://github.com/sharkdp/bat) | GIF demos, feature highlights |
| [exa](https://github.com/ogham/exa) | Screenshot galleries, color themes |
| [starship](https://github.com/starship/starship) | Preset configurations, installation matrix |
| [jq](https://github.com/jqlang/jq) | Tutorial progression, manual links |

---

## Advanced: Progressive Disclosure for Long READMEs

For READMEs exceeding 1000 lines, use collapsible sections:

```markdown
<details>
<summary><strong>Advanced Configuration</strong></summary>

Content that most users don't need on first read...

</details>
```

Or link to separate docs:

```markdown
## Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [API Documentation](docs/api.md)
- [Contributing Guide](CONTRIBUTING.md)
```

Keep the README itself focused on the 80% use case.
