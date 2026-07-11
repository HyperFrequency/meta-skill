# ADMET Endpoint Reference

Clinical meaning, computational thresholds, and applicability limits for every
endpoint in the panel. Thresholds are the empirical cutoffs used to assign the
GREEN / YELLOW / RED traffic light. All descriptor-derived rules are surrogates —
see each endpoint's limits and the experimental gold standard it approximates.

- [Absorption](#absorption)
- [Distribution](#distribution)
- [Metabolism](#metabolism)
- [Excretion](#excretion)
- [Toxicity](#toxicity)
- [Drug-likeness](#drug-likeness)
- [Prioritization by therapeutic area](#prioritization)

---

## Absorption

### Caco-2 permeability
Rate of transit across a Caco-2 monolayer, the standard in vitro proxy for
passive intestinal absorption (reported as Papp, or high/medium/low).
- GREEN (high): TPSA < 90 Å² (typically Papp > 8×10⁻⁶ cm/s).
- YELLOW (medium): TPSA 90–140 Å².
- RED (low): TPSA > 140 Å² — likely poor oral absorption; consider prodrug or
  non-oral routes.
- **Limit:** TPSA ignores active influx/efflux, paracellular transport, and
  monolayer metabolism. A trained model (`pytdc` `Caco2_Wang`, or ADMET-AI) is
  more faithful than the TPSA surrogate.

### Human intestinal absorption (HIA)
Fraction of an oral dose absorbed into the portal vein; the first PK hurdle.
- GREEN (likely high): TPSA < 140 **and** RotBonds ≤ 10.
- YELLOW: exactly one criterion met.
- RED (likely low): TPSA > 140 **and** RotBonds > 10.
- **Limit:** Active transporters (e.g. PEPT1) and enabling formulations can rescue
  poor passive absorbers.

### P-glycoprotein (P-gp / ABCB1) substrate
Efflux at the gut, BBB, and renal tubules → reduced oral bioavailability, limited
brain penetration, and P-gp-inhibitor DDI risk.
- GREEN (unlikely): MW < 400 **and** TPSA < 100, no P-gp motif.
- YELLOW: borderline size/polarity or a motif match.
- RED (likely): MW > 400 **and** TPSA > 130.
- **Limit:** Physicochemical prediction is only moderately accurate; MDCK-MDR1
  bidirectional transport is definitive.

### Aqueous solubility (LogS, ESOL)
Thermodynamic solubility at pH 7.4 as log₁₀(mol/L), via the Delaney ESOL model:
`LogS = 0.16 − 0.63·cLogP − 0.0062·MW + 0.066·RotBonds − 0.74·AromaticProportion`.
- GREEN: LogS > −4 (> 0.1 mM).
- YELLOW: LogS −4 to −6 — may need enabling formulation.
- RED: LogS < −6 (< 0.001 mM) — severe limitation.
- **Limit:** ESOL RMSE ≈ 0.7 log units; ignores crystal packing, polymorphism,
  salts. Measure kinetic/thermodynamic solubility for advanced compounds.

---

## Distribution

### Blood–brain barrier (BBB) penetration
Whether the compound distributes into brain tissue. Desired for CNS targets, a
liability (CNS side effects) for peripheral ones.
- Score = `cLogP − TPSA/60`.
- GREEN (likely): score > 0, MW < 450, TPSA < 90.
- YELLOW (uncertain): score > −0.5 but not all criteria met.
- RED (unlikely): score < −0.5 or MW > 450 or TPSA > 90.
- **Limit:** Real penetration depends on P-gp efflux, free fraction, and influx
  transport; in vivo Kp,uu is the gold standard.

### Plasma protein binding (PPB)
Fraction bound to albumin / α1-acid glycoprotein. Only free drug is active. High
PPB is not itself a liability — free concentration at target is what matters.
- GREEN: PPB < 95% (cLogP < 4), or PPB < 50% (cLogP < 0).
- YELLOW: PPB > 95% (cLogP > 4) — measure free fraction, adjust dosing.
- **Limit:** cLogP is crude; acidic drugs bind albumin, basic drugs bind AAG.
  Equilibrium dialysis / ultrafiltration for accuracy.

### Volume of distribution (VDss)
Apparent steady-state distribution volume. Sets half-life (with clearance) and
loading dose.
- GREEN (moderate): 0.5–2 L/kg; GREEN (low): < 0.5 L/kg.
- YELLOW (high): > 2 L/kg with a basic N and cLogP > 3 (tissue accumulation).
- **Limit:** Approximate from physchem; in vivo PK is definitive.

---

## Metabolism

### CYP450 liability (CYP3A4, CYP2D6, CYP2C9)
Likelihood of being a substrate/inhibitor of the three dominant isoforms
(CYP3A4 ~50% of drugs, CYP2D6 ~25%, CYP2C9 ~15%) → drug–drug-interaction risk.
CYP3A4 favors large lipophilic molecules; CYP2D6 basic amines with an aromatic
ring 5–7 Å from N; CYP2C9 anionic lipophilic acids.
- GREEN: no alerts, no size/lipophilicity flags.
- YELLOW: 1 alert or borderline physchem.
- RED: 2+ alerts.
- **Limit:** SMARTS alerts miss many substrates and cannot separate substrate from
  inhibitor. Use `pytdc` CYP datasets (e.g. `CYP3A4_Veith`) or ADMET-AI for
  learned inhibition prediction; confirm with an IC50 panel + HLM stability.

### Metabolic soft spots
Sites prone to Phase I oxidation/hydrolysis/conjugation, found by SMARTS matching:
benzylic/aryl-methyl (CYP oxidation), N-dealkylation, ester/amide hydrolysis,
thioether S-oxidation, phenol (UGT), aromatic amine (NAT). Blocking a soft spot
(e.g. benzylic CH₂ → CF₂) is a core stability-optimization move.
- GREEN: 0–1 soft spots; YELLOW: 2–3; RED: 4+.
- **Limit:** Qualitative — actual turnover depends on 3D orientation in the CYP
  active site. MetID with HLM/hepatocytes is the standard.

---

## Excretion

### Clearance route and rate
Predicted primary route (hepatic vs renal) and rate class; sets half-life and
dosing frequency.
- GREEN (renal): MW < 350, cLogP < 1, TPSA > 80 (glomerular filtration).
- GREEN (moderate hepatic): cLogP 2–3.
- YELLOW (lipophilic hepatic): cLogP > 3, MW > 400.
- RED (high-clearance risk): cLogP > 4, MW > 500 (high first-pass, short t½).
- **Limit:** The *least* accurate ADMET endpoint from physchem alone. Real
  clearance depends on enzyme kinetics, hepatic blood flow, and OATP uptake;
  scale in vitro intrinsic clearance (HLM/hepatocyte) to in vivo.

---

## Toxicity

### hERG channel liability
Blockade of the hERG K⁺ channel prolongs QT → risk of Torsades de Pointes; the
single most common cause of drug withdrawal. Classic blockers combine a basic
protonatable N, hydrophobic aromatic mass, and 5–10 Å separation between them.
- GREEN: no alerts (low probability of IC50 < 10 µM).
- YELLOW: 1 alert — run patch-clamp.
- RED: 2+ alerts — prioritize early testing.
- **Limit:** High sensitivity, low specificity (many false positives). Automated
  patch-clamp (QPatch) is definitive; ADMET-AI / `pytdc` `hERG` add a learned
  probability.

### AMES mutagenicity
Bacterial reverse-mutation risk via structural alerts: aromatic amines, nitro,
N-nitroso/azo, alkylating agents (epoxides, aziridines, alkyl halides, sulfonate
esters), Michael acceptors, acylating agents, PAHs, intercalators. A positive AMES
is a regulatory showstopper (ICH M7).
- GREEN: no alerts; RED: 1+ alert — test before progressing.
- **Limit:** Alerts are ~85% sensitive, ~65% specific; molecular context (steric
  shielding, deactivation) often nullifies an alerting substructure.

### Hepatotoxicity (DILI)
Liver-injury risk from reactive-metabolite precursors (catechols/hydroquinones/
aminophenols/anilides → quinone imines), acyl glucuronide formers (carboxylic
acids), hydrazines, thioureas, nitroaromatics, nitriles. Leading cause of
post-market withdrawal.
- GREEN: no alerts; YELLOW: 1 alert (monitor LFTs); RED: 2+ alerts.
- **Limit:** Idiosyncratic DILI is immune/genetic and poorly predicted by any
  method. Add reactive-metabolite trapping (GSH/KCN) and hepatocyte viability.

### Skin sensitization
Allergic contact dermatitis via haptenization by electrophiles; matters for
topical/occupational exposure.
- GREEN: no electrophile alerts; YELLOW: 1 low-severity alert; RED: any
  high-severity alert (epoxide, acyl halide, isocyanate).
- **Limit:** DPRA / KeratinoSens are the in vitro standards.

### Phospholipidosis (cationic amphiphilic drugs)
Lysosomal phospholipid accumulation. CAD criteria: basic/cationic N + cLogP > 2 +
MW > 300.
- GREEN: not a CAD; YELLOW: moderate CAD; RED: strong CAD (basic N, cLogP > 4).
- **Limit:** Not all CADs cause clinically relevant PLD; NBD-PE assays are better.

### LD50 acute-toxicity class
Rough GHS class from toxic structural motifs (Class 1 ≤ 5 mg/kg … Class 5
2000–5000 mg/kg).
- GREEN: no toxic motifs (~Class 4–5); YELLOW: moderate motifs (~Class 3–4);
  RED: high-toxicity motifs — organophosphates, heavy metals (~Class 1–3).
- **Limit:** The crudest endpoint here — LD50 is a whole-molecule property. In
  vivo or validated in vitro (3T3 NRU) testing is always required.

### PAINS (pan-assay interference)
Substructures that produce non-specific false-positive assay hits (aggregation,
redox cycling, fluorescence, chelation). A PAINS flag warrants counter-screens,
not automatic rejection.
- GREEN: 0 alerts; YELLOW: 1; RED: 2+.
- **Limit:** Derived from AlphaScreen; some PAINS-flagged compounds are genuine
  binders (e.g. curcumin analogs). Implemented via RDKit `FilterCatalog`.

---

## Drug-likeness

### Lipinski Rule of Five
Oral-bioavailability heuristic (Lipinski 1997): MW ≤ 500, cLogP ≤ 5, HBD ≤ 5,
HBA ≤ 10.
- GREEN: 0 violations; YELLOW: 1 (many approved drugs have one); RED: 2+.

### QED (quantitative estimate of drug-likeness)
Weighted 0–1 desirability over eight properties, calibrated to marketed drugs
(Bickerton 2012). RDKit `QED.qed(mol)`.
- GREEN: > 0.67; YELLOW: 0.49–0.67; RED: < 0.49.

### Synthetic accessibility (SA score)
Ease of synthesis 1 (easy) – 10 (hard), from fragment contributions + complexity
(Ertl & Schuffenhauer 2009; RDKit Contrib `sascorer`).
- GREEN: ≤ 4; YELLOW: 4–6; RED: > 6.

### Fsp3 (fraction sp³ carbons)
3D character; higher Fsp3 correlates with clinical success (Lovering 2009). RDKit
`CalcFractionCSP3`.
- GREEN: ≥ 0.25; YELLOW: 0.1–0.25; RED: < 0.1.

---

## Prioritization

When several endpoints flag, resolve in this order:

1. **Safety-critical first** — hERG (cardiac death), AMES (regulatory
   showstopper), DILI (top withdrawal cause).
2. **Efficacy-enabling second** — solubility, permeability, BBB (CNS targets),
   metabolic stability.
3. **Optimization metrics last** — QED, SA score, Fsp3, Lipinski.

A compound with GREEN toxicity but YELLOW drug-likeness is far preferable to one
with GREEN drug-likeness but RED toxicity.

### By therapeutic area
- **Oncology** — hERG, DILI, solubility high; AMES sometimes tolerated; Ro5 / BBB
  low priority.
- **CNS** — BBB penetration, P-gp (must not efflux), hERG, CYP2D6 polymorphism.
- **Cardiovascular** — hERG is absolute priority; AMES, DILI, PPB (narrow index).
- **Anti-infectives** — solubility, HIA, CYP DDI (polypharmacy), AMES, DILI.
- **Topical / dermatology** — skin sensitization, MW/cLogP for skin penetration.
- **Rare / orphan** — toxicity endpoints weighted high; strict Ro5 relaxable given
  unmet need.
