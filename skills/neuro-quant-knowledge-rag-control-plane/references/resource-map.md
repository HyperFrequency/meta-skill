# Knowledge RAG Control Plane Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `neuro-link` | neuro-link | `neuro-link` | `deep-tool-wiki/neuro-link/wiki.md` | `neuro-link/02-KB-main/neuro-link/index.md` | existing-kb-missing-deep |
| `qmd` | QMD | `deep-tool-wiki/qmd` | `deep-tool-wiki/qmd/wiki.md` | `neuro-link/02-KB-main/qmd/index.md` | existing-deep-missing-kb |
| `k-dense-byok` | k-dense-byok | `toolbox/k-dense-byok` | `deep-tool-wiki/k-dense-byok/wiki.md` | `neuro-link/02-KB-main/k-dense-byok/index.md` | missing |
| `vectorbtpro` | vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` | existing-full |
| `nautilus-trader` | Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` | existing-full |
| `pinelsp` | pinelsp | `pinelsp` | `deep-tool-wiki/pinelsp/wiki.md` | `neuro-link/02-KB-main/pinelsp/index.md` | missing |

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.
