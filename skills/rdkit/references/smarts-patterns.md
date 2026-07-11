# SMARTS Pattern Library for RDKit

Vetted SMARTS strings for substructure search. Compile with
`Chem.MolFromSmarts(pattern)` (returns `None` on a malformed pattern — check it),
then query with `mol.HasSubstructMatch(query)` or `mol.GetSubstructMatches(query)`.

Lowercase atoms (`c`, `n`, `o`, `s`) are aromatic; uppercase are aliphatic. `X`
is total connections, `H` explicit hydrogen count, `R` ring membership, `r`
ring size, `D` degree, `+`/`-` charge, `~` any bond.

## Functional groups

```text
[OH1][C]              any alcohol            [CH2][OH1]      primary alcohol
c[OH1]                phenol                 [CH1](=O)       aldehyde
[C](=O)[C]            ketone                 [C](=O)         any carbonyl
C(=O)[OH1]            carboxylic acid        [CX3](=O)[OX2H1]  (stricter acid)
C(=O)O[C]             ester                  C(=O)N          amide
[NX3]                 any amine              [NH2][C]        primary amine
c[NH2]                aniline                [C][O][C]       ether
C#N                   nitrile                [N+](=O)[O-]    nitro
[C][F,Cl,Br,I]        alkyl halide           c[F,Cl,Br,I]    aryl halide
[C][SH1]              thiol                  [C][S][C]       sulfide
[C][S](=O)[C]         sulfoxide              [C][S](=O)(=O)[C]  sulfone
S(=O)(=O)N            sulfonamide            [N]C(=[N])[N]   guanidine
```

## Ring systems & heterocycles

```text
c1ccccc1              benzene                C1CCCCC1        cyclohexane
[r5] [r6] [r7]        n-membered ring        a1aaaaa1        any aromatic 6-ring
n1ccccc1              pyridine               n1cccc1         pyrrole
o1cccc1               furan                  s1cccc1         thiophene
n1cncc1               imidazole              n1cnccc1        pyrimidine
c1ccc2ccccc2c1        naphthalene            c1ccc2[nH]ccc2c1  indole
n1cccc2ccccc12        quinoline              n1cnc2ncnc2c1   purine
[nR] [oR] [sR]        aromatic hetero-atom in ring
[r{12-}]              macrocycle (12+ atoms) [r{9-15}]       ring of 9–15 atoms
```

## Pharmacophore features

```text
[OH,NH,NH2,NH3+]      H-bond donor           [O,N]           H-bond acceptor (broad)
[OX2]                 ether/hydroxyl acceptor [N;!H0]        protonatable N acceptor
[O]=[C,S,P]           carbonyl-type acceptor
c1ccccc1              aromatic (pi-stacking)  [aR]           any aromatic ring atom
CCCC                  hydrophobic chain       C(C)(C)C       branched hydrophobe
```

## Charge & stereo

```text
[+] [-]               any charge             [+1] [-1] [+2]  specific charge
[N+]                  cationic N             [O-]            anionic O
C(=O)[O-]             carboxylate            [N+]([C])([C])([C])[C]  ammonium
[C@] [C@@]            tetrahedral chirality  C/C=C/C  C/C=C\\C  E / Z double bond
```

## Hybridization & connectivity

```text
[CX2]  sp carbon      [CX3]  sp2 carbon      [CX4]  sp3 carbon    [CH3]  methyl
[D1] [D2] [D3] [D4]   degree (neighbor count)
[R] [!R]              in ring / not in ring  [R1] [R2]       in exactly 1 / 2 rings
[*]  any atom         [#6]  atomic number 6  [!C]  not aliphatic carbon
[F,Cl,Br,I]           any halogen
```

## PAINS / reactive alerts (usually exclusion filters)

```text
S1C(=O)NC(=S)C1       rhodanine              O=C1C=CC(=O)C=C1   quinone
c1ccc(O)c(O)c1        catechol               OC1=CC=C(O)C=C1    hydroquinone
C=CC(=O)[C,N]         Michael acceptor       C(=O)Cl            acyl chloride
C1OC1                 epoxide                [C][I,Br]          reactive alkyl halide
```

## Privileged / common scaffolds

```text
c1ccccc1-c2ccccc2     biphenyl               N1CCNCC1        piperazine
N1CCCCC1              piperidine             N1CCOCC1        morpholine
c1ccccc1C(=O)N        benzamide              [N][C](=O)[N]   urea
```

## Metal-binding motifs

```text
C(=O)[O-]             carboxylate chelator   C(=O)N[OH]      hydroxamic acid
c1c(O)c(O)ccc1        catechol (Fe chelator) [SH]            thiol
```

## Usage

```python
from rdkit import Chem

groups = {
    "alcohol": "[OH1][C]",
    "amine": "[NX3]",
    "carboxylic_acid": "C(=O)[OH1]",
}
mol = Chem.MolFromSmiles("NCCO")
for name, smarts in groups.items():
    q = Chem.MolFromSmarts(smarts)
    if q is not None and mol.HasSubstructMatch(q):
        print("found", name)
```

## Writing SMARTS reliably

1. Be explicit when it matters — `[CX3]` (sp2) is stricter than bare `[C]`.
2. Aromatic vs aliphatic is a hard distinction: `c` never matches `C`.
3. Charge and H-count in the query must be satisfied by the target.
4. Use recursive SMARTS `$(...)` for context-dependent atoms.
5. Always validate a new pattern against a known positive *and* a known negative
   before running it over a library.
