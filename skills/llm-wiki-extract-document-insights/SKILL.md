---
name: llm-wiki-extract-document-insights
version: 0.2.0
description: Extract structured insights from EXTERNAL documents — research papers, PDFs, books, articles, reports, or a pasted transcript of someone else's work — into the user's Obsidian/turbovault knowledge base, with epistemic classification (confirmed/theoretical/speculative), dedup against existing notes, and session-foldered output. Lean router — spawns the document-insight-extractor subagent. Use WHEN the user points at an external source (paper/PDF/book/article/URL/report) and wants its findings distilled into vault notes, or says "extract insights from this paper", "pull the key claims out of this PDF", "add this article to my brain". Do NOT use for the user's OWN thoughts/conversations/notes (use llm-wiki-extract-insights), for merging existing notes into a narrative (llm-wiki-synthesize-insights), for a full research-and-integrate pipeline (llm-wiki-deep-research), for scraping/ingesting raw sources into files (scrape-ingest-organize), or for a plain cited web report with no vault integration (deep-research).
allowed-tools: [Task]
user-invocable: true
arg-description: "<session name> <file path or content description>"
---

# Extract Document Insights

Distill EXTERNAL source material into permanent vault notes with proper epistemic
classification, then deduplicate against what the knowledge base already holds.

This skill is a thin router: it parses the session name + source, spawns the
`document-insight-extractor` subagent to do the extraction, and reports back.

## When to use

- You have an external artifact — research paper, PDF, book chapter, web article,
  report, or a pasted transcript of someone else's talk/podcast/interview — and want
  its findings captured as notes in the Obsidian/turbovault "Brain".
- Triggers: "extract insights from this paper", "pull the key claims out of this PDF",
  "add this article to my brain", "capture the findings from this report".

## When NOT to use

- The content is the user's OWN thinking (conversations, chat transcripts, personal
  notes) → use `llm-wiki-extract-insights`.
- You want to merge notes that already exist into a framework/narrative →
  `llm-wiki-synthesize-insights`.
- You want an end-to-end research → extract → integrate pipeline that also finds and
  fills KB gaps → `llm-wiki-deep-research`.
- You just need to fetch/scrape raw sources into files first → `scrape-ingest-organize`.
- You want a one-off cited web report and no vault write → the `deep-research` skill.

## Usage

```
/extract-document-insights "2026-07-01 Regime-Detection Papers" /path/to/paper.pdf
/extract-document-insights "AI Agent Survey" "the transcript above"
/extract-document-insights "Options Vol Reading" https://example.com/article
```

**Session name is REQUIRED** — it names the research session and becomes the output
folder, so related sources cluster together.

## Process

1. **Parse arguments** → separate the session name from the source (file path, URL, or
   an inline "the content above" reference).
2. **Spawn the extractor** via the Task tool:
   ```
   Task(
     subagent_type="document-insight-extractor",
     prompt="Extract insights from: [source] into session '[session-name]'. "
            "Follow your workflow — contextualize the source, classify each insight "
            "epistemically (confirmed / theoretical / speculative), search the vault "
            "for duplicates before creating notes, write the notes, update the "
            "session changelog."
   )
   ```
3. **Report results** — number of insights extracted, epistemic breakdown, and the
   session folder path.
4. **Suggest a next step** — once notes exist, offer to link them into the graph:
   - `llm-wiki-find-connections` to surface non-obvious links from the new notes, or
   - `llm-wiki-integrate-recent-notes` to triage which new notes are still orphaned.

## Outputs

- Insight notes under `Brain/Document Insights/[session]/`.
- A session changelog in the same folder.
- A summary with the epistemic breakdown (confirmed vs. theoretical vs. speculative).
- A suggested follow-up (`llm-wiki-find-connections` / `llm-wiki-integrate-recent-notes`).

## Notes

- Extraction is external-source only; personal-content extraction lives in the sibling
  `llm-wiki-extract-insights`. Keeping the two separate preserves clean epistemic
  provenance in the vault (what a source claims vs. what the user thinks).
- If the source cannot be located (bad path / unreachable URL), stop and report rather
  than fabricating insights — the extractor should surface the failure, not guess.
