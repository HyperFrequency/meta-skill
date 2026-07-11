# Query Best Practices

*(Portions adapted from openscience (Apache-2.0).)*

Well-formed queries return better sources from either backend. These practices are
backend-agnostic — they apply whether the query routes to the Parallel Chat API or to
Perplexity.

## Structured Query Format

Compose queries as:

```
[Topic] + [Specific Aspect] + [Time Frame] + [Type of Information]
```

Examples:
- "CRISPR gene editing + off-target effects + 2024 + clinical trials"
- "Quantum computing + error correction + recent advances + review papers"
- "Renewable energy + solar efficiency + 2023-2025 + statistical data"

## Specific and Focused Queries

**Good** (specific, scoped, answerable):
- "Randomized controlled trials of mRNA vaccines for cancer treatment 2023-2025"
- "Explain the mechanism by which CRISPR off-target effects occur and strategies to minimize them"
- "Global AI adoption in healthcare statistics 2025 with regional breakdown"

**Poor** (too broad or vague — return shallow, unfocused results):
- "Tell me about AI"
- "Cancer research"
- "Latest news"

## Follow-Up Queries

After an initial lookup, refine with targeted follow-ups:
- "Show me the full citation for the Smith et al. 2024 paper"
- "What are the limitations of this methodology?"
- "Find similar studies using different approaches"
- "What controversies exist in this research area?"

Each follow-up is a fresh query — save every result to `sources/` (see
`saving-results.md`).
