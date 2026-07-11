# Rules, Alerts, and Chemical-Group Catalog

Criteria, thresholds, literature citations, and selection guidance for the
filters exposed by `medchem`. Thresholds below reflect the commonly published
definitions of each rule; confirm the exact cutoffs a given `medchem` release
uses against https://medchem-docs.datamol.io, since implementations vary slightly.

Single-molecule rules live under `mc.rules.basic_rules.*` and accept either a
SMILES string or an `rdkit.Chem.Mol`, returning a boolean (pass/fail).

---

## Drug-likeness rules

### Rule of Five (Lipinski)
`mc.rules.basic_rules.rule_of_five(mol)` — predicts oral bioavailability.
Lipinski et al., *Adv Drug Deliv Rev* (1997) 23:3-25.

- MW ≤ 500 Da
- cLogP ≤ 5
- H-bond donors ≤ 5
- H-bond acceptors ≤ 10

The most widely used drug-likeness filter; ~90% of orally active drugs comply.
Natural products, antibiotics, and prodrugs are common, legitimate exceptions.

### Rule of Veber
`mc.rules.basic_rules.rule_of_veber(mol)` — complements Ro5 for oral
bioavailability. Veber et al., *J Med Chem* (2002) 45:2615-2623.

- Rotatable bonds ≤ 10
- TPSA ≤ 140 Å²

TPSA tracks cell permeability; rotatable bonds track flexibility.

### Rule of Drug
`mc.rules.basic_rules.rule_of_drug(mol)` — combined pass of Rule of Five **and**
Veber **and** no PAINS substructures.

### REOS (Rapid Elimination Of Swill)
`mc.rules.basic_rules.rule_of_reos(mol)` — removes compounds unlikely to be
drugs. Walters & Murcko, *Adv Drug Deliv Rev* (2002) 54:255-271.

- MW 200-500 Da
- cLogP -5 to 5
- H-bond donors 0-5
- H-bond acceptors 0-10

### Golden Triangle
`mc.rules.basic_rules.golden_triangle(mol)` — balances lipophilicity and MW.
Johnson et al., *J Med Chem* (2009) 52:5487-5500.

- 200 ≤ MW ≤ 50 × cLogP + 400
- cLogP -2 to 5

Defines an optimal region on the MW-vs-cLogP plane (triangular in shape).

---

## Lead-likeness rules

### Rule of Oprea
`mc.rules.basic_rules.rule_of_oprea(mol)` — lead-like compounds for hit-to-lead.
Oprea et al., *J Chem Inf Comput Sci* (2001) 41:1308-1315.

- MW 200-350 Da
- cLogP -2 to 4
- Rotatable bonds ≤ 7
- Rings ≤ 4

Rationale: leads should have "room to grow" during optimization, so keep MW/cLogP
low early.

### Lead-like (soft)
`mc.rules.basic_rules.rule_of_leadlike_soft(mol)` — permissive lead-like band.

- MW 250-450 Da
- cLogP -3 to 4
- Rotatable bonds ≤ 10

### Lead-like (strict)
`mc.rules.basic_rules.rule_of_leadlike_strict(mol)` — restrictive lead-like band.

- MW 200-350 Da
- cLogP -2 to 3.5
- Rotatable bonds ≤ 7
- Rings 1-3

---

## Fragment rules

### Rule of Three
`mc.rules.basic_rules.rule_of_three(mol)` — fragment-based screening libraries.
Congreve et al., *Drug Discov Today* (2003) 8:876-877.

- MW ≤ 300 Da
- cLogP ≤ 3
- H-bond donors ≤ 3
- H-bond acceptors ≤ 3
- Rotatable bonds ≤ 3
- Polar surface area ≤ 60 Å²

Fragments are grown into leads; low complexity gives more viable starting points.

---

## CNS rules

### Rule of CNS
`mc.rules.basic_rules.rule_of_cns(mol)` — central-nervous-system drug-likeness.

- MW ≤ 450 Da
- cLogP -1 to 5
- H-bond donors ≤ 2
- TPSA ≤ 90 Å²

Blood-brain-barrier penetration needs low TPSA and few HBDs; constraints are
tighter than for peripheral targets.

---

## Structural-alert filters

### PAINS (Pan-Assay INterference compoundS)
`mc.rules.basic_rules.pains_filter(mol)` — **returns True when NO PAINS is
found.** Baell & Holloway, *J Med Chem* (2010) 53:2719-2740.

Flags frequent-hitter classes that show apparent activity through non-specific
mechanisms: catechols, quinones, rhodanines, hydroxyphenylhydrazones, alkyl/aryl
aldehydes, and specific Michael-acceptor patterns. Deprioritize in lead
selection; they are common screening false positives.

### Common Alerts
`mc.structural.CommonAlertsFilters()` — general alerts curated from ChEMBL and
the medicinal-chemistry literature. Categories:

1. **Reactive groups** — epoxides, aziridines, acid halides, isocyanates
2. **Metabolic liabilities** — hydrazines, thioureas, certain anilines
3. **Aggregators** — polyaromatic systems, long aliphatic chains
4. **Toxicophores** — nitroaromatics, aromatic N-oxides, certain heterocycles

Per-molecule result reports `has_alerts`, the matched `alert_details`, and
`num_alerts` (see `references/api.md` for shapes).

### NIBR filters
`mc.structural.NIBRFilters()` — Novartis Institutes for BioMedical Research
industrial filter set combining structural alerts with property filters; balances
drug-likeness with practical medicinal chemistry. Returns pass/fail booleans.

### Lilly Demerits
`mc.structural.LillyDemeritsFilters()` — Eli Lilly's demerit system (~275
patterns accumulated over ~18 years). Each matched pattern adds demerits; a
molecule is **rejected above 100 demerits**.

- **High (>50 demerits):** known toxic groups, highly reactive functionalities,
  strong metal chelators
- **Medium (20-50):** metabolic liabilities, aggregation-prone structures,
  frequent hitters
- **Low (5-20):** minor, context-dependent concerns

Because demerits accumulate, several minor patterns can sum past 100 with no
single fatal group — always inspect the matched-pattern list, not just pass/fail.

---

## Chemical-group patterns

`mc.groups.ChemicalGroup(groups=[...])` detects named substructure families;
custom SMARTS can be supplied alongside (see `references/api.md`).

- **hinge_binders** — kinase hinge motifs: aminopyridines, aminopyrimidines,
  indazoles, benzimidazoles. Use in kinase-inhibitor design.
- **phosphate_binders** — basic amines in specific geometries, guanidiniums,
  arginine mimetics. Kinase / phosphatase inhibitors.
- **michael_acceptors** — α,β-unsaturated carbonyls/nitriles, vinyl sulfones,
  acrylamides. Desirable as covalent warheads, but flagged as reactive in screens.
- **reactive_groups** — epoxides, aziridines, acyl halides, isocyanates,
  sulfonyl chlorides.

---

## Recommended filter stacks by stage

### HTS screening (high-throughput, permissive)
```python
rfilter = mc.rules.RuleFilters(rule_list=["rule_of_five", "pains_filter"])
alerts  = mc.structural.CommonAlertsFilters()
```

### Hit-to-lead
```python
rfilter = mc.rules.RuleFilters(rule_list=["rule_of_oprea"])
nibr    = mc.structural.NIBRFilters()
lilly   = mc.structural.LillyDemeritsFilters()
```

### Lead optimization (strict)
```python
rfilter    = mc.rules.RuleFilters(rule_list=["rule_of_drug", "rule_of_leadlike_strict"])
alerts     = mc.structural.CommonAlertsFilters()
complexity = mc.complexity.ComplexityFilter(max_complexity=400)
```

### CNS targets
```python
rfilter     = mc.rules.RuleFilters(rule_list=["rule_of_cns"])
constraints = mc.constraints.Constraints(tpsa_max=90, hbd_max=2, mw_range=(300, 450))
```

### Fragment-based discovery
```python
rfilter    = mc.rules.RuleFilters(rule_list=["rule_of_three"])
complexity = mc.complexity.ComplexityFilter(max_complexity=250)
```

---

## Filters are guidelines, not verdicts

**False positives (good drugs flagged):** ~10% of marketed drugs fail Ro5;
natural products, antibiotics, antivirals, and prodrugs routinely violate
standard rules. **False negatives (bad compounds passing):** passing a filter
does not predict target-specific or in-vivo success.

Context changes the right criteria — target class (kinase vs GPCR vs ion
channel), modality (small molecule vs PROTAC vs molecular glue), route (oral vs
IV vs topical), disease area, and stage all shift the optimal property window.
Modern practice pre-filters with rules, then scores survivors with ML models
rather than treating any single rule as a hard gate.

---

## References

1. Lipinski CA et al. *Adv Drug Deliv Rev* (1997) 23:3-25
2. Veber DF et al. *J Med Chem* (2002) 45:2615-2623
3. Oprea TI et al. *J Chem Inf Comput Sci* (2001) 41:1308-1315
4. Congreve M et al. *Drug Discov Today* (2003) 8:876-877
5. Baell JB & Holloway GA. *J Med Chem* (2010) 53:2719-2740
6. Johnson TW et al. *J Med Chem* (2009) 52:5487-5500
7. Walters WP & Murcko MA. *Adv Drug Deliv Rev* (2002) 54:255-271
8. Hann MM & Oprea TI. *Curr Opin Chem Biol* (2004) 8:255-263
