---
name: incubation-loop
description: Autonomous iterative thinking loop - processes active topics using rotating analytical moves (ACH, Bayesian updating, steelmanning, cross-domain bridging, implication checks) and persists reasoning state across scheduled runs
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

Execute the move based on what was determined in Step 3. For each move:

#### ACH Audit
- List all current competing hypotheses
- For each piece of KB evidence found: does it support, contradict, or not apply to each hypothesis?
- Build a simple diagnostic matrix (evidence × hypotheses)
- Eliminate any hypothesis that is contradicted by multiple pieces of evidence
- Update confidence scores for surviving hypotheses
- **Output**: Pruned hypothesis list with updated confidence levels

#### Bayesian Update
- State prior confidence in leading hypothesis (from last run)
- Identify new evidence from KB search
- Explicitly reason: "Given this evidence, should I be more or less confident? By how much?"
- Use rough likelihood ratios (e.g., "this evidence is 3x more likely if H1 is true than if H2 is true")
- Compute and record updated posterior confidence
- **Output**: New confidence scores with explicit reasoning for the change

#### Steelman Opposition
- State the current leading hypothesis clearly
- Construct the strongest possible argument AGAINST it - not a strawman
- Search KB explicitly for evidence supporting the opposing view
- Assess: does the steelman change the leading hypothesis, or does it survive?
- If the steelman reveals a genuine weakness, revise the hypothesis
- **Output**: Steel-manned opposition + response + any hypothesis revision

#### Cross-Domain Bridge
- Identify the core mechanism or pattern in the current question
- Run KB search from an unrelated domain (e.g., if topic is about AI, search neuroscience or Buddhism)
- Find analogous patterns or contradictory evidence from that domain
- Extract what the foreign domain implies about the current question
- **Output**: Cross-domain insight + revised framing of the question (if warranted)

#### Implication Check
- Take the current leading hypothesis as given (temporarily)
- Derive 3-5 concrete, testable implications that should be true if the hypothesis holds
- Search KB and reason about whether those implications are actually supported
- If an implication is clearly false, that is disconfirming evidence for the hypothesis
- **Output**: Implications assessed as supported/unsupported/unknown + impact on hypothesis confidence

#### Assumption Audit
- List the 3-5 key assumptions the current reasoning rests on
- Rank by: (a) how load-bearing for the conclusion, and (b) how uncertain/shaky
- Focus scrutiny on high load-bearing + high uncertainty assumptions
- For the shakiest assumption: search KB for evidence bearing on it
- **Output**: Assumption vulnerability map + revised conclusion if key assumption weakens

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
  - [ ] `git add .claude/skills/incubation-loop/SKILL.md`
  - [ ] `git commit -m "refactor(incubation-loop): <brief improvement>"`
