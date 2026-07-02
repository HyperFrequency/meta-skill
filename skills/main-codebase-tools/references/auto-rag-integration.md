# Auto-RAG route schema + weight tuning

The `/auto-rag` UserPromptSubmit hook reads `<neuro-link-root>/config/auto-rag-routes.yml`
on every prompt, matches the prompt text against each route's `keywords`, and injects
context from the matching repos' indexed sources. This skill writes one route per
registered repo.

`register_repo.sh` resolves the file as `$NLR_ROOT/config/auto-rag-routes.yml`
(`$NLR_ROOT` defaults to four levels above the script, i.e. the neuro-link repo root).
It is **not** stored in this skill's directory.

## Route schema

```yaml
routes:
  - repo: <repo-slug>            # owner-repo, lowercased, '/' → '-'  (the spec-file stem)
    keywords: [kw1, kw2, kw3]    # 3–5 topics from registration Step 1; lowercased
    index_sources:
      context7: "<resolved-id>"  # "" when Context7 unavailable (Auggie-only route)
      auggie: "<repo-slug>"      # auggie project name; omit/empty if index_auggie:false
    weight: 1.0                  # injection aggressiveness, see below
```

`keywords` are the only matcher — choose terms a prompt about this repo would actually
contain (module names, domain nouns, the project's own name), not generic words like
"code" or "test" that would over-trigger across every repo.

## Success criterion for Step 4

The route write succeeded when:

1. `config/auto-rag-routes.yml` exists and parses as valid YAML (the script seeds it with
   `routes: []` if missing).
2. A route whose `repo` equals the slug is present exactly once (re-registration must not
   duplicate it — `register_repo.sh` refuses if the spec file already exists; use
   `reindex` to refresh instead).
3. At least one `index_sources` entry is non-empty (a route with neither Context7 nor
   Auggie has nothing to inject and should not be written).

## Weight tuning

| Weight | Effect | Use for |
|---|---|---|
| 1.0 (default) | Normal injection when keywords match | Most repos |
| 0.5 | Lighter — fewer / shorter snippets | Thin Context7 coverage, or broad keywords that risk over-triggering |
| 1.5–2.0 | Aggressive — more context, earlier in prompt | The repo the user is actively, heavily working in |

Tune down if the user reports irrelevant context bleeding into unrelated prompts
(usually a too-generic keyword, not the weight). Tune up only for the current focus repo.

## Removal

`/main-codebase-tools remove <slug>` deletes only this repo's route entry from the YAML.
It does not touch shared Context7/Auggie indexes, and it archives (does not delete) the
spec file.
