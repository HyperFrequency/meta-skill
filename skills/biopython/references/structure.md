# Macromolecular Structures — `Bio.PDB`

`Bio.PDB` parses PDB and mmCIF files into a hierarchical object model and gives
you geometry, secondary-structure, neighbor-search, and superposition tools.

## SMCRA hierarchy

```
Structure → Model → Chain → Residue → Atom
```

- **Model** — usually one, but NMR ensembles have many.
- **Residue id** is a tuple `(hetflag, seqnum, insertion_code)`; standard amino
  acids use hetflag `" "` (a space), water is `"W"`, other heteroatoms `"H_..."`.

## Parsing and downloading

```python
from Bio.PDB import PDBParser, MMCIFParser, PDBList

s = PDBParser(QUIET=True).get_structure("1crn", "1crn.pdb")   # QUIET hides warnings
s = MMCIFParser(QUIET=True).get_structure("1crn", "1crn.cif") # prefer for big/modern

pdbl = PDBList()
pdbl.retrieve_pdb_file("1CRN", file_format="pdb", pdir="structures/")
pdbl.retrieve_pdb_file("1CRN", file_format="mmCif", pdir="structures/")
```

## Navigating the hierarchy

```python
model    = s[0]
chain    = model["A"]
residue  = chain[(" ", 10, " ")]     # or chain[10] for a plain standard residue
atom     = residue["CA"]
atom2    = s[0]["A"][10]["CA"]        # chained access

list(s.get_atoms())      # flat iterators at any level:
list(s.get_residues())   #   .get_atoms / .get_residues / .get_chains
list(s.get_chains())
```

Per-atom data: `atom.coord` (NumPy xyz), `atom.bfactor`, `atom.occupancy`,
`atom.element`, `atom.get_vector()`.

## Geometry

```python
d = residue1["CA"] - residue2["CA"]          # subtraction = distance in Å

from Bio.PDB.vectors import calc_angle, calc_dihedral
calc_angle(a1.get_vector(), a2.get_vector(), a3.get_vector())          # radians
calc_dihedral(a1.get_vector(), a2.get_vector(),
              a3.get_vector(), a4.get_vector())                        # radians
```

## Neighbor search (spatial queries)

```python
from Bio.PDB import NeighborSearch
ns = NeighborSearch(list(s.get_atoms()))
center = s[0]["A"][10]["CA"].coord
ns.search(center, 5.0)              # atoms within 5 Å
ns.search(center, 5.0, level="R")  # residues; level in {"A","R","C","M","S"}
```

Use this for contact maps and binding-site detection — it is far faster than an
all-pairs loop.

## Secondary structure & accessibility (DSSP)

Requires the external `dssp`/`mkdssp` binary:

```python
from Bio.PDB import DSSP
dssp = DSSP(s[0], "1crn.pdb")
for key in dssp:
    ss   = dssp[key][2]   # H,B,E,G,I,T,S,- ; helix/strand/turn/coil
    acc  = dssp[key][3]   # relative solvent accessibility
    phi  = dssp[key][4]
    psi  = dssp[key][5]
```

SS codes: `H` α-helix, `G` 3₁₀, `I` π-helix, `E` strand, `B` β-bridge, `T`
turn, `S` bend, `-` coil.

## Superposition & RMSD

```python
from Bio.PDB import Superimposer, PDBIO

ref = [a for a in s1.get_atoms() if a.name == "CA"]
mov = [a for a in s2.get_atoms() if a.name == "CA"]
n = min(len(ref), len(mov)); ref, mov = ref[:n], mov[:n]  # must match count

sup = Superimposer()
sup.set_atoms(ref, mov)          # computes optimal rotation/translation
sup.apply(s2.get_atoms())        # moves s2 onto s1
print(sup.rms)                   # RMSD in Å
```

`set_atoms` requires the two atom lists to be equal length and in
correspondence — align sequences first if the structures differ.

## Writing structures & selective output

```python
from Bio.PDB import PDBIO, MMCIFIO, Select

io = PDBIO(); io.set_structure(s); io.save("out.pdb")
MMCIFIO_ = MMCIFIO(); MMCIFIO_.set_structure(s); MMCIFIO_.save("out.cif")

class CAOnly(Select):
    def accept_atom(self, atom): return atom.name == "CA"
io.save("ca.pdb", CAOnly())      # override accept_model/chain/residue/atom
```

## Sequence from structure

```python
from Bio.PDB.Polypeptide import PPBuilder
for pp in PPBuilder().build_peptides(chain):
    seq = pp.get_sequence()           # a Seq; hand to SeqIO to write FASTA
    angles = pp.get_phi_psi_list()    # [(phi, psi), ...] for Ramachandran
```

## Common patterns

**Contact map (CA–CA under threshold):**

```python
res = [r for r in chain if r.has_id("CA")]
contacts = [(i, j) for i in range(len(res)) for j in range(i+1, len(res))
            if res[i]["CA"] - res[j]["CA"] < 8.0]
```

**Missing backbone atoms:**

```python
missing = [(r.full_id, a) for r in s.get_residues() if r.id[0] == " "
           for a in ("N", "CA", "C", "O") if not r.has_id(a)]
```

## Gotchas

- Always `PDBParser(QUIET=True)` on real-world files or you drown in warnings.
- Heteroatoms/waters have non-`" "` hetflags — filter on `residue.id[0] == " "`
  to keep only standard residues.
- Residues may carry **alternate conformations (altloc)** and structures may
  have **multiple models** — handle both before averaging geometry.
- `Superimposer` needs matched atom counts; slicing to `min(len...)` only works
  when the residues actually correspond.
