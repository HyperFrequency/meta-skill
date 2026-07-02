---
name: cornelius-incubation-loop
version: 0.1.0
description: Autonomous iterative thinking loop - processes active thinking-registry topics using rotating analytical moves (ACH, Bayesian updating, steelmanning, cross-domain bridging, implication/assumption audits) and persists reasoning state across scheduled runs until convergence. Use WHEN you have open questions needing slow, multi-cycle refinement against a knowledge base and want depth to accumulate across daily runs without a human in each loop; also use to seed a new thinking topic or check convergence status. Do NOT use for one-off fact lookups, time-critical decisions with a deadline, single-pass analysis (use cornelius-dialectic or cornelius-deep-research instead), or crystallizing a converged topic into a permanent note (that is the manual cornelius-synthesize-insights step).
automation: autonomous
schedule: "0 7 * * *"
allowed-tools: Read, Write, Grep, Glob, Bash
user-invocable: true
argument-hint: "[topic-slug] (optional - processes all active topics if omitted)"
---

# Incubation Loop

Autonomous thinking engine. Each scheduled run advances all active thinking topics by one analytical move, persisting reasoning state across runs until convergence.

## Purpose

Continuous intellectual iteration on open questions. Uses a rotating set of research-validated analytical moves (ACH, Bayesian updating, dialectical steelmanning, cross-domain bridging) to build toward well-grounded conclusions - without requiring human presence in each cycle.

**Design principle:** Each run does one move per topic. Depth accumulates across runs. No single run tries to "solve" the question.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Thinking Registry | `Brain/05-Meta/Thinking/THINKING-REGISTRY.md` | ✓ | ✓ | Active topics + status |
| Thinking Files | `Brain/05-Meta/Thinking/[topic-slug].md` | ✓ | ✓ | Per-topic reasoning journal |
| Local Brain Search | `resources/local-brain-search/` | ✓ | | Semantic search for KB evidence |
| Permanent Notes | `Brain/02-Permanent/` | ✓ | | Primary evidence source |
| Session Changelogs | `Brain/05-Meta/Changelogs/` | | ✓ | Run log |

## Prerequisites

- Registry file exists at `Brain/05-Meta/Thinking/THINKING-REGISTRY.md`
- At least one active topic seeded (see Seeding section below)
- Local Brain Search index up-to-date

---

## Process

### Step 1: Get Date and Load Registry

```bash
date '+%Y-%m-%d'
```

Read `Brain/05-Meta/Thinking/THINKING-REGISTRY.md`. Parse all topics with `status: active`.

If registry does not exist, create it:

```markdown
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
created_by: claude-sonnet-4-6
updated_by: claude-sonnet-4-6
agent_version: 01.25
---

# Thinking Registry

Active questions under continuous analysis.

| Topic Slug | Central Question | Status | Runs | Last Run |
|------------|-----------------|--------|------|----------|
```

If no active topics found, log to changelog and exit cleanly.

### Step 2: For Each Active Topic - Load State

Read `Brain/05-Meta/Thinking/[topic-slug].md`.

Parse:
- `run_count` - how many iterations completed
- `move_sequence` - which moves have been applied (determines next move)
- `current_hypotheses` - list with confidence scores
- `status` - active / converged / crystallized
- Last run's conclusions

### Step 3: Determine Next Thinking Move

Rotate through this sequence. Position = `run_count mod 6`:

| Position | Move | Research Basis |
|----------|------|----------------|
| 0 | **ACH Audit** | Heuer (CIA) - Analysis of Competing Hypotheses |
| 1 | **Bayesian Update** | Information theory - explicit confidence tracking |
| 2 | **Steelman Opposition** | Socratic dialectic - steel-man the opposite |
| 3 | **Cross-Domain Bridge** | Consilience method - what does an unrelated field say? |
| 4 | **Implication Check** | Falsificationism (Popper) - if true, what follows? Is that true? |
| 5 | **Assumption Audit** | Intelligence SAT - which premises are load-bearing and shakiest? |

### Step 4: Run KB Search for Evidence

Use Local Brain Search to find relevant notes:

```bash
cd "$(git rev-parse --show-toplevel)"
python3 resources/local-brain-search/search.py "[central question]" --limit 8 --mode spreading 2>/dev/null
python3 resources/local-brain-search/search.py "[leading hypothesis]" --limit 5 --mode spreading 2>/dev/null
```

Read the top 3-4 most relevant notes in full. These are the evidence base for this iteration.

### Step 5: Apply the Thinking Move

Execute the single move selected in Step 3. Each move has a step-by-step recipe and a
defined **Output** in [`references/thinking-moves.md`](references/thinking-moves.md):
ACH Audit, Bayesian Update, Steelman Opposition, Cross-Domain Bridge, Implication
Check, Assumption Audit. Ground the move in the KB evidence from Step 4; do not
apply more than one move per topic per run.

### Step 6: Write Updated Thinking File

Append to `Brain/05-Meta/Thinking/[topic-slug].md`:

```markdown
### Run [N]: [Move Name] - [YYYY-MM-DD]

**KB Evidence Consulted:**
- [[Note A]] - [one line on relevance]
- [[Note B]] - [one line on relevance]

**Analysis:**
[2-4 paragraphs of actual reasoning from the move]

**Updated Hypotheses:**
| Hypothesis | Confidence | Change |
|-----------|------------|--------|
| H1: [statement] | X% | ↑/↓/→ from Y% |
| H2: [statement] | X% | ↑/↓/→ from Y% |

**Current Best Answer:** [1-2 sentences - the leading position after this run]

**Open Questions for Next Run:** [What remains unresolved or most worth probing]
```

Update the frontmatter: `updated`, `updated_by`, `run_count`, `last_run`.

### Step 7: Check Convergence

A topic has converged when ALL of:
- `run_count >= 4` (minimum 4 cycles)
- Same hypothesis has led for 3+ consecutive runs
- Confidence delta between last two runs < 5 percentage points
- No major open questions flagged in last run

If converged:
- Set `status: converged` in the thinking file frontmatter
- Add note: `**CONVERGED** - Ready for crystallization via /synthesize-insights`
- Update registry status to `converged`

If not converged: continue to next topic.

### Step 8: Update Registry

Update `Brain/05-Meta/Thinking/THINKING-REGISTRY.md`:
- Increment run count for each processed topic
- Update last_run date
- Update status (active → converged where applicable)

### Step 9: Write Session Changelog

Write to `Brain/05-Meta/Changelogs/CHANGELOG - Incubation Loop YYYY-MM-DD.md`:

```markdown
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
created_by: claude-sonnet-4-6
updated_by: claude-sonnet-4-6
agent_version: 01.25
---

# Incubation Loop Session: YYYY-MM-DD

## Topics Processed

| Topic | Move Applied | Confidence Shift | Status |
|-------|-------------|-----------------|--------|
| [slug] | [move name] | [leading H]: Y% → Z% | active/converged |

## Notable Shifts
[Any hypothesis revisions, convergences, or surprising KB evidence]

## Converged Topics (Ready for Crystallization)
[List any topics that reached convergence this run]
```

---

## Seeding a New Topic

To add a topic to the loop, create `Brain/05-Meta/Thinking/[topic-slug].md`:

```markdown
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
created_by: claude-sonnet-4-6
updated_by: claude-sonnet-4-6
agent_version: 01.25
topic: "[exact question being analyzed]"
run_count: 0
last_run: null
status: active
---

# Thinking: [Topic Title]

## Central Question
[The exact question. Precise framing matters - ambiguous questions stay ambiguous.]

## Why This Question Matters
[1-2 sentences on stakes or relevance]

## Initial Hypotheses
| Hypothesis | Initial Confidence | Basis |
|-----------|-------------------|-------|
| H1: [statement] | X% | [prior knowledge or intuition] |
| H2: [statement] | X% | [prior knowledge or intuition] |

## Known Evidence (Pre-Run)
[Any notes or sources already known to be relevant]

## Constraints and Assumptions
[What are you taking as given? What's out of scope?]

---
*[Analytical runs will be appended below by the incubation loop]*
```

Then add to `THINKING-REGISTRY.md`:
```
| [topic-slug] | [central question] | active | 0 | null |
```

---

## Crystallization (Manual)

When a topic reaches `status: converged`, the human should:

1. Read the full thinking file
2. Run `/synthesize-insights [topic-slug]` to graduate conclusions to a permanent note
3. Archive thinking file: set `status: crystallized`
4. The permanent note becomes part of the KB for future searches

**Do not automate crystallization** - judgment calls about what conclusions deserve permanence belong to the human.

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Registry missing | Create empty registry, log, exit cleanly |
| No active topics | Log to changelog, exit cleanly |
| KB search returns empty | Try alternate search terms from hypothesis text; if still empty, note in run log and skip KB-grounding for this move |
| Thinking file missing for active topic | Log warning in registry, skip topic |
| Run exceeds 45 minutes | Process topics in order; skip remaining, log which were skipped |

---

## Completion Checklist

- [ ] Registry read - active topics identified
- [ ] Each active topic: KB searched with relevant queries
- [ ] Each active topic: correct move in rotation applied
- [ ] Each active topic: thinking file updated with reasoning + confidence scores
- [ ] Convergence checked for each topic
- [ ] Registry updated (run counts, dates, status changes)
- [ ] Session changelog written to `Brain/05-Meta/Changelogs/`

---

## Self-Improvement

After completing this skill's primary task, consider tactical improvements:

- [ ] **Review execution**: Were there friction points, unclear steps, or inefficiencies?
- [ ] **Identify improvements**: Could the thinking moves, convergence criteria, or file structure be sharper?
- [ ] **Scope check**: Only execution changes - NOT changes to the ACH/Bayesian/dialectic framework itself
- [ ] **Apply improvement** (if identified):
  - [ ] Edit this SKILL.md with the specific improvement
  - [ ] Keep changes minimal and focused
- [ ] **Version control**:
  - [ ] `git add .claude/skills/cornelius-incubation-loop/SKILL.md`
  - [ ] `git commit -m "refactor(incubation-loop): <brief improvement>"`
