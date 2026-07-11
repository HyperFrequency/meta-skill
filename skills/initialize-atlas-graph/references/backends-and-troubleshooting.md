# Backends, Keying, and Troubleshooting

## Choosing a backend

The graph root needs a *store*. The manifest schema (`references/graph-schema.md`) is the
same regardless; only where it lives changes.

| Backend                         | Use when                                                | Trade-off                                              |
| ------------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| **Committed JSON ledger** (default) | Solo or small team, want offline + git-native history | Manual merge on concurrent edits; fine at project scale |
| **Graph database** (e.g., Neo4j)    | Large graphs, rich traversal/queries needed             | Requires a running service; keep a committed export as the source of truth |
| **Hosted research tracker**         | Team wants a shared web canvas/UI over the graph        | Network dependency; needs auth; still key off the repo |

The `Run` node's heavy telemetry (per-step metrics, params, artifacts) is best delegated to
a real experiment tracker — **MLflow**, **Weights & Biases**, or **DVC** — with the `Run`
node storing only a *pointer* (`ref`) to the tracker's run id plus summary scalars. Do not
duplicate full metric histories into the graph.

Whatever backend you pick, keep `.atlas/graph.json` (or an exported snapshot) committed so
the repo remains the source of truth and the graph survives losing the external service.

## Repo keying and dedupe

The graph's identity comes from the repository, so the same project resolves consistently
no matter where it is checked out:

- **Preferred key:** the `origin` remote URL (`git config --get remote.origin.url`). Two
  clones of the same remote produce the same `project_id`.
- **Fallback key:** the repo folder name, when no remote is set. Persist the resulting
  `project_id` in the manifest so a later-added remote does not silently re-key the graph.
- **Never** key off the current working directory or absolute path — a subfolder or moved
  checkout would look like a different project.

**Merging duplicate roots.** If two clones each initialized a graph before syncing, you get
two `project_id`s after a merge. Resolve by hand: pick one as canonical, concatenate the
`nodes`/`edges` of the other into it (node `id`s are unique, so union is safe), delete the
duplicate manifest, and commit. Renumber only on `id` collisions.

## Verifying

```bash
root="$(git rev-parse --show-toplevel)"
graph="$root/.atlas/graph.json"

# manifest is valid JSON with the required root fields
jq -e '.project_id and .repo_key and .schema_version' "$graph" && echo "graph OK"

# it is tracked by git (so clones resolve it)
git -C "$root" ls-files --error-unmatch .atlas/graph.json >/dev/null 2>&1 \
  && echo "committed/tracked" || echo "WARNING: manifest is untracked"

# no dangling edges (every from/to references an existing node)
jq -e '[.edges[].from, .edges[].to] - [.nodes[].id] | length == 0' "$graph" \
  && echo "edges reference valid nodes"
```

## Failure modes

| Symptom                                   | Cause                                                   | Fix                                                                 |
| ----------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------- |
| `git rev-parse` fails / "not a git repo"  | Initializing outside a repo; graph has nothing to key off | Run `git init` first, or explicitly key by an absolute project dir  |
| Init "did nothing" / returned an existing id | A graph already exists — this is the idempotency gate working | Expected. Link to the returned `project_id`; do not force a new root |
| Two `project_id`s after a merge            | Concurrent init in separate clones before sync          | Merge into one canonical root (see *Merging duplicate roots*)       |
| Fresh clone reports "no graph"             | `.atlas/graph.json` was gitignored or never committed   | Remove the ignore rule, `git add .atlas/graph.json`, commit          |
| Hosted backend unreachable at init         | Network/DNS/5xx on the remote tracker                   | The local committed manifest still works offline; sync to the remote later — do **not** re-key or re-auth to "fix" a network error |
| `jq: error ... Cannot iterate`             | Manifest truncated by a crash mid-write                 | Always write via temp file + `mv` (atomic); restore from `git checkout -- .atlas/graph.json` |
| Node/edge fields drift between skills      | `schema_version` not bumped after a field change        | Bump `schema_version`; migrate older nodes or gate readers on the version |

## Relationship to other skills

The graph is the *hub*; these skills produce the *spokes*:

- `hypothesis-generation` / `hypogenic` → `Hypothesis` nodes.
- `literature-review` / `citation-management` → `Evidence` nodes of kind `citation`.
- Training/eval/simulation runs → `Run` nodes (with tracker pointers), `Evidence` results.
- `get-available-resources` runs *before* heavy runs; its report can annotate a `Run`'s
  `meta` but is not itself a graph node.

Initialize the graph first; then each of those skills appends to it rather than inventing
its own parallel ledger.
