# Gap analysis — interpreting knowledge-graph signals into task specs

Pass 4 of `/neuro-scan` runs three checks against the semantic knowledge graph
(via TurboVault) and the reasoning ontologies (via InfraNodus). This reference
explains how to read each signal and the task spec it should produce. The scan
itself is non-mutating: every finding becomes a *pending* task file in
`00-neuro-link/tasks/`, never a direct edit.

## Signal 1 — Stale hubs (`tv_get_hub_notes`)

`tv_get_hub_notes` returns the top-N concepts by graph centrality. A hub is a
load-bearing note that many other notes link to. When a hub's `last_updated` is
older than 30 days it is high-leverage but unaudited.

- Interpretation: the concept is still central but may have drifted from current
  practice. Risk scales with how many notes depend on it.
- Remediation task type: `curate` (refresh an existing page), priority inherited
  from centrality rank (top-5 hub → priority 1, top-20 → priority 2).

## Signal 2 — Isolated clusters (`tv_get_isolated_clusters`)

`tv_get_isolated_clusters` finds disconnected subgraphs in `02-KB-main/`. A
cluster that does not link to the main body is a knowledge island — usually a
topic that was ingested but never cross-linked, i.e. a structural gap.

- Interpretation: missing connective tissue, not necessarily missing content.
  The fix is usually adding links/MOC entries, occasionally a bridging note.
- Remediation task type: `ingest` when the island is thin (needs more content),
  `ontology` when the island is rich but unlinked (needs relationship edges).

## Signal 3 — Content gaps + adversarial review (InfraNodus)

Run InfraNodus `content_gap` and `adversarial_review` on each ontology in
`03-Ontology-main/`. Two distinct findings come out:

1. `content_gap`: topics the ontology references that have no backing wiki page
   in `02-KB-main/`. Each is a concrete page to write.
   - Remediation task type: `ingest`, priority 2.
2. `adversarial_review`: contradictions *between* ontologies — e.g. the workflow
   ontology and an agent ontology assert incompatible relations on the same node.
   - Remediation task type: `ontology`, priority 1 (contradictions are
     load-bearing and block downstream reasoning).

## Writing the task spec

Every gap finding produces one task file. Use the standard frontmatter from
`SKILL.md` ("Auto-queued tasks") and fill the type/priority per the mapping
above. Keep the body to: what the gap is, which signal surfaced it, and the
concrete artifact to produce (page path, ontology edge, or link set). Set
`source: neuro-scan` and `scan_date` so the finding is traceable back to the run.

| Signal                        | Tool                       | Task type  | Default priority |
| ----------------------------- | -------------------------- | ---------- | ---------------- |
| Stale hub                     | `tv_get_hub_notes`         | `curate`   | 1–2 by rank      |
| Isolated cluster (thin)       | `tv_get_isolated_clusters` | `ingest`   | 2                |
| Isolated cluster (rich)       | `tv_get_isolated_clusters` | `ontology` | 2                |
| Content gap (missing page)    | InfraNodus `content_gap`   | `ingest`   | 2                |
| Cross-ontology contradiction  | `adversarial_review`       | `ontology` | 1                |

De-dupe before queuing: if a gap already has an open pending task with the same
target, skip it rather than queue a duplicate.
