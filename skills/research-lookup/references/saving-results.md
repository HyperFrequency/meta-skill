# MANDATORY: Save All Results to Sources Folder

**Every research-lookup result MUST be saved to the project's `sources/` folder.**

This is non-negotiable. Research results are expensive to obtain and critical for reproducibility.

## Saving Rules

| Backend | `-o` Flag Target | Filename Pattern |
|---------|-----------------|------------------|
| Parallel Deep Research | `sources/research_<topic>.md` | `research_YYYYMMDD_HHMMSS_<brief_topic>.md` |
| Perplexity (academic) | `sources/papers_<topic>.md` | `papers_YYYYMMDD_HHMMSS_<brief_topic>.md` |
| Batch queries | `sources/batch_<topic>.md` | `batch_research_YYYYMMDD_HHMMSS_<brief_topic>.md` |

## How to Save

**CRITICAL: Every call to `research_lookup.py` MUST include the `-o` flag pointing to the `sources/` folder.**

**CRITICAL: Saved files MUST preserve all citations, source URLs, and DOIs.** The default text output automatically includes a `Sources` section (with title, date, URL for each source) and an `Additional References` section (with DOIs and academic URLs extracted from the response text). For maximum citation metadata, use `--json`.

```bash
# General research — save to sources/ (includes Sources + Additional References sections)
python research_lookup.py "Recent advances in CRISPR gene editing 2025" \
  -o sources/research_20250217_143000_crispr_advances.md

# Academic paper search — save to sources/ (includes paper citations with DOIs)
python research_lookup.py "Find papers on transformer attention mechanisms in NeurIPS 2024" \
  -o sources/papers_20250217_143500_transformer_attention.md

# JSON format for maximum citation metadata (full citation objects with URLs, DOIs, snippets)
python research_lookup.py "CRISPR clinical trials" --json \
  -o sources/research_20250217_143000_crispr_trials.json

# Forced backend — save to sources/
python research_lookup.py "AI regulation landscape" --force-backend parallel \
  -o sources/research_20250217_144000_ai_regulation.md

# Batch queries — save to sources/
python research_lookup.py --batch "mRNA vaccines efficacy" "mRNA vaccines safety" \
  -o sources/batch_research_20250217_144500_mrna_vaccines.md
```

## Citation Preservation in Saved Files

| Format | Citations Included | When to Use |
|--------|-------------------|-------------|
| Text (default) | `Sources (N):` section with `[title] (date) + URL` + `Additional References (N):` with DOIs and academic URLs | Standard use — human-readable with all citations |
| JSON (`--json`) | Full citation objects: `url`, `title`, `date`, `snippet`, `doi`, `type` | When you need maximum citation metadata |

**For Parallel backend**, saved files include: research report + Sources list (title, URL) + Additional References (DOIs, academic URLs).
**For Perplexity backend**, saved files include: academic summary + Sources list (title, date, URL, snippet) + Additional References (DOIs, academic URLs).

**Use `--json` when you need to:**
- Parse citation metadata programmatically
- Preserve full DOI and URL data for BibTeX generation
- Maintain the structured citation objects for cross-referencing

## Why Save Everything

1. **Reproducibility**: Every citation and claim can be traced back to its raw research source
2. **Context Window Recovery**: If context is compacted, saved results can be re-read without re-querying
3. **Audit Trail**: The `sources/` folder documents exactly how all research information was gathered
4. **Reuse Across Sections**: Multiple sections can reference the same saved research without duplicate queries
5. **Cost Efficiency**: Check `sources/` for existing results before making new API calls
6. **Peer Review Support**: Reviewers can verify the research backing every citation

## Before Making a New Query, Check Sources First

```bash
ls sources/  # Check existing saved results
```

If a prior lookup covers the same topic, re-read the saved file instead of making a new API call.

## Logging

When saving research results, always log:

```
[HH:MM:SS] SAVED: Research lookup to sources/research_20250217_143000_crispr_advances.md (3,800 words, 8 citations)
[HH:MM:SS] SAVED: Paper search to sources/papers_20250217_143500_transformer_attention.md (6 papers found)
```
