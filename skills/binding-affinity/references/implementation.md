# Implementation Recipes

Copy-ready building blocks using real, publicly documented library APIs (RDKit,
BioPython, OpenMM, SciPy). Method theory and accuracy are in
[scoring-methods.md](scoring-methods.md). All code emits **raw** estimates — do
not rescale or calibrate the numbers afterward.

---

## Setup

```bash
# Required
pip install rdkit numpy scipy biopython

# Optional — full MM/GBSA physics path
pip install openmm openmmforcefields openff-toolkit
```

Verify:

```bash
python -c "from rdkit import Chem; print('RDKit OK')"
python -c "from Bio.PDB import PDBParser; print('BioPython OK')"
python -c "import scipy, numpy; print('SciPy/NumPy OK')"
python -c "import openmm; print('OpenMM OK')"   # optional
```

---

## 1. Ligand descriptors (RDKit)

```python
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

def ligand_descriptors(mol):
    return {
        "mw":              round(Descriptors.MolWt(mol), 1),
        "logp":            round(Descriptors.MolLogP(mol), 2),
        "tpsa":            round(Descriptors.TPSA(mol), 1),
        "hbd":             Descriptors.NumHDonors(mol),
        "hba":             Descriptors.NumHAcceptors(mol),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        "aromatic_rings":  rdMolDescriptors.CalcNumAromaticRings(mol),
        "formal_charge":   Chem.GetFormalCharge(mol),
        "n_heavy_atoms":   mol.GetNumHeavyAtoms(),
    }
```

Load docked poses with `Chem.SDMolSupplier(path, removeHs=False)`; skip entries
that come back as `None` (invalid molecules).

---

## 2. Protein atoms

Prefer BioPython for correct element typing; fall back to RDKit if unavailable.

```python
from Bio.PDB import PDBParser
import numpy as np

ELEM_Z = {"C": 6, "N": 7, "O": 8, "S": 16, "H": 1, "P": 15}

def protein_atoms(pdb_path, chain_id=None):
    """Return list of (coord: np.array[3], atomic_number)."""
    structure = PDBParser(QUIET=True).get_structure("prot", pdb_path)
    out = []
    for model in structure:
        for chain in model:
            if chain_id and chain.get_id() != chain_id:
                continue
            for residue in chain:
                for atom in residue:
                    z = ELEM_Z.get(atom.element.strip(), 6)
                    out.append((atom.get_vector().get_array(), z))
        break  # first model only
    return out
```

RDKit fallback: `Chem.MolFromPDBFile(pdb, removeHs=False, sanitize=False)`, then
read coordinates from `mol.GetConformer(0)` and atomic numbers from each atom.

---

## 3. Typed contact features

Distance cutoffs per contact type (see [scoring-methods.md](scoring-methods.md)):

```python
def contact_features(protein, ligand_mol, conf_id=0):
    conf = ligand_mol.GetConformer(conf_id)
    lig = []
    for i in range(ligand_mol.GetNumAtoms()):
        a = ligand_mol.GetAtomWithIdx(i)
        p = conf.GetAtomPosition(i)
        lig.append((np.array([p.x, p.y, p.z]), a.GetAtomicNum(), a.GetIsAromatic()))

    n_hyd = n_hb = n_arom = n_chg = n_tot = 0
    inv_r6 = 0.0
    min_d = []
    POLAR = {7, 8}  # N, O (proxy for both H-bond and charged)

    for lc, lz, l_arom in lig:
        closest = float("inf")
        for pc, pz in protein:
            d = float(np.linalg.norm(lc - pc))
            closest = min(closest, d)
            if lz == 6 and pz == 6 and d <= 4.5:          n_hyd += 1
            if lz in POLAR and pz in POLAR and d <= 3.5:  n_hb  += 1
            if l_arom and lz == 6 and pz == 6 and d <= 5.0: n_arom += 1
            if lz in POLAR and pz in POLAR and d <= 4.0:  n_chg += 1
            if 0.5 < d <= 6.0:
                n_tot += 1
                inv_r6 += 1.0 / d**6
        min_d.append(closest)

    buried = sum(1 for d in min_d if d < 4.0)
    return {
        "n_hydrophobic": n_hyd, "n_hbonds": n_hb, "n_aromatic": n_arom,
        "n_charged": n_chg, "n_total_contacts": n_tot,
        "burial_fraction": round(buried / len(min_d), 2) if min_d else 0.0,
        "energy_proxy": round(inv_r6, 4),
    }
```

For large proteins, prefer `Bio.PDB.NeighborSearch` or a `scipy.spatial.cKDTree`
over the ligand atoms to avoid the O(N_lig × N_prot) double loop.

---

## 4. Empirical pKd and thermodynamic conversions

Combine features linearly, clamp to a sane range, then convert. **Fit the
weights to a PDBbind-style benchmark** (or swap in a trained RF-Score model) —
the constants below are placeholder starting values, not a validated model.

```python
import math

T, R = 298.15, 1.987e-3  # K, kcal/(mol*K)

def empirical_pkd(desc, con):
    pkd = (1.8
           + 2.50 * con["burial_fraction"]
           + 0.60 * min(con["n_hbonds"], 10)
           + 0.15 * min(con["n_hydrophobic"], 30)
           + 0.30 * min(con["n_aromatic"], 10)
           + 0.40 * min(con["n_charged"], 5)
           + 0.10 * desc["logp"]
           - 0.002 * max(0, desc["mw"] - 500)
           + 0.50 * min(con["energy_proxy"], 5.0))
    return max(1.0, min(pkd, 12.0))

def pkd_to_dg(pkd):   return -R * T * math.log(10) * pkd            # kcal/mol
def pkd_to_kd_nm(pkd):                                             # nM, 1 sig fig
    kd = 10 ** (-pkd) * 1e9
    if kd == 0: return 0
    mag = 10 ** math.floor(math.log10(abs(kd)))
    return round(kd / mag) * mag
```

Round pKd to 1 decimal and Kd to ~1 significant figure to avoid false precision.

### Confidence

```python
def confidence(desc, con):
    issues = []
    if desc["mw"] < 200:  issues.append("MW<200")
    if desc["mw"] > 600:  issues.append("MW>600")
    if desc["logp"] < -1: issues.append("LogP<-1")
    if desc["logp"] > 5:  issues.append("LogP>5")
    if con["n_total_contacts"] < 10: issues.append("contacts<10")
    if not issues:
        return ("high" if con["n_total_contacts"] > 30 else "moderate"), []
    return ("low" if len(issues) >= 2 else "moderate"), issues
```

---

## 5. MM/GBSA via OpenMM (full path)

OpenMM computes a Generalized-Born potential energy for a topology. A rigorous
ΔG_MMGBSA subtracts three consistently-built end-points; the hard part is
parameterizing the ligand (GAFF/OpenFF) and assembling the complex topology.

```python
import openmm, openmm.app as app, openmm.unit as unit

def gb_energy(pdb_path, minimize_steps=0):
    """Generalized-Born potential energy (kcal/mol) of a system."""
    pdb = app.PDBFile(pdb_path)
    ff  = app.ForceField("amber14-all.xml", "implicit/obc2.xml")
    system = ff.createSystem(pdb.topology,
                             nonbondedMethod=app.NoCutoff,
                             constraints=app.HBonds)
    integ = openmm.LangevinMiddleIntegrator(
        300 * unit.kelvin, 1 / unit.picosecond, 0.002 * unit.picoseconds)
    sim = app.Simulation(pdb.topology, system, integ)
    sim.context.setPositions(pdb.positions)
    if minimize_steps > 0:
        sim.minimizeEnergy(maxIterations=minimize_steps)
    e = sim.context.getState(getEnergy=True).getPotentialEnergy()
    return e.value_in_unit(unit.kilocalories_per_mole)

# ΔG_MMGBSA = gb_energy(complex) - gb_energy(protein) - gb_energy(ligand)
# Building complex.pdb and a parameterized ligand.pdb is the real work here;
# use openmmforcefields/OpenFF (GAFF/SMIRNOFF) to template the ligand.
```

GB model choice: `implicit/obc2.xml` (OBC2) is a common default; OBC1 and HCT are
alternatives. Do not report a protein-only or ligand-only energy as a binding
ΔG.

### RDKit MMFF fallback (no OpenMM)

```python
from rdkit.Chem import AllChem, rdMolDescriptors

def mmff_energy(mol):
    props = AllChem.MMFFGetMoleculeProperties(mol, mmffVariant="MMFF94")
    if props is None: return None
    ff = AllChem.MMFFGetMoleculeForceField(mol, props)
    return ff.CalcEnergy() if ff else None   # kcal/mol
```

Add a crude solvation proxy (e.g. scaled TPSA for polar, scaled LogP for
nonpolar) only for coarse relative filtering — this is not a real GB solvation
term.

---

## 6. Consensus (rank normalization + Kendall τ)

Use `scipy.stats.kendalltau` for agreement.

```python
from scipy.stats import kendalltau

def rank_normalize(scores, higher_is_better):
    """scores: dict key->value -> dict key->normalized rank in [0,1]."""
    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=higher_is_better)
    n = len(items)
    return {k: {"rank": r + 1, "norm": round(1.0 - r / max(n - 1, 1), 3)}
            for r, (k, _) in enumerate(items)}

def consensus(normalized_sources, weights=None):
    """normalized_sources: dict source_name -> {key: {rank, norm}}."""
    names = list(normalized_sources)
    w = weights or {n: 1.0 / len(names) for n in names}
    keys = set().union(*[s.keys() for s in normalized_sources.values()])
    out = []
    for k in keys:
        num = sum(w[n] * normalized_sources[n][k]["norm"]
                  for n in names if k in normalized_sources[n])
        den = sum(w[n] for n in names if k in normalized_sources[n])
        out.append((k, round(num / den, 3) if den else 0.0))
    out.sort(key=lambda kv: kv[1], reverse=True)

    # mean pairwise Kendall tau over shared keys
    taus = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = sorted(set(normalized_sources[a]) & set(normalized_sources[b]))
            if len(shared) >= 2:
                ra = [normalized_sources[a][k]["rank"] for k in shared]
                rb = [normalized_sources[b][k]["rank"] for k in shared]
                tau, _ = kendalltau(ra, rb)
                if tau == tau:  # skip NaN
                    taus.append(tau)
    mean_tau = sum(taus) / len(taus) if taus else 0.0
    cls = "high" if mean_tau > 0.7 else "moderate" if mean_tau >= 0.4 else "low"
    return out, round(mean_tau, 3), cls
```

Remember each source's direction: empirical pKd and interaction counts are
higher-is-better; docking scores and MM/GBSA ΔG are lower (more negative) is
better.

---

## 7. Batch virtual screening

```python
from rdkit import Chem

def batch_screen(protein, library_sdf, threshold=None, top_n=None):
    prot = protein  # precomputed protein_atoms(...) — parse ONCE
    rows = []
    for i, mol in enumerate(Chem.SDMolSupplier(library_sdf, removeHs=False)):
        if mol is None:
            continue
        desc = ligand_descriptors(mol)
        con  = contact_features(prot, mol)
        pkd  = round(empirical_pkd(desc, con), 1)
        if threshold and pkd < threshold:
            continue
        conf, _ = confidence(desc, con)
        rows.append({"name": mol.GetProp("_Name") if mol.HasProp("_Name") else f"mol_{i+1}",
                     "smiles": Chem.MolToSmiles(mol), "pKd": pkd,
                     "Kd_nM": pkd_to_kd_nm(pkd), "dG": round(pkd_to_dg(pkd), 1),
                     "confidence": conf, "mw": desc["mw"], "logp": desc["logp"]})
    rows.sort(key=lambda r: r["pKd"], reverse=True)
    return rows[:top_n] if top_n else rows
```

Parse the protein once, apply `threshold` early to skip low-value rows on large
libraries, then write the survivors to CSV (add a `rank` column). Feed the
shortlist into consensus with docking scores when available.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| All poses score nearly the same | ligands too similar, or the function does not discriminate this target class — add MM/GBSA or interaction terms to the consensus |
| `low` confidence everywhere | molecules outside the drug-like domain (MW 200-600, LogP -1 to 5); the empirical model is unreliable there |
| OpenMM setup fails | missing/uncommon residues or ligand not parameterized; fall back to RDKit MMFF or supply GAFF/OpenFF ligand parameters |
| Screening is slow (>10k mols) | use a KD-tree for contacts, parse the protein once, and filter early with `threshold` |
| Predicted Kd looks absurdly precise | round pKd to 1 decimal and Kd to 1 significant figure |
| Negative / nonsensical MM/GBSA ΔG | you likely combined mismatched end-points; only compare complex − protein − ligand from consistently built systems |
