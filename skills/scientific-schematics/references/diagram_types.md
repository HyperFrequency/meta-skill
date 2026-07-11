# Scientific Diagram Types

Catalog of the diagram types this skill generates well, with the prompt elements that
matter most for each. Use this to decide what to ask Nano Banana 2 for and which details
to include. For full worked commands see [ai_generation.md](ai_generation.md).

## Neural network architectures
Transformers, CNNs, RNNs, autoencoders, GANs.
Include: layer types and order, dimensions/node counts, flow direction (usually L→R or
bottom→top), attention/skip connections (dashed vs. solid), and a color split between
sub-stacks (e.g., encoder vs. decoder).

## Methodology / study-design flowcharts
CONSORT (RCT participant flow), PRISMA (systematic-review screening), processing pipelines.
Include: each stage box text, exact counts (n=) at every node, branch points, and a color
convention (e.g., process vs. exclusion vs. final analysis).

## Biological pathways
Signaling cascades, metabolic pathways, gene-regulatory networks.
Include: molecule/protein names in order, edge semantics (activation, inhibition,
phosphorylation), compartment boundaries (membrane, nucleus), and node shapes per molecule class.

## Circuit and electrical schematics
Analog/digital circuits, block-level electronics.
Include: components with values (1kΩ, 10µF, 5V), connection topology, and standard
engineering notation. Note: for strict schematic correctness, hand-drawn tools
(e.g., Schemdraw) may beat AI generation — verify component connectivity manually.

## System / software architectures
Block diagrams, data-flow diagrams, deployment topologies, IoT stacks.
Include: layers/tiers, component boxes, directional data-flow arrows, and protocol labels
on connections (I2C, UART, HTTP/S, gRPC).

## Conceptual frameworks and theoretical models
Hierarchies, taxonomies, relationship/entity diagrams, mind-map style frameworks.
Include: grouping, nesting/containment, and labeled relationships between concepts.

## When another approach fits better
- Pure data plots (line/bar/scatter, heatmaps, statistical figures) → use
  **scientific-visualization** (matplotlib/seaborn), not AI image generation.
- Precise, editable vector schematics that must be exact (CAD-like, strict circuits) →
  code-drawn tools (Schemdraw, NetworkX, TikZ).
- Mermaid/PlantUML text-defined diagrams → use a mermaid-focused skill.
