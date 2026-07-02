# Research Loops: Bootstrap, Inner, Outer

The detailed mechanics of the two-loop research engine. SKILL.md has the overview; this file has the step-by-step procedures, criteria, and supporting detail.

## Workspace Structure

Create this structure at the project root:

```
{project}/
├── research-state.yaml       # Central state tracking
├── research-log.md           # Decision timeline
├── findings.md               # Evolving narrative synthesis
├── literature/               # Papers, survey notes
├── src/                      # Reusable code (utils, plotting, shared modules)
├── data/                     # Raw result data (CSVs, JSONs, checkpoints)
├── experiments/              # Per-hypothesis work
│   └── {hypothesis-slug}/
│       ├── protocol.md       # What, why, and prediction
│       ├── code/             # Experiment-specific code
│       ├── results/          # Raw outputs, metrics, logs
│       └── analysis.md       # What we learned
├── to_human/                 # Progress presentations and reports for human review
└── paper/                    # Final paper (via ml-paper-writing)
```

- **`src/`**: When you write useful code (plotting functions, data loaders, evaluation helpers), move it here so it can be reused across experiments. Don't duplicate code in every experiment directory.
- **`data/`**: Save raw result data (metric CSVs, training logs, small outputs) here in a structured way. After a long research horizon, you'll need this to replot, reanalyze, and write up the paper. Name files descriptively (e.g., `trajectory_H1_runs001-010.csv`). Large files like model checkpoints go to a separate storage path (e.g., `/data/`, cloud storage) — not in the project directory.

Initialize `research-state.yaml`, `research-log.md`, and `findings.md` from `templates/`. Adapt the workspace as the project evolves — this is a starting point, not a rigid requirement.

## Research is Non-Linear

The two-loop structure is a rhythm, not a railroad. At any point you can and should:

- **Return to literature** when results surprise you, assumptions break, or you need context for a new direction — always save what you find to `literature/`
- **Brainstorm new ideas** using `21-research-ideation/` skills when stuck or when results open unexpected questions
- **Pivot the question entirely** if experiments reveal the original question was wrong or less interesting than what you found

Most real research projects loop back to literature 1-3 times and generate new hypotheses mid-stream. Don't treat bootstrap as the only time you read papers or brainstorm.

## Bootstrap: Literature and Hypotheses

Before entering the loops, understand the landscape. Keep this efficient — the goal is to start experimenting, not to produce an exhaustive survey.

1. **Search literature** for the research question. Use multiple sources — never stop at one:
   - **Exa MCP** (`web_search_exa`) if available — best for broad discovery and finding relevant papers quickly
   - **Semantic Scholar** (`pip install semanticscholar`) — best for ML/AI papers, citation graphs, and specific paper lookup. See the `20-ml-paper-writing` skill's citation workflow reference for complete API code examples
   - **arXiv** (`pip install arxiv`) — best for recent preprints and open-access papers
   - **CrossRef** — best for DOI lookup and BibTeX retrieval
   - Keep searching until you have good coverage. If one source comes up empty, try another with different keywords

   **Save everything to `literature/`**: For every paper, save a summary — title, authors, year, key findings, relevance, and the URL/DOI. One file per paper plus a running `literature/survey.md`. This is your reference library throughout the project.

2. **Identify gaps** from the literature
   - What's been tried? What hasn't? Where do existing methods break?
   - What do Discussion sections flag as future work?

3. **Form initial hypotheses** — invoke `21-research-ideation/` skills
   - `brainstorming-research-ideas` for structured diverge-converge workflow
   - `creative-thinking-for-research` for deeper cognitive frameworks
   - Each hypothesis must be testable with a clear prediction

4. **Define the evaluation**
   - Set the proxy metric and baseline before running experiments
   - The metric should be computable quickly (minutes, not hours)
   - Lock evaluation criteria upfront to prevent unconscious metric gaming

5. **Record** in research-state.yaml, log the bootstrap in research-log.md

## The Inner Loop

Rapid iteration with clear measurable outcomes. Two flavors:

- **Optimization**: make a metric go up/down (val_loss, accuracy, throughput). Think Karpathy's autoresearch.
- **Discovery**: test mechanistic hypotheses about why something works. The metric is a measurement (does grokking happen faster? does entropy increase before forgetting?), not just a target to optimize.

```
1.  Pick the highest-priority untested hypothesis
2.  Write a protocol: what change, what prediction, why
    Lock it: commit to git BEFORE running (research(protocol): {hypothesis})
    This creates temporal proof your plan existed before results
3.  Run the experiment (invoke the relevant domain skill)
4.  Sanity check before trusting results:
    - Did training converge? No NaN/Inf?
    - Does baseline reproduce expected performance?
    - Data loading correct? (spot-check a few samples)
5.  Measure the proxy metric
6.  Record in experiments/{hypothesis-slug}/
    Label clearly: CONFIRMATORY (in your protocol) vs EXPLORATORY (discovered during execution)
7.  If positive: keep, note WHY it worked
8.  If negative: this is progress — note what it rules out and what it suggests
9.  Update research-state.yaml
10. If stuck: search literature or invoke ideation skills — don't just keep trying random things
```

**Never stop.** Even if something fails, find a path forward. Debug, adjust, simplify, or pivot — but keep the research moving. The `/loop` and heartbeat mechanisms keep you going; use that momentum.

### Track the Experiment Trajectory

Maintain a running record of measurable outcomes across experiments:

```json
{
  "experiment_id": "run_014",
  "hypothesis": "H3",
  "metric_value": 0.847,
  "baseline": 0.812,
  "delta": "+0.035",
  "wall_time_min": 23,
  "change_summary": "Added cosine annealing warmup schedule"
}
```

This trajectory produces the optimization plot (like Karpathy's progress chart) — include it in progress reports. Humans love seeing the upward curve.

## The Outer Loop

Step back from individual experiments. Synthesize.

```
1. Review all results since last reflection
2. Cluster by type: what kinds of changes worked? Which didn't?
3. Ask WHY — identify the mechanism behind successes and failures
4. Update findings.md with current understanding
5. Search literature if results were surprising or assumptions need revisiting
6. Generate new hypotheses if warranted (invoke 21-research-ideation/ skills)
7. Decide direction (see criteria below)
8. Update research-state.yaml with new direction
9. Log the reflection in research-log.md
10. If there's something meaningful, generate a progress presentation
```

### Deciding Direction

Don't just pick randomly — use these criteria:

**DEEPEN** — a supported result raises follow-up questions
- Does the effect hold under different conditions? What's the mechanism?
- Action: generate sub-hypotheses (H1.1, H1.2) → back to inner loop

**BROADEN** — current results are solid, but adjacent questions are untested
- New questions emerged. The current contribution is clear but more is possible.
- Action: generate new root hypotheses → back to inner loop

**PIVOT** — results invalidate key assumptions or something more interesting appeared
- A core assumption was wrong, or an unexpected finding is more promising than the original question.
- Action: return to literature with new questions → re-bootstrap

**CONCLUDE** — sufficient evidence for a contribution
- At least one hypothesis is strongly supported (or a coherent set of negative results)
- Key ablations completed, error analysis done
- findings.md reads like a paper backbone — a human could write the abstract from it
- No critical open questions that would change the story

Note: coherent negative results are a valid contribution. "X does NOT work because Y" is publishable if the reasoning is rigorous.

### findings.md Is Your Project Memory

This file serves two purposes: it's the research narrative for humans AND your accumulated knowledge base as an agent. Read it at the start of every session, /loop tick, or heartbeat to remember what you've learned.

After every outer loop, update it to answer:

- What do we know so far? (Current Understanding)
- What patterns explain our results? (Patterns and Insights)
- What specific things did we learn not to repeat? (Lessons and Constraints)
- What remains open? (Open Questions)

The "Lessons and Constraints" section is especially important — it captures specific actionable learnings like "weight decay > 0.1 diverges at this scale" or "baseline only reproduces with batch_size=64." This prevents repeating failed approaches across sessions.

**Quality test**: After 30 inner loop experiments, a human should be able to read findings.md and write a paper abstract from it. If they can't, the outer loop isn't synthesizing — it's just logging.
