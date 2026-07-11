# PyTDC Dataset Catalog

Datasets available through Therapeutics Data Commons, grouped by problem family and
task. Sizes are approximate and change as TDC adds data — treat them as guidance for
prototyping vs full runs, not exact counts. Enumerate the live list with
`retrieve_dataset_names` (bottom of this file) or check <https://tdcommons.ai/overview/>.

All datasets share the loader pattern:

```python
from tdc.<family> import <TaskClass>
data  = <TaskClass>(name='<DatasetName>')
df    = data.get_data(format='df')
split = data.get_split(method='scaffold', seed=1, frac=[0.7, 0.1, 0.2])
```

---

## Single-Instance Prediction (`tdc.single_pred`)

### `ADME` — absorption, distribution, metabolism, excretion

**Absorption**
- `Caco2_Wang` — Caco-2 permeability (~906)
- `Caco2_AstraZeneca` — Caco-2 permeability (~700)
- `HIA_Hou` — human intestinal absorption (~578)
- `Pgp_Broccatelli` — P-glycoprotein inhibition (~1,212)
- `Bioavailability_Ma` — oral bioavailability (~640)

**Distribution**
- `BBB_Martins` — blood-brain-barrier penetration (~1,975)
- `PPBR_AZ` — plasma protein binding rate (~1,797)
- `VDss_Lombardo` — volume of distribution at steady state (~1,130)

**Metabolism** (CYP450)
- `CYP2C19_Veith`, `CYP2D6_Veith`, `CYP3A4_Veith`, `CYP1A2_Veith`, `CYP2C9_Veith`
  — enzyme inhibition (~12k each)
- `CYP2C9_Substrate_CarbonMangels`, `CYP2D6_Substrate_CarbonMangels`,
  `CYP3A4_Substrate_CarbonMangels` — substrate classification (~660 each)

**Excretion**
- `Half_Life_Obach` — half-life (~667)
- `Clearance_Hepatocyte_AZ` (~1,020), `Clearance_Microsome_AZ` (~1,102)

**Solubility / lipophilicity**
- `Solubility_AqSolDB` — aqueous solubility (~9,982)
- `Lipophilicity_AstraZeneca` — logD (~4,200)
- `HydrationFreeEnergy_FreeSolv` — hydration free energy (~642)

### `Tox` — toxicity

- `hERG` (~648), `hERG_Karim` (~13,445) — cardiotoxicity
- `AMES` — mutagenicity (~7,255)
- `DILI` — drug-induced liver injury (~475)
- `LD50_Zhu` — acute toxicity (~7,385)
- `ClinTox` — clinical trial toxicity (~1,478)
- `Carcinogens_Lagunin` (~278), `Skin_Reaction` (~404)
- `Tox21-*` — 12 nuclear-receptor / stress-response endpoints (`AhR`, `AR`, `AR-LBD`,
  `ARE`, `aromatase`, `ATAD5`, `ER`, `ER-LBD`, `HSE`, `MMP`, `p53`, `PPAR-gamma`),
  ~6k–9k each
- `ToxCast` — environmental screening (~8,597)

### `HTS` — high-throughput screening (bioactivity)

- `SARSCoV2_Vitro_Touret` (~1,484), `SARSCoV2_3CLPro_Diamond` (~879)
- `HIV_Butkiewicz` — HIV inhibition (40k+)
- `Orexin1_Receptor_Butkiewicz`, `M1_Receptor_Agonist_Butkiewicz`,
  `M1_Receptor_Antagonist_Butkiewicz`

### `QM` — quantum-mechanical properties

- `QM7` (~7,160), `QM8` (~21,786), `QM9` (~133,885)

### Other single-prediction classes

- `Yields` — reaction yield (`Buchwald-Hartwig`, `USPTO_Yields`)
- `Epitope` — epitope binding for biologics
- `Develop` — developability (manufacturing, formulation)
- `CRISPROutcome` — gene-editing outcome (`CRISPROutcome_Doench`)

**Frame columns:** `Drug_ID`, `Drug` (SMILES), `Y` (continuous or binary label).

---

## Multi-Instance Prediction (`tdc.multi_pred`)

### `DTI` — drug-target interaction (binding affinity)

- `BindingDB_Kd` — dissociation constant (~52k pairs)
- `BindingDB_IC50` — IC50 (~991k pairs — **large**, watch memory)
- `BindingDB_Ki` — inhibition constant (~375k pairs)
- `DAVIS` (~30k), `KIBA` (~118k) — kinase binding

**Frame columns:** `Drug_ID`, `Target_ID`, `Drug` (SMILES), `Target` (amino-acid
sequence), `Y` (affinity). Prefer `cold_drug` / `cold_target` splits here.

### `DDI` — drug-drug interaction

- `DrugBank` — typed interactions (~191k pairs, 1,706 drugs; multi-class)
- `TWOSIDES` — side-effect-based DDI (~4.6M pairs)

### Other interaction classes

- `PPI` — protein-protein (`HuRI`, `STRING`)
- `GDA` — gene-disease association (`DisGeNET`)
- `DrugRes` — drug response/resistance (`GDSC1`, `GDSC2`)
- `DrugSyn` — drug synergy (`DrugComb`, `DrugCombDB`, `OncoPolyPharmacology`)
- `PeptideMHC` — peptide-MHC binding (`MHC1_NetMHCpan`, `MHC2_NetMHCIIpan`)
- `AntibodyAff` — antibody-antigen affinity (`Protein_SAbDab`)
- `MTI` — miRNA-target interaction (`miRTarBase`)
- `Catalyst` — reaction catalyst prediction (`USPTO_Catalyst`)
- `TrialOutcome` — clinical trial outcome (`TrialOutcome_WuXi`)

---

## Generation (`tdc.generation`)

### `MolGen` — molecular generation (training distributions)

- `ChEMBL_V29` — drug-like molecules (~1.9M)
- `ZINC` — ZINC subset (100k+)
- `Moses` — MOSES benchmark set (~1.9M)
- `GuacaMol` — goal-directed benchmark molecules

### `RetroSyn` — retrosynthesis (predict reactants)

- `USPTO` — full USPTO reactions (~1.9M)
- `USPTO-50K` — curated subset (~50k)

### `PairMolGen` — paired molecule generation

- `Prodrug` — prodrug→drug pairs
- `Metabolite` — drug→metabolite pairs

Pair generation with an `Oracle` for goal-directed design — see
[`oracles.md`](oracles.md).

---

## Enumerating and Inspecting Datasets

```python
from tdc.utils import retrieve_dataset_names

retrieve_dataset_names('ADME')   # list of loadable dataset names for that task
retrieve_dataset_names('DTI')
retrieve_dataset_names('Tox')
```

```python
from tdc.single_pred import ADME
data = ADME(name='Caco2_Wang')
data.print_stats()            # counts, label type
data.label_distribution()     # histogram / summary stats for the Y column
```

## Loading Notes

- **First access downloads** the dataset to the working directory (or `path=`) and
  caches it; subsequent loads are fast.
- **Large sets** (`BindingDB_IC50`, `TWOSIDES`, `USPTO`, `Moses`) are hundreds of MB
  to gigabytes — prototype on a small dataset first.
- Sizes and endpoints evolve; the live catalog is the source of truth:
  <https://tdcommons.ai/overview/>.
