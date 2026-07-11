# Atlas Graph Schema

The graph is a small, explicit provenance model. It is deliberately minimal — five node
types and a handful of edge types — so it stays legible in a committed JSON file and
diffs cleanly in review. Treat this schema as a *convention*, not a hard external API:
extend fields as your domain needs, but keep `id`, `type`, and edge `from`/`to`/`rel`
stable so downstream skills can traverse it.

## Manifest shape

`.atlas/graph.json` at the repo root:

```json
{
  "project_id": "a1b2c3d4e5f6a7b8",
  "repo_key": "git@github.com:acme/protein-folding.git",
  "schema_version": "1",
  "created_at": "2026-07-11T12:00:00Z",
  "nodes": [],
  "edges": []
}
```

- `project_id` — stable id derived from `repo_key`; the graph's identity.
- `repo_key` — the origin remote URL (preferred) or repo folder name it was keyed off.
- `schema_version` — bump when you change node/edge field definitions.
- `nodes` / `edges` — appended to as the research progresses.

## Node types

Every node carries `id` (unique within the graph), `type`, `created_at`, and a free-form
`meta` object. Type-specific fields:

| Node         | Key fields                                                                 |
| ------------ | -------------------------------------------------------------------------- |
| `Hypothesis` | `statement`, `prediction`, `status` (`open`/`supported`/`refuted`)         |
| `Experiment` | `question`, `design`, `hypothesis_ids` (which hypotheses it tests)         |
| `Run`        | `experiment_id`, `config` (or a pointer to it), `commit`, `metrics`, `status` |
| `Evidence`   | `kind` (`result`/`figure`/`dataset`/`citation`), `ref` (path/DOI/URL), `summary` |
| `Decision`   | `choice` (`keep`/`revert`/`pivot`/`adopt`), `rationale`, `evidence_ids`    |

`Run.metrics` holds only *summary* scalars (final loss, AUC, etc.) for graph-level
reasoning — full step-wise logs belong in an experiment tracker, referenced by `ref`.

## Edge types

Edges are `{ "from": <id>, "to": <id>, "rel": <string> }`. Recommended relations:

| `rel`        | From → To                | Meaning                                   |
| ------------ | ------------------------ | ----------------------------------------- |
| `tests`      | Experiment → Hypothesis  | this experiment is designed to test it    |
| `instanceOf` | Run → Experiment         | a concrete execution of the experiment    |
| `produces`   | Run → Evidence           | the run generated this evidence           |
| `supports`   | Evidence → Hypothesis    | evidence raises confidence                |
| `refutes`    | Evidence → Hypothesis    | evidence lowers confidence                |
| `basedOn`    | Decision → Evidence      | the decision was made on this evidence    |
| `derivedFrom`| Hypothesis → Hypothesis  | a refined/child hypothesis                 |

## Append-a-node pattern

Adding a node is a read-modify-write on the committed manifest. Keep it atomic (write to a
temp file, then move) so a crash can't leave truncated JSON:

```bash
root="$(git rev-parse --show-toplevel)"
graph="$root/.atlas/graph.json"

node_id="hyp-$(date +%s)"
jq --arg id "$node_id" --arg ts "$(date -u +%FT%TZ)" \
   --arg s "Compound X inhibits enzyme Y" \
   --arg p "IC50 < 1 uM in the binding assay" \
   '.nodes += [{id:$id, type:"Hypothesis", created_at:$ts,
                statement:$s, prediction:$p, status:"open", meta:{}}]' \
   "$graph" > "$graph.tmp" && mv "$graph.tmp" "$graph"
```

Adding an edge is the same pattern against `.edges`:

```bash
jq --arg f "exp-01" --arg t "hyp-1720000000" \
   '.edges += [{from:$f, to:$t, rel:"tests"}]' \
   "$graph" > "$graph.tmp" && mv "$graph.tmp" "$graph"
```

## Worked example

A minimal graph after one hypothesis, one experiment, one run, and a decision:

```json
{
  "project_id": "a1b2c3d4e5f6a7b8",
  "repo_key": "git@github.com:acme/protein-folding.git",
  "schema_version": "1",
  "created_at": "2026-07-11T12:00:00Z",
  "nodes": [
    {"id": "hyp-1", "type": "Hypothesis", "statement": "Dropout 0.3 beats 0.1 on val AUC",
     "prediction": "val AUC +0.02", "status": "supported"},
    {"id": "exp-1", "type": "Experiment", "question": "Does higher dropout regularize better?",
     "design": "sweep dropout {0.1,0.3}, 3 seeds", "hypothesis_ids": ["hyp-1"]},
    {"id": "run-1", "type": "Run", "experiment_id": "exp-1",
     "config": "configs/dropout03.yaml", "commit": "9f2 ...", "metrics": {"val_auc": 0.91}},
    {"id": "ev-1", "type": "Evidence", "kind": "result",
     "ref": "runs/run-1/metrics.json", "summary": "val AUC 0.91 vs 0.89 baseline"},
    {"id": "dec-1", "type": "Decision", "choice": "keep",
     "rationale": "AUC gain exceeds prediction threshold", "evidence_ids": ["ev-1"]}
  ],
  "edges": [
    {"from": "exp-1", "to": "hyp-1", "rel": "tests"},
    {"from": "run-1", "to": "exp-1", "rel": "instanceOf"},
    {"from": "run-1", "to": "ev-1", "rel": "produces"},
    {"from": "ev-1", "to": "hyp-1", "rel": "supports"},
    {"from": "dec-1", "to": "ev-1", "rel": "basedOn"}
  ]
}
```

Traversing `Hypothesis <- tests <- Experiment <- instanceOf <- Run -> produces -> Evidence`
reconstructs the full chain of reasoning behind any claim — which is the entire point of
keeping the graph.
