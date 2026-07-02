---
name: llm-wiki-extract-insights
version: 0.2.0
description: Mine the USER'S OWN raw internal material — conversation transcripts, voice-memo/meeting dumps, journals, freewrites, rough notes — for their original thinking (personal theories, contrarian takes, synthesis leaps, hard-won heuristics), preserving their voice, deduping against the existing vault, and writing atomic permanent notes into the Obsidian/turbovault vault. Use WHEN the user says "extract insights from this transcript/journal/conversation", "pull my original ideas out of these notes", "turn this brain-dump into permanent notes", or points at their own recorded content. Do NOT use for external documents/papers/books/PDFs (use llm-wiki-extract-document-insights), for combining notes that ALREADY exist into a framework or article (use llm-wiki-synthesize-insights), for whole-vault structure/hub/cluster analysis (use llm-wiki-analyze-kb), for mining hidden cross-domain links (use llm-wiki-auto-discovery), or for triaging recently-added notes (use llm-wiki-integrate-recent-notes).
allowed-tools: [Task]
user-invocable: true
arg-description: "<file path or a pointer to the user's own content (e.g. 'the conversation above')>"
---

# Extract Insights

Lean router. Extracts the user's *original* thinking from their **own** raw material and lands it as atomic permanent notes in the vault. This is the internal-source counterpart to `llm-wiki-extract-document-insights` (external sources) — the two never overlap.

## When this fires (vs. when it does not)

Fires for **first-party raw material the user produced**: transcripts, voice/meeting dumps, journals, freewrites, chat logs, rough notes. The job is *distillation of the user's own ideas*, not summarization of someone else's argument.

Route elsewhere when:
- Source is an external document (paper, book, article, PDF) → `llm-wiki-extract-document-insights`
- The notes to combine **already exist** in the vault → `llm-wiki-synthesize-insights`
- You want vault-wide structure (hubs, clusters, bridges) → `llm-wiki-analyze-kb`
- You want surprising cross-domain links surfaced → `llm-wiki-auto-discovery`
- You want recently-added notes triaged for connectedness → `llm-wiki-integrate-recent-notes`

## Usage

```
/llm-wiki-extract-insights /path/to/transcript.md
/llm-wiki-extract-insights "the conversation above about dopamine and habit loops"
```

## What gets extracted

Signal (keep): personal theories, contrarian positions, cross-domain synthesis, non-obvious heuristics, framings the user arrived at themselves.
Noise (drop): restated common knowledge, generic advice, transcription filler, ideas already captured in the vault.

## Process

1. **Resolve the source** from the argument — a file path, or a pointer to content already in context. If ambiguous, ask which content before spawning.
2. **Spawn the extractor** via `Task`, handing it the resolved source and the mandatory workflow below:

   ```
   Task(
     description="Extract insights from user's own content",
     prompt="""Extract the user's ORIGINAL insights from: <resolved source>.
     Mandatory workflow:
     1. Contextualize — read the whole source; note the user's voice and recurring framings.
     2. Chunk large sources so nothing is truncated.
     3. Search the vault (turbovault semantic search) for near-duplicates; skip anything already captured.
     4. Extract only original thinking (theories, contrarian views, synthesis, heuristics) — preserve the user's wording.
     5. Write one atomic permanent note per insight into the vault's extracted-notes folder, wikilinking to related existing notes.
     6. Append a run entry to the vault changelog: source, notes created, duplicates skipped.
     Report counts back."""
   )
   ```

   > No standalone `insight-extractor` subagent is required; the prompt above IS the contract. If a project-local extractor subagent exists, pass its `subagent_type`.
3. **Report** insights extracted, permanent notes created, and duplicates skipped.

## Outputs

- One atomic permanent note per surviving insight, wikilinked into the Obsidian/turbovault vault.
- A changelog entry recording the run (source, created, skipped).
- A summary of what was extracted.

## Edge cases

- **Empty / trivial source** → report "no original insights found"; create nothing.
- **Everything is a duplicate** → create nothing; note it in the changelog.
- **No vault index available** → still extract, but flag that dedup was skipped so the user can run integration later.
