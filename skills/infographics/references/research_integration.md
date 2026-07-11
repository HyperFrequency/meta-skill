# Research Integration (`--research`)

Detailed reference for the optional research phase used by
`scripts/generate_infographic.py`. Load this when you need to decide whether to
enable `--research` or to understand what the research phase produces.

## Automatic Data Gathering (`--research`)

When creating infographics that require accurate, up-to-date data, use the
`--research` flag to automatically gather facts and statistics using
**Perplexity Sonar Pro**.

```bash
# Research and generate statistical infographic
python skills/infographics/scripts/generate_infographic.py \
  "Global renewable energy adoption rates by country" \
  -o figures/renewable_energy.png --type statistical --research

# Research for timeline infographic
python skills/infographics/scripts/generate_infographic.py \
  "History of artificial intelligence breakthroughs" \
  -o figures/ai_history.png --type timeline --research

# Research for comparison infographic
python skills/infographics/scripts/generate_infographic.py \
  "Electric vehicles vs hydrogen vehicles comparison" \
  -o figures/ev_hydrogen.png --type comparison --research
```

## What Research Provides

The research phase automatically:

1. **Gathers Key Facts**: 5-8 relevant facts and statistics about the topic
2. **Provides Context**: Background information for accurate representation
3. **Finds Data Points**: Specific numbers, percentages, and dates
4. **Cites Sources**: Mentions major studies or sources
5. **Prioritizes Recency**: Focuses on 2023-2026 information

## When to Use Research

**Enable research (`--research`) for:**
- Statistical infographics requiring accurate numbers
- Market data, industry statistics, or trends
- Scientific or medical information
- Current events or recent developments
- Any topic where accuracy is critical

**Skip research for:**
- Simple conceptual infographics
- Internal process documentation
- Topics where you provide all the data in the prompt
- Speed-critical generation

## Research Output

When research is enabled, additional files are created:
- `{name}_research.json` - Raw research data and sources
- Research content is automatically incorporated into the infographic prompt
