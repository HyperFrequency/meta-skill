# Reasoning Workflow

The point of this skill is not the SMARTS matcher — it is the **chain-of-thought
layer** that turns a matched substructure into an actionable, falsifiable
rationale. This file describes the method, an LLM prompt template that consumes
the structured report, and how to wire the whole thing into a lead-optimization
loop.

## The cause -> mechanism -> fix chain

For every liability, force the explanation through three linked steps:

1. **Structural cause** — the *specific* substructure responsible, named
   concretely (e.g. "basic piperazine, pKa ~8.5"), not the endpoint restated.
2. **Biological mechanism** — the physical/biochemical pathway from that
   substructure to the phenotype (e.g. "protonated amine engages the hERG inner
   vestibule via cation-pi"). This is the falsifiable claim.
3. **Structural fix** — a concrete transformation that neutralizes *that
   mechanism* while preserving the pharmacophore (e.g. "piperazine → morpholine:
   keep the H-bond acceptor, drop the basicity").

If any step is vague, the rationale is not usable. "It's toxic because it's
lipophilic" fails step 1 (no substructure) and step 2 (no mechanism). The
catalogue in `structural-alerts.md` pre-writes steps 1–3 for each pattern; the
LLM's job is to select the relevant ones, weigh them against the physchem
liabilities, and resolve conflicts (a fix that helps hERG but worsens
solubility).

## Method basis (CoTox, DrugR)

Two results motivate this design; treat the headline numbers as reported by the
source works rather than independently reproduced here:

- **CoTox** (Park et al., 2025) — chain-of-thought toxicity prediction that
  grounds each call in structural and biological context. The reported takeaway:
  reasoning that names the mechanism substantially outperforms a bare-label
  classifier on toxicity endpoints.
- **DrugR** (Liu et al., 2026) — makes liability reasoning *explicit before*
  proposing an optimization, rather than optimizing a black-box score directly.
  Reported takeaway: reasoning-first optimization finds much better molecules per
  step than blind score-chasing.

The shared lesson this skill operationalizes: **surface the mechanism, then
act.** A model that must state *why* before it edits makes fewer superstitious
changes.

## LLM prompt template

Feed the structured report (from `reference-implementation.md`) into a reasoning
model:

```
You are a medicinal chemist reviewing an ADMET liability report.

Molecule (canonical SMILES): {smiles}
Overall assessment: {assessment}

Physicochemical violations:
{for each: property = value, violation, severity}

Structural alerts:
{for each: endpoint | structural_cause | mechanism | suggested_fix}

Task:
1. Rank the liabilities by how likely they are to sink this molecule.
   Weight a single high-severity genotox/cardiotox alert above several
   low-severity physchem violations.
2. For the top 2-3, confirm or challenge the stated mechanism using the actual
   molecular context (is the flagged group shielded, deactivated, or truly
   exposed?). Note any false positives.
3. Propose one concrete analogue that addresses the top liability WITHOUT
   introducing a new one. Give the modified SMILES and state which mechanism it
   neutralizes and what it preserves.
```

Always keep step 2 — the model must be allowed (and required) to overrule the
catalogue when the molecular context contradicts it. The alerts are high-recall
heuristics; the reasoning step is where precision is recovered.

## Integration with lead optimization

Use this skill as the **critic** in an optimization loop; delegate the generator
to `molecular-optimization`:

```
1. admet-prediction    -> raw scores / probabilities
2. admet-reasoning      -> liability report (this skill)
3. LLM reasoning         -> ranked liabilities + one proposed analogue
4. molecular-optimization-> generate/enumerate analogues around that proposal
5. admet-prediction     -> re-score
6. admet-reasoning      -> did the target liability actually clear? new ones?
   repeat until CLEAN or budget exhausted
```

The re-check in step 6 is essential: a "fix" that lowers the hERG score but
introduces an aromatic amine has traded a cardiotox flag for a genotox flag. Only
the reasoning pass catches that substitution, because the raw score for the
*original* endpoint improved.

## Verifying a proposed fix

Before accepting an analogue, confirm the edit removed the specific alert and did
not add another:

```python
before = generate_report(parent_smiles)
after  = generate_report(analogue_smiles)

cleared = {a["structural_cause"] for a in before["structural_alerts"]} \
        - {a["structural_cause"] for a in after["structural_alerts"]}
introduced = {a["structural_cause"] for a in after["structural_alerts"]} \
           - {a["structural_cause"] for a in before["structural_alerts"]}
```

A good fix has a non-empty `cleared` and an empty `introduced`, and does not push
a physchem property out of range (check `after["threshold_liabilities"]`).
