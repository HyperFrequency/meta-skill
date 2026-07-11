# Datamol Reactions and Datasets

## Reactions — `dm.reactions`

Apply chemical transformations defined as SMARTS reaction patterns. The reaction
object itself comes from RDKit; datamol handles the application and product cleanup.

`dm.reactions.apply_reaction(rxn, reactants, product_index=None, single_product_group=False, as_smiles=False, rm_attach=False, sanitize=True)`

| Parameter | Meaning |
|---|---|
| `rxn` | RDKit reaction (`ReactionFromSmarts`) |
| `reactants` | **Tuple** of reactant `Mol` objects (single reactant → `(mol,)`) |
| `product_index` | Which product to return; `None` (default) returns all matched products |
| `single_product_group` | `True` returns one flattened product group; default `False` returns every product group |
| `as_smiles` | Return SMILES (`True`) or `Mol` (`False`, default) |
| `rm_attach` | Strip attachment-point markers from products (default `False`) |
| `sanitize` | Sanitize products (default `True`) |

By default (`product_index=None, single_product_group=False`) you get back a nested
list of product groups. For the common "one clean product" case, pin
`single_product_group=True, product_index=0`:

```python
from rdkit.Chem import rdChemReactions

rxn = rdChemReactions.ReactionFromSmarts(
    "[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[Cl:3]"    # acid → acid chloride
)
product = dm.reactions.apply_reaction(
    rxn, (dm.to_mol("CC(=O)O"),),
    single_product_group=True, product_index=0, sanitize=True,   # single Mol back
)
```

### Building reactions (RDKit)

```python
from rdkit.Chem import rdChemReactions
# amide formation: amine + carboxylic acid → amide
amide = rdChemReactions.ReactionFromSmarts("[N:1].[C:2](=[O:3])[OH]>>[N:1][C:2](=[O:3])")
# Suzuki coupling: aryl halide + boronic acid → biaryl
suzuki = rdChemReactions.ReactionFromSmarts("[c:1][Br].[c:2][B]([OH])[OH]>>[c:1][c:2]")
```

### Batch application (guard every product)

```python
products = []
for m in reactants:
    try:
        p = dm.reactions.apply_reaction(
            rxn, (m,), single_product_group=True, product_index=0
        )
        if p is not None:
            products.append(p)
    except Exception as e:
        print(f"reaction failed: {e}")
```

### Concepts

- **SMARTS** is the pattern language; atom maps (`[C:1]`) preserve atom identity
  across the arrow; `[1*]` is a generic attachment point.
- Not every SMARTS reaction is chemically reasonable — validate products on known
  cases before trusting a transform at scale.

---

## Toy Datasets — `dm.data`

Small, pre-cleaned datasets for testing code and tutorials. Return a DataFrame
(`as_df=True`) or a molecule list.

| Function | Contents |
|---|---|
| `dm.data.cdk2(as_df=True, mol_column="mol")` | RDKit CDK2 kinase-inhibitor set with activity data |
| `dm.data.freesolv()` | 642 molecules with experimental/calculated hydration free energies (`iupac`, `smiles`, `expt`, `calc`) |
| `dm.data.solubility(as_df=True, mol_column="mol")` | Aqueous solubility with a `split` column (`train`/`test`) |

```python
sol = dm.data.solubility(as_df=True)
train, test = sol[sol.split == "train"], sol[sol.split == "test"]
X_train = [dm.to_fp(m) for m in train["mol"]]
```

### Important

These are **toy** datasets — for learning and smoke-testing pipelines only. Do not
benchmark models or draw scientific conclusions from them; validate real work on
real project data, and cite original sources if you publish.
