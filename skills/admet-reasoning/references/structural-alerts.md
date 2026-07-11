# Structural Alert Catalogue

Each alert is a SMARTS pattern annotated with the ADMET endpoint it flags, the
structural cause, the biological mechanism, and a suggested remediation. Matching
is a plain RDKit substructure search:

```python
from rdkit import Chem
pattern = Chem.MolFromSmarts("[NX3;H1]1CCNCC1")   # compile once
mol.HasSubstructMatch(pattern)                     # boolean
mol.GetSubstructMatches(pattern)                   # tuple of atom-index tuples
```

The catalogue is intentionally small and **mechanism-annotated** — it is not a
comprehensive screening ruleset. For exhaustive PAINS/BRENK/NIH filtering use the
`medchem` sibling skill. Every hit is a hypothesis, not a verdict; read the
false-positive notes at the bottom before acting on a report.

## hERG (cardiotoxicity)

The hERG (Kv11.1) potassium channel is blocked by many drugs, causing QT
prolongation. The canonical pharmacophore is a **basic (protonatable) nitrogen**
plus lipophilic aromatic bulk; the protonated amine engages the channel inner
vestibule through cation-pi and hydrophobic contacts.

| SMARTS | Structural cause | Mechanism | Suggested fix |
|--------|------------------|-----------|---------------|
| `[NX3;H1]1CCNCC1` | Basic piperazine (pKa ~8.5) | Protonated amine binds the hERG inner vestibule via cation-pi | Replace piperazine with morpholine — keeps an H-bond acceptor while dropping basicity |
| `[NX3;H1]1CCCCC1` | Basic piperidine | Lipophilic basic amine is a classic hERG pharmacophore | Reduce basicity: N-acylation, swap to tetrahydropyran, or add a polar substituent |
| `[nH]1cccc1` | Electron-rich 5-membered N-heteroaromatic (pyrrole) | Electron-rich heteroaromatics can contact hERG aromatic residues | N-methylation or ring expansion |

## DILI (drug-induced liver injury / hepatotoxicity)

Most idiosyncratic hepatotoxicity is driven by **reactive-metabolite formation**
— CYP-mediated oxidation to electrophiles that deplete glutathione and haptenize
proteins.

| SMARTS | Structural cause | Mechanism | Suggested fix |
|--------|------------------|-----------|---------------|
| `[N+](=O)[O-]` | Nitro group | Nitroreduction to nitroso and hydroxylamine metabolites drives oxidative stress | Replace nitro with cyano, trifluoromethyl, or methylsulfonyl |
| `c1ccc2c(c1)ccc1ccccc12` | Anthracene / extended PAH | CYP oxidation to reactive epoxides damages hepatocytes | Break into monocyclic systems or add polar substituents to block metabolic sites |
| `O=c1cc[nH]c(=O)c1` | Pyrimidinedione / uracil-type dione (BROAD — see caveat) | Proposed CYP bioactivation to reactive epoxide intermediates | Bioisosteric replacement of the dione motif |

## CYP inhibition

Reversible CYP450 inhibition raises DDI risk. Two common motifs: **azole nitrogen
coordinating the heme iron**, and **flat lipophilic systems** that fit CYP3A4's
hydrophobic channel.

| SMARTS | Structural cause | Mechanism | Suggested fix |
|--------|------------------|-----------|---------------|
| `c1cnc[nH]1` | Unsubstituted imidazole (heme-coordinating azole) | Azole N lone pair coordinates the CYP heme Fe, blocking the active site | N-methylation, or swap to a non-coordinating heterocycle |
| `c1ccc(-c2ccccc2)cc1` | Biphenyl | Planar lipophilic aromatics are good CYP3A4 substrates/inhibitors | Introduce an sp3 carbon to break planarity, or add a polar group |

## AMES (mutagenicity)

Genotoxicity via **DNA-reactive electrophiles**. Aromatic amines and nitroarenes
are the archetypal Ames-positive alerts.

| SMARTS | Structural cause | Mechanism | Suggested fix |
|--------|------------------|-----------|---------------|
| `[NX3;H2]c1ccccc1` | Aromatic amine (aniline) | CYP1A2 N-hydroxylation gives an electrophilic nitrenium ion that forms DNA adducts | Acetylate (amide), N-methylate, or replace with a non-amino substituent |
| `[NX3;H2]c1ccc(cc1)[N+](=O)[O-]` | para-Nitroaniline | Nitroreduction plus amine activation yields a potent DNA-reactive species | Remove either the nitro or the amino group; use a non-reactive bioisostere |

## Solubility

| SMARTS | Structural cause | Mechanism | Suggested fix |
|--------|------------------|-----------|---------------|
| `c1ccc2ccccc2c1` | Fused aromatic rings (naphthalene-type) | Extended flat aromatics raise crystal-packing energy and lower aqueous solubility | Disrupt planarity with sp3 centres, cut ring count, or add solubilizing groups (OH, NH2) |

Solubility is *also* covered quantitatively by the ESOL LogS threshold in
`physchem-liabilities.md`.

## Extending the catalogue

Add a 5-tuple `(smarts, endpoint, cause, mechanism, fix)`. Guidelines:

- **Validate the SMARTS.** `Chem.MolFromSmarts(smarts)` must not return `None`;
  test it against a known positive and a known negative before trusting it.
- **Prefer specific SMARTS.** Add ring-size, charge (`[N+]`), hybridization
  (`[NX3]`), and aromaticity (`c` vs `C`) constraints to cut false positives.
- **Cite the mechanism.** The whole point is an actionable, falsifiable
  rationale — a bare pattern with no mechanism is just a filter.
- **Keep fixes constructive.** Name a bioisostere or transformation, not just
  "remove it".

## False-positive caveats

- SMARTS fires on the substructure regardless of context. Steric shielding,
  deactivating neighbours, or a metabolic soft spot elsewhere can make a flagged
  liability irrelevant.
- The **pyrimidinedione DILI alert** and the **fused-aromatic solubility alert**
  are deliberately broad and match many benign or endogenous scaffolds. Tighten
  their SMARTS before using a report to kill a chemical series.
- Absence of alerts is **not** a clean bill of health — the catalogue is a
  curated subset, not full ADMET coverage.
