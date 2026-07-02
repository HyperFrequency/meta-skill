---
name: llm-wiki-brain-merge
version: 0.2.0
description: Compare and selectively merge two separate knowledge vaults / note directories (Obsidian, turbovault, or any markdown folder), then rebuild the target vault's search index. Modes — diff (what's unique to each side), pull (import notes from a source into your target), learn (bidirectional exchange, approval per direction). Use WHEN the user names TWO vaults or brain/note folders and wants to reconcile, sync, transfer, or seed one from the other ("merge that vault into mine", "what's unique in the other brain", "pull its notes", "seed a new vault from my old one"). Do NOT use for single-vault work — structure/cluster analysis (llm-wiki-analyze-kb), recent-note triage (llm-wiki-integrate-recent-notes), connection discovery (llm-wiki-find-connections), notes into prose (llm-wiki-synthesize-insights). Do NOT use for git/branch merges, file-level source diffs, or whole code repos (use repo-merge). Only moves markdown between two vault dirs and refreshes the local index.
automation: gated
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent]
user-invocable: true
---

# Vault Brain Merge

Compare and selectively merge knowledge between **two separate vaults** — any two directories of markdown notes (an Obsidian vault, a turbovault-backed brain, or a plain notes folder). Path-agnostic: it is not tied to a fixed location.

Vaults grow independently and accumulate unique notes. This skill lets you see what each side has that the other lacks and move notes between them safely, then rebuilds the target's search index so retrieval stays current.

This is a **router**: pick a mode, run its steps, respect the gates.

## When this skill (and when a sibling instead)

Use it only when the user is working across **two vaults**. For single-vault operations, route to the sibling that owns it:

- Whole-vault structure / clusters / hubs → `llm-wiki-analyze-kb`
- Triage of recently added / orphaned notes → `llm-wiki-integrate-recent-notes`
- Connections around one note or topic → `llm-wiki-find-connections`
- Combining notes into a narrative or framework → `llm-wiki-synthesize-insights`
- Merging whole code repositories → `repo-merge`
- git/branch merges or file-level source diffs → plain git tooling, not this skill

## Modes

- **diff** — compare two vaults, report what is unique to each
- **pull** — import selected notes from a source vault into a target vault
- **learn** — bidirectional exchange, with an approval gate per direction

## State dependencies

| Source | Location | Read | Write |
|--------|----------|------|-------|
| Source vault | user-specified path | ✓ | — |
| Target vault | user-specified path (default: current vault) | ✓ | ✓ |
| Target search index | rebuilt via `turbovault` after any change | — | ✓ |

## Step 0: Resolve inputs

Ask (or infer from the request):

1. **Source vault path** — the vault to compare against or pull from
2. **Target vault path** — the vault to compare or import into (default: current vault)
3. **Mode** — diff, pull, or learn

If a path is ambiguous ("the other one", a bare name), scan nearby directories for markdown vaults and present a pick list. A vault is any directory containing `.md` files; an Obsidian vault also has an `.obsidian/` folder:

```bash
# candidate vaults: dirs with a .obsidian marker, plus any dir holding .md files
find "$HOME" -maxdepth 4 -name ".obsidian" -type d 2>/dev/null | sed 's|/.obsidian$||' | sort
```

### Pre-flight integrity checks

Before any compare or copy, validate both sides. Abort and report if a check fails — never merge into or out of a malformed vault.

```bash
for VAULT in "$SOURCE" "$TARGET"; do
  [ -d "$VAULT" ]  || { echo "MISSING: $VAULT is not a directory"; exit 1; }
  [ -r "$VAULT" ]  || { echo "UNREADABLE: $VAULT"; exit 1; }
  [ -n "$(find "$VAULT" -name '*.md' -print -quit)" ] \
                   || echo "WARN: $VAULT has no .md files (empty/wrong path?)"
done
[ -w "$TARGET" ]   || { echo "READ-ONLY target: $TARGET"; exit 1; }
```

Also confirm source and target are not the same path (a self-merge is a no-op) and that target is not a subdirectory of source (rsync into a parent can recurse). If either holds, stop and re-confirm paths with the user.

---

## DIFF MODE

**Goal:** show what each vault has that the other doesn't, grouped by folder.

### Step 1: Inventory both vaults

```bash
SOURCE="[SOURCE_VAULT_PATH]"
TARGET="[TARGET_VAULT_PATH]"

find "$SOURCE" -name "*.md" | sed "s|$SOURCE/||" | sort > /tmp/vault_source.txt
find "$TARGET" -name "*.md" | sed "s|$TARGET/||" | sort > /tmp/vault_target.txt

echo "Source: $(wc -l < /tmp/vault_source.txt) files"
echo "Target: $(wc -l < /tmp/vault_target.txt) files"
```

### Step 2: Generate diff lists

```bash
comm -23 /tmp/vault_source.txt /tmp/vault_target.txt > /tmp/unique_to_source.txt
comm -13 /tmp/vault_source.txt /tmp/vault_target.txt > /tmp/unique_to_target.txt
comm -12 /tmp/vault_source.txt /tmp/vault_target.txt > /tmp/in_both.txt

echo "Unique to source: $(wc -l < /tmp/unique_to_source.txt)"
echo "Unique to target: $(wc -l < /tmp/unique_to_target.txt)"
echo "In both: $(wc -l < /tmp/in_both.txt)"
```

### Step 3: Group by folder and present

```bash
echo "=== UNIQUE TO SOURCE ==="
awk -F'/' '{print $1}' /tmp/unique_to_source.txt | sort | uniq -c | sort -rn

echo "=== UNIQUE TO TARGET ==="
awk -F'/' '{print $1}' /tmp/unique_to_target.txt | sort | uniq -c | sort -rn
```

For each folder, show a few sample filenames so the user gets a sense of what's there. Present as a clean table, and note folders that exist in one vault but not the other (structural differences).

**Gate 1:** present the report, then ask: "Want to pull any of this into your vault? Which folders or files?"

---

## PULL MODE

**Goal:** import specific notes from source into target, safely.

### Step 1: run diff (if not already done)

### Step 2: clarify scope

If not specified, ask which folders or files to pull (a folder name, all unique files, or specific filenames).

**Gate 2:** confirm scope before touching anything:
> "About to copy [N] files from [source] → [target]. Files already in target will be SKIPPED. Proceed?"

### Step 3: execute copy (never overwrites existing notes)

```bash
rsync -av --ignore-existing \
  "[SOURCE]/[SELECTED_FOLDER]/" \
  "[TARGET]/[SELECTED_FOLDER]/"
```

For a full unique-file pull:

```bash
while IFS= read -r file; do
  dest="[TARGET]/$file"
  mkdir -p "$(dirname "$dest")"
  cp -n "[SOURCE]/$file" "$dest"
done < /tmp/unique_to_source.txt
```

### Step 4: refresh the target index

Rebuild the target vault's search index via the `turbovault` skill so retrieval reflects the new notes. Report total files copied, skipped, and confirm the index refreshed.

---

## LEARN MODE

**Goal:** bidirectional exchange — each vault gets what the other has.

### Step 1: run diff in both directions

### Step 2: source → target

Show what source has that target lacks.

**Gate 3:** "Source has [N] unique files. Pull into target? (y/n/select folders)" — if approved, run the pull.

### Step 3: target → source

Show what target has that source lacks.

**Gate 4:** "Target has [M] unique files. Push into source? (y/n/select folders)" — if approved:

```bash
rsync -av --ignore-existing \
  "[TARGET]/[SELECTED_FOLDER]/" \
  "[SOURCE]/[SELECTED_FOLDER]/"
```

### Step 4: refresh indexes on both sides

Rebuild the search index for **both** vaults via `turbovault` (they both changed). Report files exchanged in each direction and confirm both indexes refreshed.

---

## Tips

- **Start with diff** — understand what you're working with before moving anything.
- **Safe by default** — `--ignore-existing` / `cp -n` never overwrites existing notes.
- **Content conflicts** — same filename, different content is flagged but not auto-resolved; recommend manual review.
- **Structural differences** — folders present in only one vault are worth surfacing (the vaults may have evolved differently).
- **Index refresh** — always runs after file changes so search stays current.

## Error recovery

- Copy fails mid-way → re-run; `--ignore-existing` / `cp -n` make it idempotent.
- Index rebuild fails → re-run the `turbovault` reindex for that vault.
- Paths not found → re-run the Step 0 discovery scan.

## Boundaries

- Only moves markdown between two vault directories and refreshes the local index — no in-place note edits, no ontology generation, no ingestion of external sources.
- Not for merging code repositories (`repo-merge`), git/branch merges, or file-level source diffs.

## Adjacent skills

`turbovault` (vault index + queries), `llm-wiki` (scaffold/maintain a single wiki), `llm-wiki-analyze-kb`, `llm-wiki-integrate-recent-notes`, `llm-wiki-find-connections`, `llm-wiki-synthesize-insights`, `repo-merge`.
