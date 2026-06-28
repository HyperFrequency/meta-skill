# Forecasting Oracle ML Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `tabpfn` | TabPFN | `toolbox/TabPFN` | `deep-tool-wiki/tabpfn/wiki.md` | `neuro-link/02-KB-main/tabpfn/index.md` | missing |
| `chronos-forecasting` | chronos-forecasting | `toolbox/chronos-forecasting` | `deep-tool-wiki/chronos-forecasting/wiki.md` | `neuro-link/02-KB-main/chronos-forecasting/index.md` | missing |
| `ludwig` | Ludwig | `toolbox/ludwig` | `deep-tool-wiki/ludwig/wiki.md` | `neuro-link/02-KB-main/ludwig/index.md` | missing |
| `h2o-3` | h2o-3 | `toolbox/h2o-3` | `deep-tool-wiki/h2o-3/wiki.md` | `neuro-link/02-KB-main/h2o-3/index.md` | existing-deep-missing-kb |
| `hmmlearn` | hmmlearn | `toolbox/hmmlearn` | `deep-tool-wiki/hmmlearn/wiki.md` | `neuro-link/02-KB-main/hmmlearn/index.md` | missing |
| `deeplob` | DeepLOB | `toolbox/DeepLOB` | `deep-tool-wiki/deeplob/wiki.md` | `neuro-link/02-KB-main/deeplob/index.md` | missing |
| `tlob` | TLOB | `toolbox/TLOB` | `deep-tool-wiki/tlob/wiki.md` | `neuro-link/02-KB-main/tlob/index.md` | missing |

## Local Family Docs (Level 1)

Before the per-tool wiki/KB paths above, check these repo-local family notes:

- `toolbox/docs/tools/oracle-ml-family.md`: shared family overview and install status.
- `toolbox/docs/tools/h2o.md`: H2O JDK/JAVA_HOME and cluster lifecycle notes.
- `toolbox/_pending/deeplob.md`, `toolbox/_pending/tlob.md`: packaging status for the LOB
  research repos. If these still show no install metadata, treat DeepLOB/TLOB as
  script/notebook work and do not invent an import path.
- `.batch-runs/.../evidence` and current venv commands: fresh proof for any runtime claim.

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.
