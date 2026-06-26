---
name: ontology-generator
description: Generate comprehensive ontological knowledge graphs in [[wikilinks]] syntax for InfraNodus visualization. Use when the user requests to create an ontology, extract entities and relationships from text, or generate knowledge graph structures. Handles both topic-based ontology generation and entity extraction from existing text. Output is formatted for direct paste into InfraNodus.com for network visualization and AI-powered gap analysis.
---

# Ontology Generator for InfraNodus

Generate ontological knowledge graphs in InfraNodus format using [[wikilinks]] syntax. Output can be pasted directly into InfraNodus.com to visualize as a network and develop gaps and clusters with AI.

## Input Types

Accept these input types:

1. **Topic**: Generate comprehensive ontology for a given domain
2. **Text**: Extract ontological structure from provided text
3. **Macro / Domain**: Generate a layered ontology covering an entire problem space — its subdomains, methods, artifacts, and stakeholders (see Specialized Modes below)
4. **Agent**: Capture an AI agent's capabilities, tools, state, goals, and constraints as a network (see Specialized Modes)
5. **Workflow State**: Represent a workflow's steps, transitions, preconditions, postconditions, and failure modes (see Specialized Modes)
6. **Dimension (6 sub-modes — for the `llm-wiki` skill's ontology layer)**: Generate a single-dimension ontology focused on one of the canonical wiki dimensions. Sub-modes: `systems`, `concepts`, `connections`, `differences`, `constraints`, `sources` (see Specialized Modes below)

## Specialized Modes

When the user invokes one of these modes (or the input clearly fits one), produce ontologies that respect that mode's conventions in addition to the general rules below.

### Macro / Domain Mode

Use when the user asks for an ontology of an *entire* problem space (e.g. "quantitative trading", "drug discovery", "the neuro-quant stack"). Goal: a layered ontology that explicitly distinguishes scale.

Required layers (each contributes ~8+ relations):

- **Subdomains** — what areas the macro domain decomposes into (`[partOf]`)
- **Methods** — techniques and approaches used (`[isA]`, `[derivedFrom]`)
- **Artifacts** — concrete outputs, data, models, tools (`[hasAttribute]`, `[partOf]`)
- **Stakeholders / agents** — humans, teams, automated agents (`[relatedTo]`, `[dependentOn]`)
- **Cross-layer bridges** — relations spanning two layers (e.g. method → artifact, agent → method)

Add a `[scale: macro|domain|task]` annotation to each relation when ambiguous, e.g.:

```
[[walk-forward optimization]] is a method within [[quant validation]] [isA] [scale: domain]
[[neuro-quant]] coordinates [[strategy-workflow]] across [[nautilus-trader]] [relatedTo] [scale: macro]
```

### Agent Mode

Use when modelling an AI agent (skill, subagent, MCP server). Goal: a network that captures what the agent *is*, *does*, *needs*, and *avoids*.

Required dimensions (each ~8+ relations):

- **Identity** — name, role, version (`[hasAttribute]`)
- **Capabilities** — what the agent can do (`[isA]`, `[causes]`)
- **Tools** — MCP servers, CLIs, file-system access (`[dependentOn]`, `[partOf]`)
- **State** — current mode, memory contents, in-progress work (`[hasAttribute]`, `[occursAt]`)
- **Goals** — objectives and success criteria (`[causes]`, `[dependentOn]`)
- **Constraints** — guardrails, refusals, budgets (`[opposes]`, `[dependentOn]`)

Add a `[dim: identity|capability|tool|state|goal|constraint]` annotation. Example:

```
[[research-lookup-agent]] uses [[parallel-web-mcp]] for source retrieval [dependentOn] [dim: tool]
[[research-lookup-agent]] must avoid [[hallucinated-citations]] [opposes] [dim: constraint]
[[research-lookup-agent]] currently holds [[half-finished-bibliography]] in memory [hasAttribute] [dim: state]
```

### Workflow State Mode

Use when modelling a multi-step workflow as a graph. Goal: a network where steps, transitions, and conditions are first-class entities.

Required node types (each ~8+ relations):

- **Steps** — discrete actions or stages (`[partOf]` the workflow)
- **Transitions** — directed moves between steps (`[causes]`, `[derivedFrom]`)
- **Preconditions / postconditions** — what must hold before/after (`[dependentOn]`, `[hasAttribute]`)
- **Artifacts** — what the step produces or consumes (`[partOf]`, `[derivedFrom]`)
- **Failure modes** — what can go wrong, and the compensating transitions (`[opposes]`, `[causes]`)

Add a `[type: step|transition|precond|postcond|artifact|failure]` annotation. Example:

```
[[backtest-step]] requires [[clean-ohlcv-data]] as precondition [dependentOn] [type: precond]
[[backtest-step]] produces [[tearsheet-html]] as artifact [causes] [type: artifact]
[[backtest-step]] transitions to [[walk-forward-step]] when [[in-sample-sharpe]] exceeds threshold [causes] [type: transition]
[[backtest-step]] fails when [[data-gap]] is detected, falling back to [[data-refetch-step]] [opposes] [type: failure]
```

Network discipline still applies in all three specialized modes: avoid hub-and-spoke topologies. If "the workflow" or "the agent" or "the macro domain" itself becomes a hub appearing in every paragraph, you are writing a tree — rebalance toward cross-references between the layered entities.

### Dimension Modes (for the `llm-wiki` skill's ontology layer)

Six narrow modes designed to feed the `llm-wiki` skill's per-dimension ontology files. Each mode produces a focused single-dimension graph — not a full-spectrum ontology. The `llm-wiki` workflow W7 (`ontology-aggregate`) calls one of these modes per output file, then concatenates the six into `ontologies/full-wiki-ontology.md` in W8.

Each dimension has a canonical question, a preferred annotation tag, and a recommended relation-code set. Stay inside the recommended set unless an entity genuinely demands a relation outside it — then add it and note the deviation.

#### `systems` mode

**Question**: What concrete deployable things exist in this domain?

**Annotation tag**: `[type: server|service|module|venue|exchange|library|cli|process|container|cluster]`

**Preferred relation codes**: `[isA]`, `[partOf]`, `[locatedIn]`, `[dependentOn]`, `[hasAttribute]`

**Example**:

```
[[nautilus-trader]] is an instance of [[algorithmic-trading-platform]] [isA] [type: library]
[[trading-node]] is part of [[nautilus-trader]] [partOf] [type: module]
[[hyperliquid-adapter]] is located in [[trading-node]] [locatedIn] [type: module]
[[backtest-engine]] depends on [[parquet-data-catalog]] [dependentOn] [type: module]
[[order-book-l2]] has attribute [[depth-aggregated]] [hasAttribute] [type: module]
```

Use when populating: `ontologies/systems-ontology.md`, `wikis/deep-tool-wiki/<tool>/ontology/systems-ontology.md`, `wikis/deep-agent-wiki/systems/`.

#### `concepts` mode

**Question**: What abstract ideas matter — algorithms, theories, methods, principles, metrics?

**Annotation tag**: `[type: algorithm|theory|method|principle|metric|model|paradigm]`

**Preferred relation codes**: `[isA]`, `[derivedFrom]`, `[hasAttribute]`, `[opposes]`, `[relatedTo]`

**Example**:

```
[[walk-forward-validation]] is a type of [[out-of-sample-validation]] [isA] [type: method]
[[deflated-sharpe-ratio]] is derived from [[sharpe-ratio]] [derivedFrom] [type: metric]
[[walk-forward-validation]] has attribute [[purged-cv]] [hasAttribute] [type: method]
[[k-fold-cv]] opposes [[purged-embargoed-cv]] for time-series [opposes] [type: method]
[[probability-of-backtest-overfitting]] is related to [[deflated-sharpe-ratio]] [relatedTo] [type: metric]
```

Use when populating: `ontologies/concepts-ontology.md`, `wikis/deep-tool-wiki/<tool>/ontology/concepts-ontology.md`, `wikis/deep-agent-wiki/concepts/`.

#### `connections` mode

**Question**: What depends on / cites / implements / wraps / extends what?

**Annotation tag**: `[type: depends|cites|implements|extends|wraps|integrates|forks]`

**Preferred relation codes**: `[dependentOn]`, `[derivedFrom]`, `[partOf]`, `[causes]`, `[relatedTo]`

**Example**:

```
[[hftbacktest]] is derived from [[nautilus-trader]] design [derivedFrom] [type: forks]
[[nautilus-trader]] depends on [[arrow]] for the parquet catalog [dependentOn] [type: depends]
[[turbovault]] integrates with [[obsidian-vault]] [relatedTo] [type: integrates]
[[deeplob]] cites [[zhang-zohren-roberts-2019]] as the source paper [derivedFrom] [type: cites]
[[neuro-harness]] wraps [[contextforge-gateway]] [partOf] [type: wraps]
```

Use when populating: `ontologies/connections-ontology.md`, `wikis/deep-tool-wiki/<tool>/ontology/connections-ontology.md`, `wikis/deep-agent-wiki/connections/`.

#### `differences` mode

**Question**: When use X versus Y? What contrasts matter for decisions?

**Annotation tag**: `[type: tradeoff|when-to|version|paradigm|cost|latency|accuracy]`

**Preferred relation codes**: `[opposes]`, `[hasAttribute]`, `[isA]`, `[relatedTo]`

**Example**:

```
[[vectorbt]] opposes [[nautilus-trader]] on event-vs-vectorized backtest [opposes] [type: paradigm]
[[vectorbt]] has attribute [[fast-on-large-grids]] [hasAttribute] [type: tradeoff]
[[nautilus-trader]] has attribute [[realistic-fill-latency]] [hasAttribute] [type: tradeoff]
[[xgboost]] opposes [[lightgbm]] on speed-for-large-categoricals [opposes] [type: tradeoff]
[[purged-cv]] is a type of [[time-series-cv]] preferred over [[k-fold]] [isA] [type: when-to]
```

Use when populating: `ontologies/differences-ontology.md`, `wikis/deep-tool-wiki/<tool>/ontology/differences-ontology.md`, `wikis/deep-agent-wiki/differences/`.

#### `constraints` mode

**Question**: What are the limits, anti-patterns, gotchas, deprecated paths?

**Annotation tag**: `[type: limit|antipattern|footgun|deprecated|scale|memory|api-change]`

**Preferred relation codes**: `[opposes]`, `[dependentOn]`, `[hasAttribute]`, `[causes]`

**Example**:

```
[[obsidian-sync-plugin]] opposes [[turbovault-writes]] on the same vault [opposes] [type: antipattern]
[[vectorbt]] depends on [[fitting-in-memory]] for parameter sweeps [dependentOn] [type: scale]
[[arxiv-html-version]] has attribute [[not-available-for-all-papers]] [hasAttribute] [type: limit]
[[mlfinlab-v1]] opposes [[mlfinlab-v0]] on import paths [opposes] [type: api-change]
[[paywalled-papers]] cause [[broken-wikilink-resolution]] without __paywalled stubs [causes] [type: footgun]
```

Use when populating: `ontologies/constraints-ontology.md`, `wikis/deep-tool-wiki/<tool>/ontology/constraints-ontology.md`, `wikis/deep-agent-wiki/constraints/`.

#### `sources` mode

**Question**: Where did this knowledge come from? What's the provenance chain?

**Annotation tag**: `[type: paper|book|blog|repo|standard|talk|email|interview]`

**Preferred relation codes**: `[derivedFrom]`, `[locatedIn]`, `[hasAttribute]`, `[isA]`

**Example**:

```
[[deflated-sharpe-ratio]] is derived from [[bailey-lopez-de-prado-2014]] [derivedFrom] [type: paper]
[[bailey-lopez-de-prado-2014]] is located in [[journal-of-portfolio-management]] [locatedIn] [type: paper]
[[advances-in-financial-machine-learning]] is a [[book]] [isA] [type: book]
[[nautilus-trader-docs]] has attribute [[updated-2026-05]] [hasAttribute] [type: repo]
[[vpin-original-paper]] is derived from [[easley-lopez-de-prado-ohara-2012]] [derivedFrom] [type: paper]
```

Use when populating: `ontologies/sources-ontology.md`, `wikis/deep-tool-wiki/<tool>/ontology/sources-ontology.md`, `wikis/deep-agent-wiki/sources/`.

#### Invocation

Pass the dimension mode as the first argument when invoking the skill, with the input corpus (tool wiki content or agent wiki dimension folder) as the second argument. The `llm-wiki` workflow W7 calls this skill once per dimension; W1 calls it 6 times when populating a new tool wiki (or once per dimension as the tool is built up). The output is always a single Markdown file matching the dimension's name, ready to drop into `ontologies/<dim>-ontology.md` or `wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md`.

Network discipline still applies in dimension modes — no hub-and-spoke. If "the tool" or "the dimension" itself becomes a hub appearing in every paragraph, rebalance toward cross-references between the dimension-tagged entities.

## Entity Generation Principles

Generate comprehensive responses with multiple elements. Explore the full variety of entities belonging to the domain of inquiry. Include various types of:

- Entities
- Classes
- Relationships
- Axioms
- Rules

**Critical**: Avoid hierarchical structures with one central idea. First iteration should be comprehensive, long, and cover the widest possible domain. Generate network structures, not trees.

## Output Format

Each entity uses [[wikilink]] syntax. Relations are described in plain text within the same paragraph. Relation codes appear at paragraph end in [squarebrackets].

### Syntax Pattern

```
[[entity1]] relation description [[entity2]] [relationCode]
```

### Formatting Rules

- Each relation = separate paragraph line
- Minimum 8 paragraphs per relationship type
- Each statement MUST have at least 2 entities in [[wikilinks]]
- Each statement MUST have a [relationCode]

### Example

```
[[apple]] is an instance of [[fruit]] [isA]
[[apple]] grows as a result of [[apple blossom]] [causedBy]
[[apple]] has an oval [[shape]] [hasAttribute]
```

## Relation Codes

Use ONLY these relation codes (unless user provides alternatives):

- `[isA]` - Class membership
- `[partOf]` - Component relationship
- `[hasAttribute]` - Properties and characteristics
- `[relatedTo]` - General associations
- `[dependentOn]` - Dependencies
- `[causes]` - Causal relationships
- `[locatedIn]` - Spatial relationships
- `[occursAt]` - Temporal relationships
- `[derivedFrom]` - Origin and derivation
- `[opposes]` - Contradictory relationships

## Relationship Balance

Ensure relations cover both:

- **Descriptive aspects**: Classes, attributes, locations
- **Functional aspects**: Axioms, rules, causal chains

## Entity Distribution

- Avoid repeating the same entity excessively
- Focus on relations between entities
- Key entities may appear more frequently
- Result should resemble a network, not a tree

## Paragraph Structure Examples

### ❌ AVOID: Tree/Hierarchical Structure

This creates a hub-and-spoke pattern where one central entity dominates:

```
[[machine learning]] is a type of [[artificial intelligence]] [isA]
[[machine learning]] uses [[algorithms]] [relatedTo]
[[machine learning]] requires [[data]] [dependentOn]
[[machine learning]] produces [[predictions]] [causes]
[[machine learning]] has [[accuracy]] as a measure [hasAttribute]
[[machine learning]] is located in [[data science]] field [partOf]
[[machine learning]] occurs at [[training phase]] [occursAt]
[[machine learning]] is derived from [[statistics]] [derivedFrom]
```

**Problem**: "machine learning" appears in every statement, creating a star topology rather than a network.

### ✅ PREFERRED: Network Structure

Distribute entities across multiple interconnected relationships:

```
[[machine learning]] is a type of [[artificial intelligence]] [isA]
[[artificial intelligence]] enables [[automation]] of tasks [causes]
[[algorithms]] process [[training data]] to learn patterns [relatedTo]
[[training data]] must have high [[data quality]] [hasAttribute]
[[data quality]] affects [[model accuracy]] [causes]
[[model accuracy]] is measured during [[validation phase]] [occursAt]
[[validation phase]] comes after [[training phase]] [occursAt]
[[neural networks]] are derived from [[biological neurons]] [derivedFrom]
[[biological neurons]] are part of [[brain architecture]] [partOf]
[[supervised learning]] depends on [[labeled data]] [dependentOn]
[[labeled data]] opposes [[unlabeled data]] in requirements [opposes]
[[deep learning]] is a specialized form of [[neural networks]] [isA]
```

**Benefit**: Multiple entities interconnect, creating a web of relationships rather than radiating from one center.

### Example: Topic-Based Ontology (Climate Change)

Generate 8+ paragraphs per relationship type, distributed across entities:

```
[[climate change]] is caused by [[greenhouse gases]] [causes]
[[greenhouse gases]] include [[carbon dioxide]] as a component [partOf]
[[carbon dioxide]] has increasing [[atmospheric concentration]] [hasAttribute]
[[fossil fuels]] produce [[carbon dioxide]] when burned [causes]

[[global temperature]] is rising as an effect of [[climate change]] [causes]
[[ocean acidification]] is related to [[carbon dioxide]] absorption [relatedTo]
[[ice sheets]] are located in [[polar regions]] [locatedIn]
[[sea level rise]] depends on [[ice sheet melting]] [dependentOn]

[[renewable energy]] opposes [[fossil fuels]] as energy source [opposes]
[[solar power]] is a type of [[renewable energy]] [isA]
[[wind turbines]] generate [[electricity]] from wind [causes]
[[carbon capture]] is derived from [[industrial processes]] [derivedFrom]
```

### Example: Text-Based Extraction

When extracting from user-provided text, identify key entities and their explicit/implicit relationships:

**User text**: "Photosynthesis converts light energy into chemical energy. Chloroplasts contain chlorophyll which absorbs sunlight."

**Ontology output**:
```
[[photosynthesis]] converts [[light energy]] into forms [causes]
[[light energy]] becomes [[chemical energy]] through conversion [derivedFrom]
[[chloroplasts]] are located in [[plant cells]] [locatedIn]
[[chloroplasts]] contain [[chlorophyll]] as component [partOf]
[[chlorophyll]] has [[green color]] as property [hasAttribute]
[[chlorophyll]] absorbs [[sunlight]] for energy [relatedTo]
[[sunlight]] is a form of [[light energy]] [isA]
[[chemical energy]] is stored in [[glucose molecules]] [locatedIn]
```

### Balancing Relationship Types

Ensure each relation code appears 8+ times across different entity pairs:

**[isA] examples**: taxonomic/class relationships
**[partOf] examples**: compositional structures
**[hasAttribute] examples**: descriptive properties
**[causes] examples**: causal chains
**[dependentOn] examples**: prerequisite relationships
**[relatedTo] examples**: general associations
**[locatedIn] examples**: spatial positioning
**[occursAt] examples**: temporal sequencing
**[derivedFrom] examples**: origins and evolution
**[opposes] examples**: contrasts and alternatives

## Handling Follow-up Requests

When asked clarifying questions, provide responses in the same syntax. Only output ontologies developing in the requested direction:

- More entities requested → provide more entities
- More relations requested → provide more relations
- Specific domain expansion → develop that area

## Output Requirements

**Critical output format**:

1. Output ONLY the ontology
2. Use simple code snippet format for easy copying
3. NO explanations before or after
4. NO descriptions of what was done
5. NO metadata or commentary
6. JUST the ontology in specified format

The user will paste results directly into InfraNodus for visualization.

## InfraNodus Tool Handoff

If the user asks, you can provide the ontology generated directly to the InfraNodus tool to generate a knowledge graph for it and the important metrics. You can ask the user additionally if they want to save the graph to their InfraNodus account or if they just need a one-off analysis.

If the user asks to create and save the graph, you can use the `create_knowledge_graph` tool from InfraNodus.

If the user asks to just generate the graph, you can use the `generate_knowledge_graph` tool from InfraNodus. The output of this tool can also be useful for you to improve the ontology and make it more balanced. You can also use the `cognitive_variability` skill for that.

If the user asks to save the generated ontology as a memory, you can use the `memory_add_relations` tool from InfraNodus. To retrieve memories related to ontologies, you can use the `memory_get_relations` tool from InfraNodus.

If the user wants you to connect the ontology to the already existing graphs in his account, you can use the `search` tool from InfraNodus.
