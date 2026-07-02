# Research Discipline & Quality Standards

Principles to enforce continuously across the whole run — not tied to any specific phase.

## Discipline

- **Lock before you run**: Commit your experiment protocol to git before executing. Never combine protocol + results in one commit. The git history is your lightweight pre-registration.
- **Confirmatory vs exploratory**: Results matching your locked protocol are confirmatory. Everything else is exploratory — interesting but requiring more skepticism.
- **Negative results are progress**: A refuted hypothesis tells you something. Log what it rules out and what it suggests.
- **Sanity check before analysis**: Verify training converged, baselines reproduce, and data is correct before trusting your primary metric.
- **Return to literature when confused**: Don't guess — search (Exa for discovery, Semantic Scholar for ML/AI lookup, arXiv for preprints).
- **Never stop**: Don't wait for human approval on routine decisions. Find the best path forward autonomously.
- **Use whatever compute is available**: Adapt to the environment — local GPU, cluster, cloud, or just CPU. If no GPU, scale experiments down. Don't block on compute.

## Quality Standards

**Good**: hypotheses have mechanistic reasoning ("X because Y, predicting Z"), not just "try X"; findings.md builds a coherent narrative; negative results are recorded with what they rule out; the agent updates its model when experiments contradict expectations; progress reports tell a research story with compelling visualizations.

**Bad**: pure hyperparameter sweeps without interpretation; findings.md is just experiment logs copy-pasted; agent never revisits assumptions after failures; optimizing metrics without understanding why changes work.
