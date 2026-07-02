# Sync patterns — upstream change → affected pages mapping

Re-syncing a toolbox wiki should regenerate only the pages a release actually
touched, not the whole directory. This file describes the diff-to-affected-pages
mapping used by the re-sync flow (SKILL.md "Sync cadence", step 3).

## Inputs

- The wiki dir `08-code-docs/toolbox/<tool>/` with per-page frontmatter
  (`version_indexed`, `primary_sources`).
- The upstream mirror under `state/mirrors/toolbox/<slug>/`, refreshed to the
  latest release tag (or HEAD if the tool is untagged).
- The upstream `CHANGELOG.md` (or `git log` between `version_indexed` and the
  new tag when no changelog exists).

## Algorithm

1. **Refresh mirror** to the new tag. Record `old = version_indexed`,
   `new = <tag>`.
2. **Build the change set.** Prefer the CHANGELOG section(s) between `old` and
   `new`. If absent, fall back to `git diff --name-only old..new` to get changed
   paths plus commit subjects for keywords.
3. **Extract signals** from the change set:
   - changed file paths (e.g. `src/llm.ts`, `README.md`)
   - keywords from changelog entry text (API names, config keys, "BREAKING")
4. **Match against pages.** For each wiki page, mark it *affected* if either:
   - any `primary_sources` entry matches a changed path (exact or directory
     prefix — `src/` matches `src/llm.ts`), or
   - a changelog keyword appears in the page body or its frontmatter
     (`open_questions` often name the exact thing a release fixes).
5. **Regenerate** only affected pages via `/wiki-curate` against the refreshed
   mirror. Always treat `05-changelog-watch.md` as affected on any version bump.
6. **Bump metadata** on regenerated pages: `version_indexed = new`,
   `last_synced = today`. Leave untouched pages' `version_indexed` alone so the
   next sync still diffs from their real baseline.

## Match precedence

When both a path match and a keyword match fire, path wins (higher confidence).
A `BREAKING` keyword forces every page whose `primary_sources` intersect the
changed paths to be regenerated even if the body looks unrelated, because
breaking changes commonly ripple into config and integration pages.

## Edge cases

- **No tags, no changelog:** diff HEAD against the commit recorded at last sync
  (store it alongside `version_indexed` as a short SHA in the page or in
  `config/toolbox-watch.yml`).
- **Renamed/deleted upstream files:** a `primary_sources` entry that no longer
  exists is itself a signal — flag the page for review rather than silently
  skipping it.
- **Docs-only release:** if only `README`/docs changed, regenerate the
  architecture/overview pages but skip API/config unless keywords say otherwise.
- **Huge diff (major bump):** regenerate the whole directory; partial syncs are
  unreliable across a major version boundary.
