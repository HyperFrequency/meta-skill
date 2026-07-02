# Workflows W1–W10

## Setup (prerequisites — one-time per machine)

1. **Obsidian vault** at `~/Vaults/neuro-quant-vault` (canonical).
2. **InfraNodus MCP (local OSS)** at `http://infranodus-mcp:9005/sse`. Per `project_infranodus_local_only.md`, never default to `infranodus.com`.
3. **TurboVault MCP** at `http://turbovault:9004/sse` (bind-mounts the vault read-write).
4. **ContextForge gateway** at `localhost:4444` (federates the MCPs).
5. **CouchDB** at `localhost:5984` for Obsidian Self-hosted LiveSync (see `neuro-harness/docs/obsidian-livesync.md`).
6. **CLI tools**:
   - `markitdown` — PDF/DOCX/HTML → markdown (`uv tool install markitdown`)
   - `ripgrep` — fast vault search (`brew install ripgrep`)
   - `jq` — JSON munging
   - `pandoc` — fallback converter for edge formats

Verify the stack:

```bash
for svc in infranodus-mcp:9005 turbovault:9004 gitnexus:9001 tree-sitter:9003; do
  printf "%-30s " "$svc"
  curl -sS --max-time 2 "http://$svc/sse" | head -1
done
mcp2cli --help | head -5
```

If a service is down, surface that to the user before running any workflow.

---

## Build workflows (W1 – W3)

### W1 — `new-tool-wiki`: add a new tool to `deep-tool-wiki/`

Goal: populate one new `deep-tool-wiki/<tool>/` from upstream docs.

```
1. CONFIRM tool name (kebab-case, matches PyPI / GitHub repo name where possible)
2. SCRAPE upstream docs via web-scrape-ingest skill
     → __raw/articles/<tool>-upstream/ as a working set
3. CONVERT non-markdown sources via markitdown
4. CURATE into wikis/deep-tool-wiki/<tool>/:
   - index.md       — purpose, current version, install, upstream URL, status
   - overview.md    — 1-page narrative synthesis (use cornelius-synthesize-insights)
   - api.md         — public surface (only what users touch — avoid the autoreference dump trap)
   - concepts/      — one .md per non-trivial concept the tool surfaces
   - examples/      — minimal runnable code examples
   - pitfalls.md    — known issues, footguns, anti-patterns (see neuro-quant memory)
   - sources.md     — verbatim list of URLs + scrape dates + commit SHAs
5. GENERATE the per-tool ontology directory:
     - For each dimension in {systems, concepts, connections, differences, constraints, sources}:
         ontology-creator <dim>-mode over the curated content (NOT __raw/)
         → wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md
     - Concat the 6 → ontology/full-ontology.md (for tool-local queries)
6. WRITE AGENTS.md per subdirectory (api/, concepts/, examples/) using the
   per-folder template (see conventions.md)
7. RUN W7 (ontology-aggregate) on each of the 6 dimensions
     so the new tool's entries surface in ontologies/
8. RUN W8 (full-wiki-rebuild) so full-wiki-ontology.md picks up the new tool
9. LOG to log.md: timestamp, tool name, page count, ontology size, gap count
```

The `deep-tool-wiki` SKILL automates steps 2-5 for a single tool. This `llm-wiki` skill owns the scaffold (step 1) + the propagation (steps 7-9).

### W2 — `new-agent-knowledge`: add a cross-cutting page to `deep-agent-wiki/`

Goal: when knowledge belongs to NO single tool, place it in the right dimension subfolder.

```
1. CLASSIFY the knowledge to exactly one dimension:
     systems   — it's a concrete deployable thing
     concepts  — it's an abstract idea
     connections — it's a relationship between two named things
     differences — it's a contrast / when-to-use-which
     constraints — it's a limit, anti-pattern, gotcha
     sources   — it's about provenance
   If two dimensions feel right, pick the one closest to the page's title.
   The other dimensions get [[wikilinks]] back to this page in their pages.
2. WRITE wikis/deep-agent-wiki/<dimension>/<slug>.md
   - Title H1 matches the file slug
   - Frontmatter:
       dimension: <dimension>
       cross-links: [tool-a, tool-b, …]   # tools this page connects to
       sources: [<source-page>, …]        # for provenance
       verified: <date>
   - Body: 1-paragraph definition → relations to other entities (wikilinked) →
           code/diagram if useful → references
3. CROSS-LINK from tool wikis: each [[<tool>]] page that mentions this concept
   should [[wikilink]] back to the new page
4. RUN W7 (ontology-aggregate) for the dimension you wrote into
5. LOG to log.md
```

### W3 — `bootstrap`: instantiate the entire structure from zero

One script. Idempotent — running twice does no damage; missing dirs are created, existing ones are left alone.

```bash
VAULT=~/Vaults/neuro-quant-vault

# Top-level structure
mkdir -p "$VAULT"/__raw/{notes,papers,youtube,articles,search-results,patents,books,interviews,__paywalled,assets}
mkdir -p "$VAULT"/wikis/deep-tool-wiki
mkdir -p "$VAULT"/wikis/deep-agent-wiki/{systems,concepts,connections,differences,constraints,sources}
mkdir -p "$VAULT"/ontologies
mkdir -p "$VAULT"/{output,todos}

# Top-level schema files
touch "$VAULT"/{CLAUDE.md,AGENTS.md,log.md}

# Per-folder AGENTS.md
for d in \
  __raw __raw/notes __raw/papers __raw/youtube __raw/articles \
  __raw/search-results __raw/patents __raw/books __raw/interviews \
  __raw/__paywalled \
  wikis/deep-tool-wiki \
  wikis/deep-agent-wiki \
  wikis/deep-agent-wiki/systems wikis/deep-agent-wiki/concepts \
  wikis/deep-agent-wiki/connections wikis/deep-agent-wiki/differences \
  wikis/deep-agent-wiki/constraints wikis/deep-agent-wiki/sources \
  ontologies output todos; do
  touch "$VAULT/$d/AGENTS.md"
done

# Empty global ontology placeholders
for dim in systems concepts connections differences constraints sources full-wiki; do
  touch "$VAULT/ontologies/${dim}-ontology.md"
done

# Per-tool helper — call this when adding a tool (or call it ad-hoc to scaffold
# the tool's ontology/ subfolder before W1 populates content)
init_tool() {
  local tool="$1"
  local tool_root="$VAULT/wikis/deep-tool-wiki/$tool"
  mkdir -p "$tool_root"/{concepts,examples,ontology}
  touch "$tool_root"/{AGENTS.md,index.md,overview.md,api.md,pitfalls.md,changelog.md,sources.md}
  touch "$tool_root/concepts/AGENTS.md" "$tool_root/examples/AGENTS.md"
  for dim in systems concepts connections differences constraints sources; do
    touch "$tool_root/ontology/${dim}-ontology.md"
  done
  touch "$tool_root/ontology/full-ontology.md" "$tool_root/ontology/AGENTS.md"
}
# Usage: init_tool vectorbt

echo "Bootstrap complete. Now run W4 (schema-write) to populate AGENTS.md files."
echo "To add a tool: init_tool <tool-name>"
```

---

## Maintain workflows (W4 – W10)

### W4 — `schema-write`: populate every `AGENTS.md` + the top-level `CLAUDE.md`

Each `AGENTS.md` carries directory-local rules. Use the per-folder template in `conventions.md`; specialize the "What lives here" and "Anti-patterns" sections.

The top-level `CLAUDE.md` / `AGENTS.md` carries the global view + load-bearing memory notes (`project_infranodus_local_only.md`, `feedback_auto_stub_pages.md`, `feedback_vault_root_clean.md`). Template in `conventions.md`.

### W5 — `tool-update`: refresh an existing tool wiki when upstream changes

```
1. DETECT upstream change:
     - Read sources.md to get the canonical URL list + last scrape date
     - Re-fetch each URL through parallel-web with --since=<last-scrape-date>
     - Diff the markdown
2. For each changed page:
     - Re-scrape, re-convert via markitdown
     - Update wikis/deep-tool-wiki/<tool>/<page>.md
     - Append to changelog.md
3. RE-RUN ontology-creator per dimension to refresh wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md
     - Only regenerate dimensions whose source content actually changed
     - Then re-union into ontology/full-ontology.md (W7c)
4. PROPAGATE downstream:
     - For each dimension where the tool ontology changed, mark
       ontologies/<dim>-ontology.md stale → triggers W7
     - W8 will then rebuild full-wiki-ontology.md
5. LOG to log.md
```

### W6 — `cross-tool-link`: discover connections between tools

```
1. COLLECT all wikis/deep-tool-wiki/*/＜tool＞-ontology.md files
2. PASS to infranodus merged_graph_from_texts (via mcp2cli or
   /forge infranodus.merged_graph_from_texts)
3. For each cross-tool edge surfaced in the merged graph:
     a. Check if the connection already has a page in
        wikis/deep-agent-wiki/connections/
     b. If not, create a stub page with the cornelius-find-connections
        skill — frontmatter cross-links to BOTH tool pages
     c. If yes, append the new edge as evidence
4. RUN W7 for the "connections" dimension
5. LOG
```

`cornelius-find-connections` is the prose-driven half of this workflow; InfraNodus is the structural half. Use both.

### W7 — `ontology-aggregate`: rebuild a global dimension ontology

For each dimension `<dim>` in `{systems, concepts, connections, differences, constraints, sources}`:

```
1. COLLECT inputs:
     a. wikis/deep-agent-wiki/<dim>/*.md
     b. wikis/deep-tool-wiki/*/ontology/<dim>-ontology.md
        (one file per tool, pre-computed in W1 step 5 / W5 step 3)
2. PASS the union to ontology-creator with dimension mode <dim>
     (each dimension has its preferred relation-code set + annotation
      tag — see ontology-creator/SKILL.md → "Dimension Modes")
3. WRITE the merged output to ontologies/<dim>-ontology.md
     - Replace the entire file (regenerated, not appended)
     - Sort entities by slug for stable diffs
4. LOG to log.md: dimension, input file count, output relation count
```

Run W7 individually per dimension when only one dimension changed. Run it for all 6 (then W8) after a big ingest.

### W7b — per-tool ontology refresh

When a single tool's content changes but no cross-tool propagation is needed:

```
1. For each dimension whose source content changed:
     ontology-creator <dim>-mode over wikis/deep-tool-wiki/<tool>/
     → wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md
2. Run W7c (full-ontology rebuild for the tool)
3. Trigger W7 (global aggregate) for the changed dimensions
4. Then W8 if at least one global dimension changed
```

### W7c — per-tool `full-ontology.md` rebuild

The per-tool `full-ontology.md` is the union of the tool's six dimension ontologies. Cheap to regenerate; do it whenever any of the 6 dimension files changes:

```
cat wikis/deep-tool-wiki/<tool>/ontology/{systems,concepts,connections,differences,constraints,sources}-ontology.md \
  > wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md.new
# optional: pipe through ontology-creator topic-mode for de-dup + sort
mv wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md.new \
   wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md
```

`full-ontology.md` is the **canonical tool-local query input**. Use it when the question is about one tool. Use `ontologies/full-wiki-ontology.md` when the question spans tools.

### W8 — `full-wiki-rebuild`: combine 6 dimensions into the union ontology

```
1. READ all 6 ontologies/<dim>-ontology.md files
2. CONCATENATE into one corpus
3. PASS to infranodus generate_knowledge_graph
     (this is the canonical input for W9 gap analysis)
4. WRITE the resulting unified graph + relation list to
   ontologies/full-wiki-ontology.md
5. LOG
```

`full-wiki-ontology.md` is the **canonical input** for any cross-wiki query — never query against per-dimension files directly when the question spans dimensions.

### W9 — `gap-analysis`: find what's missing

```
1. FEED ontologies/full-wiki-ontology.md to infranodus generate_content_gaps
2. INTERPRET the returned gap list:
     - Each gap = an unconnected or under-connected entity
     - Each gap is a hint: "scrape source X to fill this in"
3. WRITE todos/<date>-gaps.md with one todo per gap:
     - High-priority: gaps that bridge two existing clusters
     - Low-priority: peripheral gaps
4. CROSS-LINK each todo to the relevant wiki page (so the operator can navigate
   from todo → existing context → fill the gap)
5. LOG
```

Run W9 after every major aggregation cycle (W7 + W8).

### W10 — `lint`: vault hygiene

```
1. ORPHAN PAGES — pages with no incoming wikilinks
     - Tool wikis: every page should be linked from index.md or overview.md
     - Agent wiki: every page should be linked from at least one tool wiki
       OR from the dimension's own ontology
     - Use cornelius-coherence-sweep to detect
2. BROKEN WIKILINKS — [[target]] where target.md doesn't exist
     - Convert to stub if intentional (see __paywalled/ pattern)
     - Otherwise fix the slug or remove
3. STALE verified DATES — frontmatter verified: older than 90 days
     - Schedule a W5 (tool-update) for the relevant tool
4. CONTRADICTIONS — use cornelius-detect-tensions on each dimension folder
     to find pages whose claims contradict each other
5. WRITE output/<date>-lint-report.md
6. LOG
```
