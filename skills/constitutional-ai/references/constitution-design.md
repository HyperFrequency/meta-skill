# Constitution Design

The "constitution" is the set of natural-language principles the model uses to
critique, revise, and rank its own outputs. Quality of the constitution is the
single biggest lever on CAI outcomes.

## Principle selection

- Keep principles short, behavioral, and non-overlapping. Each should be testable
  against a single response ("does this avoid toxicity?") rather than abstract.
- Order matters when many principles apply; put the most important
  (helpful/honest/harmless tradeoff) first since later principles are weighted
  less reliably by the critique model.
- 4-16 principles is typical. Too few under-specifies behavior; too many dilutes
  the critique signal and increases contradiction.
- Anthropic's published constitution draws principles from sources like the UN
  Declaration of Human Rights and platform trust-and-safety guidelines, plus
  Anthropic-authored principles. See the paper (arXiv:2212.08073) for the list.

## Helpfulness vs harmlessness tradeoff

- A harmlessness-only constitution produces evasive refusals. Always pair
  harmlessness principles with an explicit "engage and explain rather than
  refuse" principle.
- The SL phase tends to over-correct toward refusal; the RL (RLAIF) phase, with
  helpfulness preferences mixed in, restores the balance. Sample preference
  prompts from BOTH helpfulness and harmlessness distributions.

## Domain-specific constitutions

- For a specialized deployment (medical, legal, finance), add domain principles
  on top of the general harmlessness set rather than replacing it — e.g.
  "do not give individualized investment advice; explain general concepts."
- Randomly sample a single principle (or small subset) per critique step rather
  than always concatenating all of them; this improves coverage and reduces the
  model anchoring on the first principle only.
