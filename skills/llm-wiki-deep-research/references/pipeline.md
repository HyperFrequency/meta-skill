# Deep Research Pipeline — Phase Detail & Agent Prompts

Full instructions for each phase. SKILL.md routes here; execute phases in order.

---

## Phase 1: Topic Selection & Research Planning

### A. Directed Mode (user provided topic(s))
- Parse `$ARGUMENTS` for topic(s).
- Validate topics are research-worthy.
- Plan research scope for each topic.

### B. Autonomous Mode (`""` or `"auto"`)
Analyze the knowledge base to identify research opportunities:

1. Read the vault analysis: `cat knowledge-base-analysis.md` (produced by
   `llm-wiki-analyze-kb`).
2. Check recent activity: `ls -lt "Document Insights/" | head -10`
3. Identify gaps based on:
   - Underrepresented domains/clusters in `knowledge-base-analysis.md`
   - Missing connections flagged in recent changelogs
   - Emerging themes from existing insights
   - The user's recent work patterns
   - CLAUDE.md priorities and future directions
4. Select 1-3 topics that fill gaps, build on the vault's existing strength
   areas, connect underexplored domains, add empirical validation to intuitive
   frameworks, or challenge current thinking.

**Good topic examples:** pick a domain that `knowledge-base-analysis.md` flags as
thin or that bridges two existing hubs — e.g. a mechanism underlying a heavily
linked note, an empirical counterpart to an intuitive framework, or a
cross-domain link between two otherwise disconnected clusters.

---

## Phase 2: Execute Research

Get timestamp for session folder naming (`YYYY-MM-DD Topic Description`):
```bash
date '+%Y-%m-%d %H:%M:%S %Z'
```

For each topic, launch `Task` with `subagent_type='research-specialist'`:

```
TOPIC: [Selected topic]

Conduct comprehensive research on [topic] focusing EXCLUSIVELY on the most recent
research and developments.

⚠️ CRITICAL RECENCY REQUIREMENT:
Your training data may be outdated. Prioritize the most recent information
available through web search, even if it contradicts training data.

SEARCH STRATEGY:
- Use web/search grounding to find papers from the last 12-18 months
- Explicitly search "2024"/"2025"/"recent"/"latest" in queries
- Check publication dates - reject anything older than 2023 unless foundational
- Look for preprints, conference proceedings, recent journal publications
- Prioritize arXiv from last 6 months, conference papers from 2024-2025
- Search "state of the art [topic] 2024" / "[topic] breakthrough 2025"

RESEARCH REQUIREMENTS:
1. Target Sources (RECENT ONLY):
   - arXiv preprints (2024-2025, prioritize last 6 months)
   - Major conferences 2024-2025 (NeurIPS, ICML, ICLR, AAAI, ACL, EMNLP)
   - Leading AI labs' recent publications (OpenAI, Anthropic, Google DeepMind,
     Microsoft Research)
   - Top-tier journals (2024-2025 issues only)
   - Industry whitepapers / blog posts (last 12 months)
2. Key Focus Areas: novel mechanisms/frameworks not in training data; empirical
   findings with quantified results; counter-intuitive/contrarian insights;
   cross-domain applications; real-world implementations; practical implications.
3. Output Requirements: structured report (15-25 major papers/developments); full
   citations with DATES (title, authors, DATE, venue, arXiv ID); key findings;
   performance metrics; emerging trends; URLs; critical analysis/synthesis.
4. Save Location: resources/[Topic-Slug]-Research-Report-YYYY-MM-DD.md

VERIFICATION: verify 80%+ of papers are from 2024-2025; if not, search again with
more explicit recency filters. Trust search results over training data.
```

**Strategy:** run topics sequentially if related (later research references
earlier), parallel if independent domains. Decide based on topic relationships.

**Monitor:** after each agent, note report path, verify 15-25+ papers, check
citations/empirical data, confirm report saved in `/resources/`.

---

## Phase 3: Extract Insights

Create session folder `Document Insights/[YYYY-MM-DD Topic Description]/`.

For each research report, launch `Task` with
`subagent_type='document-insight-extractor'`:

```
Extract unique insights from the research report for the knowledge base.

SOURCE DOCUMENT: [Full path to research report]
SESSION FOLDER: [Session folder name]

EXTRACTION GUIDELINES:
1. Focus on novel insights: paradigm shifts, counter-intuitive findings,
   empirical validation, novel mechanisms, cross-domain applications, contrarian
   perspectives backed by evidence.
2. Bridge to existing KB: connect to the vault's primary hubs and frameworks (as
   identified in `knowledge-base-analysis.md`); identify consilience (3+ domains
   converging); find validation/challenges to current thinking.
3. Prioritize: findings that extend understanding; empirics validating intuitive
   frameworks; novel architectures/methodologies; real-world implications;
   philosophical/meta-level insights.
4. Quality standards: 15-25 high-quality insights per report; avoid redundancy
   (ALWAYS search for duplicates first); include citations (title, authors,
   year); tag for discoverability; create connections to existing notes.
5. Output: permanent notes in session folder; full citations/sources; tags; noted
   connections; changelog `CHANGELOG - Document Analysis YYYY-MM-DD.md`.

CRITICAL: ALWAYS dedupe before creating notes. Store ALL notes in
Document Insights/[Session-Folder]/. Write a comprehensive changelog.
```

**Monitor:** verify insights in correct session folder, changelog created, count
of unique insights, deduplication performed.

---

## Phase 4: Insight Interview (Optional Gate)

After extraction, summarize the 5-8 most significant insights (note titles + one
line each; highlight ones that challenge KB frameworks or contradict current
notes; flag surprising/counterintuitive results).

**[APPROVAL GATE]** Present:

> "[N] insights extracted on [topic]. Before connection discovery, would you like
> a quick insight interview? I'll ask 6-8 questions grounded in your existing
> notes and these findings to capture YOUR angles, reactions, and disagreements.
> Responses save to `Personal Insights/` and the connection finder maps both
> sets together. Say **yes** to run, or **skip** to go straight to connection
> discovery."

- **If yes:** run a short interview for the current topic — one question at a
  time, grounded in the extracted findings and the user's existing notes. Save
  the user's responses as notes under `Personal Insights/`; note the session
  timestamp so Phase 5 includes these notes.
- **If skip:** proceed to Phase 5.

If the interview ran, Phase 5 maps connections across BOTH the external research
session folder and the new personal notes in `Personal Insights/`.

---

## Phase 5: Connection Discovery

**Strategy:** (A) single comprehensive pass over the whole session folder, or
(B) 2-3 targeted passes — new↔existing AI insights, new↔primary hubs,
cross-domain bridges/synthesis. Choose by insight count and domain diversity.

Launch `Task` with `subagent_type='connection-finder'`:

```
Discover connections between newly extracted insights and the existing KB.

STARTING POINTS: all notes in Document Insights/[Session-Folder]/
(or specify individual notes for targeted passes).

GOALS:
1. Bridge to existing knowledge: connect to existing notes; link to the vault's
   primary hubs and frameworks (from knowledge-base-analysis.md); map to MOCs and
   output content.
2. Cross-domain opportunities: surface links that bridge two otherwise
   disconnected clusters in the vault (these are the highest-value connections).
3. Synthesis: clusters ready for article development; consilience zones (3+
   domains); emergent/meta patterns; framework extensions; new MOC candidates.
4. Parameters: similarity 0.65-0.85; depth 2-3 levels per insight; focus on
   non-obvious, high-value connections.
5. Output: map direct connections; identify bridge notes; highlight consilience
   zones; write changelog `CHANGELOG - Connection Discovery Session YYYY-MM-DD.md`
   under Changelogs/; update the master CHANGELOG.md; suggest concrete article
   topics or framework extensions.
```

**Monitor:** verify changelog written under `Changelogs/`, master `CHANGELOG.md`
updated, note consilience zones / synthesis opportunities, identify high-priority
article topics.

---

## Error Handling

- **Insufficient papers:** broaden criteria; extend date range to include 2023;
  consider adjacent topics; document limitation in summary.
- **Too many duplicates:** focus on truly novel contributions; look for empirical
  validation; seek contrarian perspectives; topic may already be well-covered.
- **Weak connections:** topic may be genuinely novel (good); widen similarity
  threshold; run extra passes on specific hubs; document gap as synthesis chance.
- **Any phase fails:** document the error in the summary; continue with successful
  phases; provide partial results; recommend retry or alternative approach.
