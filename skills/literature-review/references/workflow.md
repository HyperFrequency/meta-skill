# Literature Review Workflow (Detailed)

The full seven-phase methodology. SKILL.md routes here for the step-by-step
detail; the high-level phase list lives there.

## Phase 1: Planning and Scoping

1. **Define Research Question**: Use the PICO framework (Population, Intervention,
   Comparison, Outcome) for clinical/biomedical reviews.
   - Example: "What is the efficacy of CRISPR-Cas9 (I) for treating sickle cell
     disease (P) compared to standard care (C)?"

2. **Establish Scope and Objectives**:
   - Define clear, specific research questions.
   - Determine review type (narrative, systematic, scoping, meta-analysis).
   - Set boundaries (time period, geographic scope, study types).

3. **Develop Search Strategy**:
   - Identify 2-4 main concepts from the research question.
   - List synonyms, abbreviations, and related terms for each concept.
   - Plan Boolean operators (AND, OR, NOT) to combine terms.
   - Select a minimum of 3 complementary databases.

4. **Set Inclusion/Exclusion Criteria**:
   - Date range (e.g., last 10 years: 2015-2024).
   - Language (typically English, or specify multilingual).
   - Publication types (peer-reviewed, preprints, reviews).
   - Study designs (RCTs, observational, in vitro, etc.).
   - Document all criteria clearly.

## Phase 2: Systematic Literature Search

1. **Multi-Database Search** — select databases appropriate for the domain.
   See `references/database_strategies.md` for per-database access and search tips.

   - **Biomedical & Life Sciences**: `gget search pubmed`, `gget search biorxiv`,
     `bioservices` (ChEMBL, KEGG, UniProt).
   - **General Scientific**: arXiv API, Semantic Scholar API, Google Scholar.
   - **Specialized**: `gget alphafold`, `gget cosmic`, `datacommons-client`.

2. **Document Search Parameters** for each database:
   ```markdown
   ## Search Strategy
   ### Database: PubMed
   - **Date searched**: 2024-10-25
   - **Date range**: 2015-01-01 to 2024-10-25
   - **Search string**:
     ("CRISPR"[Title] OR "Cas9"[Title])
     AND ("sickle cell"[MeSH] OR "SCD"[Title/Abstract])
     AND 2015:2024[Publication Date]
   - **Results**: 247 articles
   ```

3. **Export and Aggregate Results**:
   ```bash
   python scripts/search_databases.py combined_results.json \
     --deduplicate --format markdown --output aggregated_results.md
   ```

## Phase 3: Screening and Selection

1. **Deduplication** (by DOI primary, title fallback):
   ```bash
   python scripts/search_databases.py results.json --deduplicate --output unique_results.json
   ```
   Document the number of duplicates removed.

2. **Title Screening**: Review titles against criteria; exclude irrelevant studies;
   document the number excluded.

3. **Abstract Screening**: Read abstracts; apply criteria rigorously; document
   exclusion reasons.

4. **Full-Text Screening**: Obtain full texts; review against all criteria;
   document specific exclusion reasons; record final included count.

5. **Create PRISMA Flow Diagram**:
   ```
   Initial search: n = X
   ├─ After deduplication: n = Y
   ├─ After title screening: n = Z
   ├─ After abstract screening: n = A
   └─ Included in review: n = B
   ```

## Phase 4: Data Extraction and Quality Assessment

1. **Extract Key Data** from each included study: metadata (authors, year, journal,
   DOI), design/methods, sample size and population, key findings, author-noted
   limitations, funding/conflicts.

2. **Assess Study Quality**:
   - **RCTs**: Cochrane Risk of Bias tool.
   - **Observational studies**: Newcastle-Ottawa Scale.
   - **Systematic reviews**: AMSTAR 2.
   - Rate each study High / Moderate / Low / Very Low. Consider excluding very
     low-quality studies.

3. **Organize by Themes**: Identify 3-5 major themes; group studies by theme
   (studies may appear in multiple); note patterns, consensus, and controversies.

## Phase 5: Synthesis and Analysis

1. **Create Review Document** from template:
   ```bash
   cp assets/review_template.md my_literature_review.md
   ```

2. **Write Thematic Synthesis** (NOT study-by-study summaries):
   - Organize the Results section by themes or research questions.
   - Synthesize findings across multiple studies within each theme.
   - Compare and contrast approaches and results; identify consensus and controversy;
     highlight the strongest evidence.

   Example:
   ```markdown
   #### 3.3.1 Theme: CRISPR Delivery Methods

   Multiple delivery approaches have been investigated for therapeutic gene editing.
   Viral vectors (AAV) were used in 15 studies^1-15^ and showed high transduction
   efficiency (65-85%) but raised immunogenicity concerns^3,7,12^. In contrast, lipid
   nanoparticles demonstrated lower efficiency (40-60%) but improved safety
   profiles^16-23^.
   ```

3. **Critical Analysis**: Evaluate methodological strengths/limitations across
   studies; assess quality and consistency of evidence; identify knowledge and
   methodological gaps; note future research needs.

4. **Write Discussion**: Interpret findings in broader context; discuss implications;
   acknowledge review limitations; compare with previous reviews; propose specific
   future research directions.

## Phase 6: Citation Verification

**CRITICAL**: All citations must be verified for accuracy before final submission.

1. **Verify All DOIs**:
   ```bash
   python scripts/verify_citations.py my_literature_review.md
   ```
   The script extracts DOIs, verifies each resolves, retrieves CrossRef metadata,
   generates a verification report, and outputs formatted citations.

2. **Review Verification Report**: Check failed DOIs; verify author names, titles,
   and publication details; correct errors; re-run until all pass.

3. **Format Citations Consistently**: Choose one style and use it throughout (see
   `references/citation_styles.md`). Ensure in-text citations match the reference list.

## Phase 7: Document Generation

1. **Generate PDF**:
   ```bash
   python scripts/generate_pdf.py my_literature_review.md \
     --citation-style apa --output my_review.pdf
   ```
   Options: `--citation-style` (apa, nature, chicago, vancouver, ieee),
   `--no-toc`, `--no-numbers`, `--check-deps`.

2. **Review Final Output**: Check formatting/layout, all sections present, citations
   render, figures/tables appear, table of contents accurate.

3. **Quality Checklist**:
   - [ ] All DOIs verified with verify_citations.py
   - [ ] Citations formatted consistently
   - [ ] PRISMA flow diagram included (for systematic reviews)
   - [ ] Search methodology fully documented
   - [ ] Inclusion/exclusion criteria clearly stated
   - [ ] Results organized thematically (not study-by-study)
   - [ ] Quality assessment completed
   - [ ] Limitations acknowledged
   - [ ] References complete and accurate
   - [ ] PDF generates without errors

## Complete Example Workflow

```bash
# 1. Create review document from template
cp assets/review_template.md crispr_sickle_cell_review.md

# 2. Search multiple databases (gget for PubMed/bioRxiv; direct API for
#    arXiv/Semantic Scholar). Export results as JSON.

# 3. Aggregate and process results
python scripts/search_databases.py combined_results.json \
  --deduplicate --rank citations --year-start 2015 --year-end 2024 \
  --format markdown --output search_results.md --summary

# 4. Screen results, extract data, organize by themes.

# 5. Write the review following the template structure.

# 6. Verify all citations
python scripts/verify_citations.py crispr_sickle_cell_review.md
cat crispr_sickle_cell_review_citation_report.json
python scripts/verify_citations.py crispr_sickle_cell_review.md  # re-verify

# 7. Generate professional PDF
python scripts/generate_pdf.py crispr_sickle_cell_review.md \
  --citation-style nature --output crispr_sickle_cell_review.pdf

# 8. Review final PDF and markdown outputs.
```

## Best Practices

**Search Strategy**: Use ≥3 databases; include preprint servers; document search
strings/dates/counts; run pilot searches and refine; sort by citation count to
surface influential work first.

**Screening and Selection**: Use clear pre-defined criteria; screen Title → Abstract
→ Full text; document exclusions; for systematic reviews use dual independent
screening.

**Synthesis**: Organize thematically, not study-by-study; synthesize across studies;
be critical about quality and consistency; identify gaps.

**Quality and Reproducibility**: Use appropriate quality-assessment tools; verify all
citations; document methodology for reproducibility; follow PRISMA for systematic
reviews.

**Writing**: Be objective, systematic, specific (numbers, statistics, effect sizes),
and clear (logical thematic flow).

## Common Pitfalls to Avoid

1. **Single database search** — always search multiple databases.
2. **No search documentation** — document all searches for reproducibility.
3. **Study-by-study summary** — organize thematically instead.
4. **Unverified citations** — always run verify_citations.py.
5. **Too broad search** — refine with specific terms.
6. **Too narrow search** — include synonyms and related terms.
7. **Ignoring preprints** — include bioRxiv, medRxiv, arXiv.
8. **No quality assessment** — assess and report study quality.
9. **Publication bias** — note potential bias toward positive results.
10. **Outdated search** — clearly state the search date.
