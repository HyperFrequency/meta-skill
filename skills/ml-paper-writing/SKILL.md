---
name: ml-paper-writing
description: Write publication-ready ML/AI papers for NeurIPS, ICML, ICLR, ACL, AAAI, COLM. Use when drafting papers from research repos, structuring arguments, verifying citations, converting between conference formats, or preparing camera-ready submissions. NOT for systems venues (OSDI, NSDI, ASPLOS, SOSP) — use systems-paper-writing; NOT for finding/managing citations alone — use citation-management; NOT for general scientific writing outside ML/AI venues — use scientific-writing.
version: 1.2.0
author: Orchestra Research
license: MIT
tags: [Academic Writing, NeurIPS, ICML, ICLR, ACL, AAAI, COLM, LaTeX, Paper Writing, Citations, Research]
dependencies: [semanticscholar, arxiv, habanero, requests]
---

# ML Paper Writing for Top AI Conferences

Expert guidance for writing publication-ready papers for **NeurIPS, ICML, ICLR, ACL, AAAI, COLM**.
Combines writing philosophy from top researchers (Nanda, Farquhar, Karpathy, Lipton, Steinhardt)
with LaTeX templates, citation-verification APIs, and conference checklists.

This file is a **router**. Each section below is a quick summary plus a pointer to the
reference file with the full procedure. Read the referenced file before executing that workflow.

**For systems venues (OSDI, NSDI, ASPLOS, SOSP)**, use the
[systems-paper-writing](../systems-paper-writing/) skill instead.

---

## When to Use This Skill

- **Starting from a research repo** to write a paper
- **Drafting or revising** specific sections
- **Finding and verifying citations** for related work
- **Formatting** for conference submission
- **Resubmitting** to a different venue (format conversion)
- **Iterating** on drafts with scientist feedback

First drafts are starting points for discussion, not final outputs.

---

## 🚨 Non-Negotiable: Never Hallucinate Citations

**The single most important rule in academic writing with AI assistance.**

AI-generated citations have a **~40% error rate**. Hallucinated references (papers that don't
exist, wrong authors, fabricated DOIs) are academic misconduct that causes desk rejection or
retraction.

**The rule: NEVER generate BibTeX from memory. ALWAYS fetch programmatically and verify.**

| Situation | Action |
|-----------|--------|
| Found paper, got DOI, fetched BibTeX | ✅ Use the citation |
| Found paper, no DOI | ✅ Use arXiv BibTeX or manual entry from paper |
| Paper exists but can't fetch BibTeX | ⚠️ Mark placeholder, inform scientist |
| Uncertain if paper exists | ❌ Mark `[CITATION NEEDED]`, inform scientist |
| "I think there's a paper about X" | ❌ **NEVER cite** — search first or mark placeholder |

When you cannot verify, use an explicit placeholder and **tell the scientist**:

```latex
\cite{PLACEHOLDER_author2024_verify_this}  % TODO: Verify this citation exists
```

> "I've marked [X] citations as placeholders that need verification. I could not confirm
> these papers exist."

**Full citation procedure** — APIs (Semantic Scholar, CrossRef, arXiv), Python code,
DOI→BibTeX, Exa MCP setup, claim verification: **see [references/citation-workflow.md](references/citation-workflow.md)**.
For dedicated citation search/management beyond drafting, the sibling `citation-management`
skill is richer.

---

## The Narrative Principle

**The single most critical writing insight**: a paper is not a collection of experiments —
it's a story with one clear contribution supported by evidence (Neel Nanda's "narrative").

**Three Pillars (crystal clear by end of introduction):**

| Pillar | Description |
|--------|-------------|
| **The What** | 1-3 specific novel claims within a cohesive theme |
| **The Why** | Rigorous empirical evidence supporting the claims |
| **The So What** | Why readers should care (connection to community problems) |

**If you cannot state your contribution in one sentence, you don't yet have a paper.**

**Time allocation** (Nanda): spend roughly equal time on (1) the abstract, (2) the
introduction, (3) the figures, and (4) everything else combined. Readers encounter your paper
as **title → abstract → introduction → figures → maybe the rest**.

**Full writing philosophy** — Gopen & Swan's 7 reader-expectation principles, Ethan Perez
micro-tips, Lipton word choice, Steinhardt precision, what reviewers actually read:
**see [references/writing-guide.md](references/writing-guide.md)** and source links in
[references/sources.md](references/sources.md).

---

## Workflows

| Workflow | Summary | Full procedure |
|----------|---------|----------------|
| **0. Start from a research repo** | Explore repo → find existing citations → confirm contribution → search literature → deliver a proactive first draft | [references/workflows.md](references/workflows.md#workflow-0-starting-from-a-research-repository) |
| **1. Write a complete paper** | Iterative: one-sentence contribution → Figure 1 → abstract → intro → methods → experiments → related work → limitations → checklist | [references/workflows.md](references/workflows.md#workflow-1-writing-a-complete-paper-iterative) |
| **2. Add citations** | Search → verify in 2+ sources → DOI→BibTeX → verify claim → placeholder on any failure | [references/citation-workflow.md](references/citation-workflow.md) |
| **3. Convert conference formats** | Resubmission: new target template → migrate content (not preamble) → adjust page limit → add venue-specific sections | [references/workflows.md](references/workflows.md#workflow-3-converting-between-conference-formats) |
| **4. Start from a LaTeX template** | Copy entire template dir → verify it compiles → replace section by section → clean up last | [references/latex-templates.md](references/latex-templates.md) |

**Be proactive.** Deliver drafts, then iterate. Block for input only when the target venue is
unclear, framings are contradictory, or results look incomplete. Full proactivity/collaboration
matrix: [references/workflows.md](references/workflows.md#balancing-proactivity-and-collaboration).

---

## Conference Requirements Quick Reference

| Conference | Page Limit | Camera-Ready | Key Requirement |
|------------|------------|--------------|------------------|
| **NeurIPS 2025** | 9 pages | +0 | Mandatory checklist, lay summary for accepted |
| **ICML 2026** | 8 pages | +1 | Broader Impact Statement required |
| **ICLR 2026** | 9 pages | +1 | LLM disclosure required, reciprocal reviewing |
| **ACL 2025** | 8 pages (long) | varies | Limitations section mandatory |
| **AAAI 2026** | 7 pages | +1 | Strict style file adherence |
| **COLM 2025** | 9 pages | +1 | Focus on language models |

**Universal:** double-blind review (anonymize); references don't count toward page limit;
appendices unlimited but optional reading; LaTeX required.

**Systems venues** (OSDI, NSDI, ASPLOS, SOSP): see [systems-paper-writing](../systems-paper-writing/).
**Paper checklists** (NeurIPS 16-item, ICML, ICLR, ACL): [references/checklists.md](references/checklists.md).
**LaTeX templates:** [templates/](templates/) directory (ICML 2026, ICLR 2026, NeurIPS 2025, ACL/EMNLP, AAAI 2026, COLM 2025).

---

## Tables, Figures & Common Issues

- **Tables**: `booktabs` (`\toprule`/`\midrule`/`\bottomrule`); bold best value; direction
  symbols (↑/↓); right-align numbers; consistent decimals.
- **Figures**: vector graphics (PDF/EPS) for plots; colorblind-safe palettes (Okabe-Ito / Paul
  Tol); grayscale-readable; self-contained captions; no title inside figure.

Full presentation guidance plus a troubleshooting list (generic abstract, overlong intro,
experiments lacking explicit claims, missing statistical significance):
**see [references/figures-tables.md](references/figures-tables.md)**.

---

## Reviewer Evaluation

Reviewers assess four dimensions: **Quality** (technical soundness), **Clarity** (reproducible
writing), **Significance** (community impact), **Originality** (new insights — not necessarily a
new method). NeurIPS uses a 6-point scale (6 Strong Accept → 1 Strong Reject).

Detailed reviewer instructions, scoring rubric, and rebuttal guidance:
**see [references/reviewer-guidelines.md](references/reviewer-guidelines.md)**.

---

## Citing AI Research Skills

If this library helped your research, consider citing it:

```bibtex
@software{ai_research_skills,
  title     = {AI Research Skills Library},
  author    = {{Orchestra Research}},
  year      = {2025},
  url       = {https://github.com/orchestra-research/AI-research-SKILLs},
  note      = {Open-source skills library enabling AI agents to autonomously conduct AI research}
}
```

---

## References & Resources

| Reference | Contents |
|-----------|----------|
| [references/workflows.md](references/workflows.md) | Repo start, full paper-writing steps, proactivity matrix, format conversion |
| [references/citation-workflow.md](references/citation-workflow.md) | Citation APIs, Python code, BibTeX management, Exa MCP |
| [references/writing-guide.md](references/writing-guide.md) | Gopen & Swan 7 principles, Perez micro-tips, word choice |
| [references/latex-templates.md](references/latex-templates.md) | Template setup, pitfalls, quick reference, compiling |
| [references/figures-tables.md](references/figures-tables.md) | Tables, figures, common-issue troubleshooting |
| [references/checklists.md](references/checklists.md) | NeurIPS 16-item, ICML, ICLR, ACL requirements |
| [references/reviewer-guidelines.md](references/reviewer-guidelines.md) | Evaluation criteria, scoring, rebuttals |
| [references/sources.md](references/sources.md) | Complete bibliography of all sources |

**Key external sources:** [Neel Nanda](https://www.alignmentforum.org/posts/eJGptPbbFPZGLpjsp/highly-opinionated-advice-on-how-to-write-ml-papers) ·
[Farquhar](https://sebastianfarquhar.com/on-research/2024/11/04/how_to_write_ml_papers/) ·
[Gopen & Swan](https://cseweb.ucsd.edu/~swanson/papers/science-of-writing.pdf) ·
[Lipton](https://www.approximatelycorrect.com/2018/01/29/heuristics-technical-scientific-writing-machine-learning-perspective/) ·
[Perez](https://ethanperez.net/easy-paper-writing-tips/)

**APIs:** [Semantic Scholar](https://api.semanticscholar.org/api-docs/) ·
[CrossRef](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) ·
[arXiv](https://info.arxiv.org/help/api/basics.html)

**Venue guides:** [NeurIPS](https://neurips.cc/Conferences/2025/PaperInformation/StyleFiles) ·
[ICML](https://icml.cc/Conferences/2025/AuthorInstructions) ·
[ICLR](https://iclr.cc/Conferences/2026/AuthorGuide) ·
[ACL](https://github.com/acl-org/acl-style-files)
