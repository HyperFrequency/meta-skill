# PyTDC Oracles

An **oracle** is a callable that scores a molecule (by SMILES) on a property. Oracles
are the objective functions for generation tasks: they turn "make a better molecule"
into a number a search loop can optimize. TDC ships 17+ built-in oracles.

Two uses:

1. **Goal-directed generation** — maximize/minimize a property (bind DRD2, be drug-like).
2. **Distribution learning** — check whether generated molecules match a target
   property distribution.

The generation/search algorithm itself belongs in `molecular-optimization`; this file
covers only the scoring layer.

## Basic Usage

```python
from tdc import Oracle

oracle = Oracle(name='GSK3B')
score  = oracle('CC(C)Cc1ccc(cc1)C(C)C(O)=O')   # single SMILES -> float
scores = oracle(['SMILES1', 'SMILES2', 'SMILES3'])  # list -> list of floats
```

Batch a list in one call — it is faster than looping, especially for ML oracles.

---

## Biochemical Oracles (target activity)

ML models predicting activity/binding against a biological target. Higher score =
stronger predicted activity. Medium speed.

| Name | Target | Typical use |
|------|--------|-------------|
| `DRD2` | Dopamine receptor D2 | CNS / psychiatric |
| `GSK3B` | Glycogen synthase kinase-3β | Alzheimer's, diabetes, oncology |
| `JNK3` | c-Jun N-terminal kinase 3 | Neurodegeneration |
| `5HT2A` | Serotonin 2A receptor | Psychiatric |
| `ACE` | Angiotensin-converting enzyme | Hypertension |
| `MAPK`, `P38`, `CDK`, `PARP1`, `PIK3CA` | Kinases / oncology targets | Cancer, inflammation |

```python
oracle = Oracle(name='DRD2')
score  = oracle(smiles)
```

`DRD2`, `GSK3B`, and `JNK3` are the standard trio used in de-novo design benchmarks.

---

## Physicochemical Oracles (drug-likeness / ADME proxies)

Fast, rule- or descriptor-based. No external models needed.

- **`QED`** — quantitative estimate of drug-likeness, 0 (poor) → 1 (drug-like);
  Bickerton et al. Higher is better.
- **`SA`** — synthetic accessibility, 1 (easy) → 10 (hard). **Lower is better** — invert
  it in composite objectives.
- **`LogP`** — octanol-water partition coefficient (lipophilicity); drug-like ≈ 0–5.
- **`MW`** — molecular weight in Daltons; drug-like ≈ 150–500.
- **`Lipinski`** — count of Rule-of-Five violations (MW ≤ 500, logP ≤ 5, HBD ≤ 5,
  HBA ≤ 10); 0 = fully compliant.

```python
qed = Oracle(name='QED')(smiles)   # 0..1
sa  = Oracle(name='SA')(smiles)    # 1..10, lower better
```

---

## Composite / Benchmark Oracles

Used in GuacaMol/MOSES-style distribution and rediscovery benchmarks.

- **`Isomer_Meta`** — target a specific molecular formula / isomer profile.
- **`Median1`, `Median2`** — reward molecules similar to multiple references at once.
- **`Rediscovery`** — similarity to a known reference drug (can you regenerate it?).
- **`Similarity`** — structural similarity to a target (typically Tanimoto over
  fingerprints).
- **`Uniqueness`** — fraction of unique molecules in a set (pass a list).
- **`Novelty`** — how different generated molecules are from a training set (needs the
  training set as context).

```python
uniq = Oracle(name='Uniqueness')(generated_smiles_list)
```

---

## Docking / Retrosynthesis Oracles (slow, need backends)

These require external software and are far slower — reserve for final scoring, not
inner-loop optimization of thousands of candidates.

- **`Docking` / `Vina`** — protein-ligand docking (AutoDock Vina). Returns binding
  energy in kcal/mol; **more negative = stronger**. Needs a prepared protein structure
  and the docking binary.
- **`ASKCOS`** — retrosynthetic feasibility scoring. Needs an ASKCOS backend.

If the backend is missing, these raise at call time — verify the install before
depending on them.

---

## Speed and Reliability

- **Fast** (rule-based): `QED`, `SA`, `LogP`, `MW`, `Lipinski`.
- **Medium** (ML models): `DRD2`, `GSK3B`, `JNK3`, other target oracles.
- **Slow** (external): `Vina`, `Docking`, `ASKCOS`.

Oracle scores are **predictions, not measurements** — ML oracles may not generalize
outside their training chemical space. Validate top candidates experimentally, and
sanity-check with more than one oracle.

---

## Multi-Objective Optimization

Real design balances potency, drug-likeness, and synthesizability. Combine oracles in
a custom scoring function, remembering each oracle's direction and range:

```python
from tdc import Oracle

qed_oracle  = Oracle(name='QED')    # higher better, 0..1
sa_oracle   = Oracle(name='SA')     # lower better, 1..10
drd2_oracle = Oracle(name='DRD2')   # higher better

def objective(smiles):
    qed  = qed_oracle(smiles)
    sa   = 1.0 / (1.0 + sa_oracle(smiles))   # invert so higher is better
    drd2 = drd2_oracle(smiles)
    return 0.3 * qed + 0.3 * sa + 0.4 * drd2

objective('CC(C)Cc1ccc(cc1)C(C)C(O)=O')
```

---

## Goal-Directed Generation Loop

The generator is yours (`molecular-optimization`); the oracle ranks its output:

```python
from tdc import Oracle
from tdc.generation import MolGen

seed_smiles = MolGen(name='ChEMBL_V29').get_data()['Drug'].tolist()
oracle = Oracle(name='GSK3B')

# generated = your_generator.generate(n=1000)   # user-supplied
scores = oracle(generated)                        # batch score
ranked = sorted(zip(generated, scores), key=lambda x: x[1], reverse=True)
for smiles, score in ranked[:10]:
    print(f"{score:.3f}  {smiles}")
```

## Distribution Learning

Compare generated vs training property distributions instead of maximizing:

```python
import numpy as np
from tdc import Oracle

qed = Oracle(name='QED')
train_scores, gen_scores = qed(train_smiles), qed(generated)
print(f"train  mu={np.mean(train_scores):.3f} sd={np.std(train_scores):.3f}")
print(f"gen    mu={np.mean(gen_scores):.3f} sd={np.std(gen_scores):.3f}")
```

## Custom Oracles

Any callable with the `(smiles) -> score` (or list→list) contract works as an oracle in
your own loops:

```python
class CustomOracle:
    def __call__(self, smiles):
        # return a float, or a list of floats for a list input
        ...
```

Reference: <https://tdcommons.ai/functions/oracles/>. GuacaMol and MOSES papers define
the composite/distribution benchmarks these oracles back.
