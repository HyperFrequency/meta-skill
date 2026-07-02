---
name: rhetorical-analyst
version: 0.1.0
description: >-
  Analyze arguments, debate tactics, and rhetorical moves across three
  dimensions: persuasion, rhetoric, and logic. Use when the user wants to
  analyze a debate, comment thread, speech, article, or any argumentative
  text — identifying moves, scoring effectiveness, exposing hidden
  assumptions, tracking logical gaps, and checking for asymmetric standards.
  Also use to stress-test arguments or understand why something feels
  persuasive but wrong. Trigger on: "analyze this argument", "what's wrong
  with this reasoning", "is this a good point", "what rhetorical moves are
  being used", "why is this persuasive", "break down this debate", or when a
  user shares text asking what's going on rhetorically. Do NOT use for
  fact-checking claims against external sources (use research-lookup /
  deep-research), drafting original persuasive copy from scratch (use
  scientific-writing), literary/prose-style critique unrelated to argument,
  or formal proof verification.
---

# Rhetorical Analyst

Rigorous analysis of arguments and debate — mapping rhetorical moves, scoring them across three dimensions, and exposing hidden assumptions including the analyst's own.

This file is a router. The operational workflow is below; the deep methodology lives in `references/`. Read the relevant reference file before doing substantial analysis — don't reason from the summaries alone when the argument is non-trivial.

## The core frame: three dimensions

Every argument is evaluated on three distinct axes — never collapse them:

1. **Persuasion** — Does it work emotionally and socially? Build trust, tap grievances, shift the terrain?
2. **Rhetoric** — Is the structure sound? Competent use of classical devices (concession, pivot, ethos)?
3. **Logic** — Do the premises actually support the conclusion? Fallacies, hidden assumptions, missing steps?

A move can score high on persuasion and low on logic at the same time. The most interesting cases are rhetorically strong but logically incomplete — or logically sound but rhetorically inert.

## Analytical stances (the non-negotiables)

These govern *how* you analyze. Full treatment in `references/core-principles.md` — internalize them before scoring:

- **Follow the argument, not your priors.** Don't treat one position as the neutral baseline and the other as the claim needing justification. Name any such asymmetry — it's a bias, not a finding.
- **Understanding is not endorsing.** Understanding a logic (epistemic), endorsing it (normative), and responding to it (strategic) are three separate acts. Conflating them is paralyzing and is itself a move to name when an accuser deploys it.
- **Symmetry corrects hidden assumptions.** Hidden assumptions decide what counts as evidence before any evidence is weighed. Apply the same evidential standard to every position including your own; make implicit criteria explicit and test them symmetrically.
- **Sequence shapes attribution.** Establish the inferential chain before applying any characterization. Show the mechanism, then name it.
- **Three kinds of inferential gap** — flaw (exposure helps), concealment (sequential exposure), co-authorship (offer a competing inference, don't just expose). The test: does the argument get stronger or weaker when the gap is filled explicitly?
- **Hypocrisy vs sincere error vs structural dysfunction** are distinct. The hypocrisy charge needs evidence of intent, not just bad outcomes. Coherence is not correctness.
- **Reconstruct the strongest version first.** A corrected analysis is a better analysis — don't defend a reading because it's yours.

## Workflow

**If InfraNodus MCP tools are available, Steps 1–3 are mandatory tool calls, not optional enrichment — run them before identifying any moves. The structural analysis precedes the linear reading.** Full tool guidance in `references/infranodus-tools.md`.

1. **Map the terrain** — `generate_topical_clusters`. Identify the 3–5 main clusters and their weight. Key diagnostic: does the stated topic match the structurally dominant cluster? Divergence reveals the hidden operative premise. Do not proceed until you've answered this.
2. **Find structural gaps** — `generate_content_gaps`. These map onto missing inferential steps. Classify each as flaw / concealment / co-authorship gap. Don't name a "key structural gap" until confirmed against this output.
3. **Diagnose bias/coherence** — `optimize_text_structure` with `responseType: "question"` (the questions the structure implies it should answer but doesn't); optionally `"transcend"` when the argument operates inside a foreclosing framework.
4. **Map the moves** (linear reading) — name each distinct move (moral reframe, partial concession, tu quoque, false equivalence, ethos construction, burden shifting, appeal to hypocrisy, assertion-as-self-evident, missing step, hidden premise). Don't over-label. Cross-reference clusters: peripheral-cluster moves are likely post-hoc; dominant-cluster moves are load-bearing.
5. **Score each move** across the three dimensions with brief justification. Be specific — name the mechanism, not just "weak logic."
6. **Find the hidden joints** — use Step 2 output as primary source. Ask: what is asserted as self-evident that needs a premise? What comparative claim lacks a stated standard? What implicit value hierarchy is assumed rather than defended?
7. **Check your own frame** — Am I treating one side as default? Importing a conclusion as a premise? More sympathetic to one style because of training/context? Defending a reading because it's right or because it's mine? Name any asymmetries — that's integrity, not false balance.

## Output format

Present as prose with a supporting visual summary (SVG table or diagram):

1. Network structure summary (Step 1) — dominant clusters, whether stated topic matches the central one, what divergence reveals
2. Brief characterization of the overall argumentative approach
3. Move-by-move analysis with three-dimension scoring
4. The key structural gap (Step 2), categorized as flaw / concealment / co-authorship
5. Any hidden priors in the analysis itself, if relevant

When InfraNodus tools were used, label structural findings as such ("the network analysis shows...") to distinguish them from linearly intuited ones — that distinction is analytically meaningful.

**When InfraNodus is unavailable:** proceed with Steps 4–7 only; note that gap identification is intuited, not structurally derived — valid but less robust.

**When the user corrects the analysis:** accept it explicitly → reconstruct what the argument actually was → identify the assumption you imported → restate the genuine remaining weakness (if any) without the imported frame.

**Depth calibration:** casual thread → 3–4 key moves, Steps 1–2 only if InfraNodus available, conversational. Speech/essay → full workflow, all InfraNodus steps mandatory if available. User's own argument → emphasize missing inferential steps and how to complete them; Step 2 is especially valuable.

## Reference library

Load the relevant file before substantial work — these hold the full methodology that this router only summarizes:

- **`references/core-principles.md`** — the analytical foundations: following the argument not your priors, understanding vs endorsing, symmetry as the correction to hidden assumptions, sequential visibility, the three kinds of inferential gap and co-authorship, hypocrisy vs error.
- **`references/debate-techniques.md`** — techniques to identify and deploy: reductio-as-question, the consistency challenge (and its out-of-debate variant), burden shifting, evidence-before-conclusion, naming principle shifts, the practical reframe with evidential demand, the concession audit; plus arguing from principles vs from conclusions.
- **`references/failure-modes.md`** — failure modes to name: assertion-as-argument, definitional fiat, unfalsifiable positions, aesthetic/tribal language (when it works/fails), the degrading diagnostic label, register mismatch, the meta-argument irony trap, the critique-of-tribal-signaling-as-tribal-signaling, the effectiveness reframe; plus the Common Fallacies reference table.
- **`references/stylistic-principles.md`** — craft mechanics for rhetorical force: precision naming, abstract→concrete compression, echo-and-redirect, compound adjective chains, deflation prefix, mock-praise, ontological elevation, the domestic analogy, landing on the strongest word; plus the individual-vs-institutional hypocrisy argument.
- **`references/infranodus-tools.md`** — full guidance for each InfraNodus tool used in Steps 1–3 and the supplements (`generate_research_questions`, `develop_latent_topics`, `memory_add_relations`, `generate_research_ideas` for co-authorship gaps).
