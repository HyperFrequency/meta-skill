# Technical Integration & API Reference

## Environment Variables

```bash
# Primary backend (Parallel Chat API) - REQUIRED
export PARALLEL_API_KEY="your_parallel_api_key"

# Academic search backend (Perplexity) - REQUIRED for academic queries
export OPENROUTER_API_KEY="your_openrouter_api_key"
```

## API Specifications

**Parallel Chat API:**
- Endpoint: `https://api.parallel.ai` (OpenAI SDK compatible)
- Model: `core` (60s-5min latency, complex multi-source synthesis)
- Output: Markdown text with inline citations
- Citations: Research basis with URLs, reasoning, and confidence levels
- Rate limits: 300 req/min
- Python package: `openai`

**Perplexity sonar-pro-search:**
- Model: `perplexity/sonar-pro-search` (via OpenRouter)
- Search mode: Academic (prioritizes peer-reviewed sources)
- Search context: High (comprehensive research)
- Response time: 5-15 seconds

## Command-Line Usage

```bash
# Auto-routed research (recommended) — ALWAYS save to sources/
python research_lookup.py "your query" -o sources/research_YYYYMMDD_HHMMSS_<topic>.md

# Force specific backend — ALWAYS save to sources/
python research_lookup.py "your query" --force-backend parallel -o sources/research_<topic>.md
python research_lookup.py "your query" --force-backend perplexity -o sources/papers_<topic>.md

# JSON output — ALWAYS save to sources/
python research_lookup.py "your query" --json -o sources/research_<topic>.json

# Batch queries — ALWAYS save to sources/
python research_lookup.py --batch "query 1" "query 2" "query 3" -o sources/batch_research_<topic>.md
```

## Error Handling and Limitations

**Known Limitations:**
- Parallel Chat API (core model): Complex queries may take up to 5 minutes
- Perplexity: Information cutoff, may not access full text behind paywalls
- Both: Cannot access proprietary or restricted databases

**Fallback Behavior:**
- If the selected backend's API key is missing, tries the other backend
- If both backends fail, returns structured error response
- Rephrase queries for better results if initial response is insufficient
