# Common Issues

Troubleshooting for autonomous research runs.

**Inner loop stalls (no metric improvement)**
Run an outer loop. Is the metric the right one? Is the search space exhausted? Consider broadening or pivoting. Search literature for new approaches.

**Stuck and not making progress**
Don't keep trying random changes. Step back: search literature for related work, invoke `21-research-ideation/` brainstorming skills, or run an outer loop reflection. Being stuck means you need new information or a new perspective, not more experiments.

**Results contradict baseline expectations**
Investigate, don't ignore. Return to literature — your protocol might have an error, the published baseline may be wrong, or conditions differ. Update findings.md with what you learn.

**Agent loses context between ticks**
Ensure research-state.yaml and findings.md are updated after every action. These files are your memory across sessions.

**Can't find relevant papers**
Try multiple approaches in order: Exa MCP for broad search, Semantic Scholar for specific ML/AI paper lookup (`pip install semanticscholar`), arXiv for preprints (`pip install arxiv`). See the `20-ml-paper-writing` skill's citation workflow reference for complete API code. Note: Google Scholar has no official API — use Semantic Scholar instead for programmatic search.

**No GPU available**
Use CPU and scale experiments down. Many research tasks (analysis, interpretability, small model training) run fine on CPU. Adjust experiment design to fit available compute rather than blocking.

**Experiments take longer than /loop interval**
Normal. On the next tick, check if it finished. If not, keep waiting or do something else useful (update notes, search papers). Adjust interval if needed.

**Not sure when to conclude**
Three questions: Do you have a strongly supported finding? Can you explain WHY it works? Would findings.md make a convincing paper abstract? If yes to all: conclude.
