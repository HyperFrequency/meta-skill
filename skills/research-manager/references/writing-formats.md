# ARA Writing Formats

Canonical on-disk structure and entry templates for the `ara/` artifact. Load this
when you are about to write or update an `ara/` file and need the exact schema.

## ARA Directory Structure

```text
ara/
  PAPER.md                          # Root manifest + layer index
  logic/                            # What & Why
    problem.md                      #   Problem definition + gaps
    claims.md                       #   Falsifiable assertions + proof refs
    concepts.md                     #   Term definitions
    experiments.md                  #   Experiment plans (declarative)
    solution/
      architecture.md               #   System design
      algorithm.md                  #   Math + pseudocode
      constraints.md                #   Boundary conditions
      heuristics.md                 #   Tricks + rationale + sensitivity
    related_work.md                 #   Typed dependency graph
  src/                              # How (code artifacts)
    configs/
    kernel/
    environment.md
  trace/                            # Journey
    exploration_tree.yaml           #   Research DAG
    sessions/
      session_index.yaml            #   Master session index
      YYYY-MM-DD_NNN.yaml          #   Individual session records
  evidence/                         # Raw Proof
    README.md
    tables/
    figures/
  staging/                          # Unclassified observations
    observations.yaml
```

## Exploration Tree Structure (exploration_tree.yaml)

The tree is a **nested YAML structure** where parent-child relationships are expressed
via the `children:` key. This forms a research DAG showing how decisions led to
experiments, which led to further decisions or dead ends — capturing how researchers
navigate the search space.

- Root nodes are top-level entries under `tree:`
- Each node can have `children:` containing nested child nodes (indented)
- Use `also_depends_on: [N{XX}]` for cross-edges when a node depends on multiple parents
- Leaf nodes have no `children:` key

**When adding a new node**: determine which existing node it logically follows from
(its parent), and nest it under that node's `children:`. If it's a new top-level
research thread, add it as a root node.

```yaml
tree:
  - id: N01
    type: question
    title: "{root research question}"
    provenance: user
    timestamp: "YYYY-MM-DDTHH:MM"
    description: >
      {what is being explored}
    children:

      - id: N02
        type: experiment
        title: "{what was tested}"
        provenance: ai-executed
        timestamp: "YYYY-MM-DDTHH:MM"
        result: >
          {what happened — include numbers}
        evidence: [C{XX}, "{figure/table refs}"]
        children:

          - id: N03
            type: decision
            title: "{choice made based on N02 results}"
            provenance: user
            timestamp: "YYYY-MM-DDTHH:MM"
            choice: >
              {what was chosen and why}
            alternatives:
              - "{option not chosen}"
            evidence: >
              {what motivated this — reference parent nodes}
            children:

              - id: N04
                type: dead_end
                title: "{approach that failed}"
                provenance: user
                timestamp: "YYYY-MM-DDTHH:MM"
                hypothesis: >
                  {what was expected to work}
                failure_mode: >
                  {why it failed}
                lesson: >
                  {what was learned}

              - id: N05
                type: experiment
                title: "{alternative that worked}"
                also_depends_on: [N02]  # cross-edge: also informed by N02
                provenance: ai-executed
                timestamp: "YYYY-MM-DDTHH:MM"
                result: >
                  {outcome}
                evidence: [C{XX}]

      - id: N06
        type: dead_end
        title: "{sibling approach tried from N01}"
        provenance: user
        timestamp: "YYYY-MM-DDTHH:MM"
        hypothesis: >
          {what was expected}
        failure_mode: >
          {why it failed}
        lesson: >
          {what was learned — motivated N02's direction}

  - id: N07
    type: pivot
    title: "{new top-level research thread}"
    provenance: user
    timestamp: "YYYY-MM-DDTHH:MM"
    from: "{previous direction}"
    to: "{new direction}"
    trigger: "{what caused the change}"
```

### Node Type Reference

| Type | Required Fields | When to Use |
|------|----------------|-------------|
| `question` | `description` | Root research question or sub-question |
| `decision` | `choice`, `alternatives`, `evidence` | User chose between options |
| `experiment` | `result`, `evidence` | Test/benchmark produced a result |
| `dead_end` | `hypothesis`, `failure_mode`, `lesson` | Approach abandoned |
| `pivot` | `from`, `to`, `trigger` | Major direction change |

## Claim (logic/claims.md)

```markdown
## C{XX}: {title}
- **Statement**: {falsifiable assertion}
- **Status**: hypothesis | untested | testing | supported | weakened | refuted | revised
- **Provenance**: user | ai-suggested | user-revised
- **Falsification criteria**: {what would disprove this}
- **Proof**: [{evidence refs or "pending"}]
- **Dependencies**: [C{YY}, ...]
- **Tags**: {comma-separated}
```

## Heuristic (logic/solution/heuristics.md)

```markdown
## H{XX}: {title}
- **Rationale**: {why this works}
- **Provenance**: user | ai-suggested | user-revised
- **Sensitivity**: low | medium | high
- **Code ref**: [{file paths}]
```

## Observation (staging/observations.yaml)

```yaml
- id: O{XX}
  timestamp: "YYYY-MM-DDTHH:MM"
  provenance: user | ai-suggested | ai-executed
  content: "{raw observation}"
  context: "{what was happening}"
  potential_type: claim | heuristic | decision | unknown
  promoted: false
```

## Session Record (trace/sessions/YYYY-MM-DD_NNN.yaml)

```yaml
session:
  id: "YYYY-MM-DD_NNN"
  timestamp: "YYYY-MM-DDTHH:MM"
  summary: "{one-line summary of what happened}"

events_logged:
  - type: decision | experiment | dead_end | pivot | claim | heuristic | observation
    id: "{N/C/H/O}{XX}"
    provenance: user | ai-suggested | ai-executed | user-revised
    summary: "{what}"

ai_actions:
  - action: "{what AI did}"
    provenance: ai-executed
    files_changed: ["{paths}"]

claims_touched:
  - id: C{XX}
    action: created | advanced | weakened | confirmed
    provenance: user | ai-suggested

open_threads:
  - "{what needs follow-up}"

ai_suggestions_pending:
  - "{unconfirmed AI suggestions from this session}"
```

## Initialization (if ara/ does not exist)

Create the full directory structure and seed files automatically. Do not ask.

```bash
mkdir -p ara/{logic/solution,src/{configs,kernel},trace/sessions,evidence/{tables,figures},staging}
```

Then write:

1. `ara/PAPER.md` — root manifest (infer title, authors, venue from project context)
2. `ara/trace/sessions/session_index.yaml` — `sessions: []`
3. `ara/trace/exploration_tree.yaml` — `tree: []`
4. `ara/staging/observations.yaml` — `observations: []`
5. `ara/logic/claims.md` — `# Claims`
6. `ara/logic/problem.md` — `# Problem`
7. `ara/logic/solution/heuristics.md` — `# Heuristics`
8. `ara/evidence/README.md` — `# Evidence Index`
