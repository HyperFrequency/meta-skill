# Backend Routing Detail

The skill auto-detects query type and routes to the optimal backend.

## Routing Logic

```
Query arrives
    |
    +-- Contains academic keywords? (papers, DOI, journal, peer-reviewed, etc.)
    |       YES --> Perplexity sonar-pro-search (academic search mode)
    |
    +-- Everything else (general research, market data, technical info, analysis)
            --> Parallel Chat API (core model)
```

## Academic Keywords (Routes to Perplexity)

Queries containing these terms are routed to Perplexity for academic-focused search:

- Paper finding: `find papers`, `find articles`, `research papers on`, `published studies`
- Citations: `cite`, `citation`, `doi`, `pubmed`, `pmid`
- Academic sources: `peer-reviewed`, `journal article`, `scholarly`, `arxiv`, `preprint`
- Review types: `systematic review`, `meta-analysis`, `literature search`
- Paper quality: `foundational papers`, `seminal papers`, `landmark papers`, `highly cited`

## Everything Else (Routes to Parallel)

All other queries go to the Parallel Chat API (core model), including:

- General research questions
- Market and industry analysis
- Technical information and documentation
- Current events and recent developments
- Comparative analysis
- Statistical data retrieval
- Complex analytical queries

## Manual Override

```bash
# Force Parallel Deep Research
python research_lookup.py "your query" --force-backend parallel

# Force Perplexity academic search
python research_lookup.py "your query" --force-backend perplexity
```

## Core Capabilities by Backend

### 1. General Research Queries (Parallel Chat API)

**Default backend.** Comprehensive, multi-source research with citations via the Chat API (`core` model).

Example queries:
- "Recent advances in CRISPR gene editing 2025"
- "Compare mRNA vaccines vs traditional vaccines for cancer treatment"
- "AI adoption in healthcare industry statistics"
- "Global renewable energy market trends and projections"
- "Explain the mechanism underlying gut microbiome and depression"

Response includes: comprehensive markdown report, inline citations from authoritative web sources, structured sections, multiple perspectives, source URLs.

### 2. Academic Paper Search (Perplexity sonar-pro-search)

**Used for academic-specific queries.** Prioritizes scholarly databases and peer-reviewed sources.

Example queries:
- "Find papers on transformer attention mechanisms in NeurIPS 2024"
- "Foundational papers on quantum error correction"
- "Systematic review of immunotherapy in non-small cell lung cancer"
- "Cite the original BERT paper and its most influential follow-ups"
- "Published studies on CRISPR off-target effects in clinical trials"

Response includes: summary of key findings, 5-8 high-quality citations (authors, titles, journals, years, DOIs), citation counts, venue tier indicators, methodology highlights, research gaps.

### 3. Technical and Methodological Information (Parallel)

- "Western blot protocol for protein detection"
- "Statistical power analysis for clinical trials"
- "Machine learning model evaluation metrics comparison"

### 4. Statistical and Market Data (Parallel)

- "Prevalence of diabetes in US population 2025"
- "Global AI market size and growth projections"
- "COVID-19 vaccination rates by country"
