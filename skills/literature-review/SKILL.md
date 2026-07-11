---
name: literature-review
version: 0.1.0
description: Conduct comprehensive, systematic literature reviews using multiple academic databases (PubMed, arXiv, bioRxiv, Semantic Scholar, etc.). This skill should be used when conducting systematic literature reviews, meta-analyses, research synthesis, or comprehensive literature searches across biomedical, scientific, and technical domains. Creates professionally formatted markdown documents and PDFs with verified citations in multiple citation styles (APA, Nature, Vancouver, etc.). Not for ad-hoc single-paper lookups (use paper-lookup) or general research synthesis without systematic methodology (use deep-research).
allowed-tools: Read Write Edit Bash
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Literature Review

Conduct systematic, comprehensive literature reviews following rigorous academic
methodology: search multiple databases, synthesize findings thematically, verify
every citation, and generate professional markdown + PDF output.

This is a **router**. The high-level flow lives here; step-by-step detail lives in
`references/`. Read the relevant reference file before executing a phase.

## When to Use This Skill

- Conducting a systematic literature review for research or publication.
- Synthesizing current knowledge on a topic across multiple sources.
- Performing meta-analysis or scoping reviews.
- Writing the literature-review section of a paper or thesis.
- Investigating the state of the art; identifying research gaps.
- When verified citations and professional formatting are required.

**Not for**: ad-hoc single-paper lookups (use `paper-lookup`) or general research
synthesis without systematic methodology (use `deep-research`).

## Workflow at a Glance

Seven phases — full detail in **`references/workflow.md`**:

1. **Planning & Scoping** — define question (PICO), scope, search strategy,
   inclusion/exclusion criteria.
2. **Systematic Search** — query ≥3 databases; document every search string, date,
   and result count. Database-specific access and tips: `references/database_strategies.md`.
3. **Screening & Selection** — deduplicate → title → abstract → full-text; build a
   PRISMA flow diagram.
4. **Data Extraction & Quality Assessment** — extract metadata/findings; rate quality
   (Cochrane RoB, Newcastle-Ottawa, AMSTAR 2); group into 3-5 themes.
5. **Synthesis & Analysis** — write a *thematic* synthesis (never study-by-study);
   critical analysis; discussion.
6. **Citation Verification** — `python scripts/verify_citations.py <review.md>`;
   re-run until all DOIs pass. Styles: `references/citation_styles.md`.
7. **Document Generation** — `python scripts/generate_pdf.py <review.md> --citation-style <style>`;
   review against the quality checklist in `references/workflow.md`.

Start from the template: `cp assets/review_template.md my_literature_review.md`.

## Choosing Which Papers to Include

Prioritize influential, highly-cited papers from reputable authors and top venues —
quality over quantity. Citation-count thresholds, venue tiers, author-reputation
assessment, seminal-paper identification, and forward/backward citation chaining are
detailed in **`references/paper_selection.md`**.

## Figures (Required)

**Every literature review MUST include at least 1-2 AI-generated figures** via the
**scientific-schematics** skill — this is not optional. Generate at minimum one
diagram (e.g., a PRISMA flow diagram); prefer 2-3 for comprehensive reviews (search
strategy flowchart, thematic synthesis diagram, conceptual framework). Describe the
diagram in natural language; the schematic is generated, reviewed, and refined
automatically:

```bash
python scripts/generate_schematic.py "your diagram description" -o figures/output.png
```

See the **scientific-schematics** skill for detail.

## Bundled Resources

**Scripts** (`scripts/`):
- `verify_citations.py` — verify DOIs against CrossRef; output formatted citations.
- `generate_pdf.py` — convert markdown to professional PDF (`--check-deps` to verify tooling).
- `search_databases.py` — deduplicate, rank, filter, and format search results.

**References** (`references/`):
- `workflow.md` — full seven-phase methodology, example workflow, best practices, pitfalls.
- `paper_selection.md` — high-impact prioritization and citation chaining.
- `database_strategies.md` — comprehensive per-database search strategies.
- `citation_styles.md` — citation formatting (APA, Nature, Vancouver, Chicago, IEEE).

**Assets** (`assets/`):
- `review_template.md` — complete literature-review template with all sections.

## Integration with Other Skills

- **Database access**: `gget` (PubMed, bioRxiv, COSMIC, AlphaFold, UniProt),
  `bioservices` (ChEMBL, KEGG, Reactome, PubChem), `datacommons-client` (statistics).
- **Visualization**: `scientific-schematics` (figures), `matplotlib`, `seaborn`.
- **Related skills**: `paper-lookup` (single papers), `deep-research` (non-systematic
  synthesis), `citation-management` (Scholar/PubMed metadata + BibTeX),
  `venue-templates` (journal-specific writing styles when preparing a review for a venue).

## Dependencies

```bash
pip install requests              # citation verification
brew install pandoc               # PDF generation (apt-get install pandoc on Linux)
brew install --cask mactex        # LaTeX (apt-get install texlive-xetex on Linux)
python scripts/generate_pdf.py --check-deps
```

## External References

- PRISMA: http://www.prisma-statement.org/ · Cochrane Handbook:
  https://training.cochrane.org/handbook · AMSTAR 2: https://amstar.ca/
- MeSH Browser: https://meshb.nlm.nih.gov/search · PubMed Advanced Search:
  https://pubmed.ncbi.nlm.nih.gov/advanced/
