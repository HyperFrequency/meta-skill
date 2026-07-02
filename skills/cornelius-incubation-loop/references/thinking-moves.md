# Thinking Moves Reference

Detailed execution recipes for the six analytical moves rotated by the incubation
loop (one move per topic per run; position = `run_count mod 6`). See SKILL.md Step 3
for the rotation table and research basis. Apply the move selected in Step 3, then
record its **Output** in the thinking file per SKILL.md Step 6.

## ACH Audit (position 0)
- List all current competing hypotheses
- For each piece of KB evidence found: does it support, contradict, or not apply to each hypothesis?
- Build a simple diagnostic matrix (evidence × hypotheses)
- Eliminate any hypothesis that is contradicted by multiple pieces of evidence
- Update confidence scores for surviving hypotheses
- **Output**: Pruned hypothesis list with updated confidence levels

## Bayesian Update (position 1)
- State prior confidence in leading hypothesis (from last run)
- Identify new evidence from KB search
- Explicitly reason: "Given this evidence, should I be more or less confident? By how much?"
- Use rough likelihood ratios (e.g., "this evidence is 3x more likely if H1 is true than if H2 is true")
- Compute and record updated posterior confidence
- **Output**: New confidence scores with explicit reasoning for the change

## Steelman Opposition (position 2)
- State the current leading hypothesis clearly
- Construct the strongest possible argument AGAINST it - not a strawman
- Search KB explicitly for evidence supporting the opposing view
- Assess: does the steelman change the leading hypothesis, or does it survive?
- If the steelman reveals a genuine weakness, revise the hypothesis
- **Output**: Steel-manned opposition + response + any hypothesis revision

## Cross-Domain Bridge (position 3)
- Identify the core mechanism or pattern in the current question
- Run KB search from an unrelated domain (e.g., if topic is about AI, search neuroscience or Buddhism)
- Find analogous patterns or contradictory evidence from that domain
- Extract what the foreign domain implies about the current question
- **Output**: Cross-domain insight + revised framing of the question (if warranted)

## Implication Check (position 4)
- Take the current leading hypothesis as given (temporarily)
- Derive 3-5 concrete, testable implications that should be true if the hypothesis holds
- Search KB and reason about whether those implications are actually supported
- If an implication is clearly false, that is disconfirming evidence for the hypothesis
- **Output**: Implications assessed as supported/unsupported/unknown + impact on hypothesis confidence

## Assumption Audit (position 5)
- List the 3-5 key assumptions the current reasoning rests on
- Rank by: (a) how load-bearing for the conclusion, and (b) how uncertain/shaky
- Focus scrutiny on high load-bearing + high uncertainty assumptions
- For the shakiest assumption: search KB for evidence bearing on it
- **Output**: Assumption vulnerability map + revised conclusion if key assumption weakens
