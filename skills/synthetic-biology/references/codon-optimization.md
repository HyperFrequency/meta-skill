# Codon Optimization

Back-translate a protein (or re-code an existing gene) into the codons a target
host prefers, then enforce constraints that matter for gene synthesis and
expression. Pure NumPy/Python — no external service.

## Codon Adaptation Index (CAI)

CAI measures how well a coding sequence matches a host's high-expression codon
usage. For each codon `i`, the relative adaptiveness weight is

```
w_i = f(codon_i) / f_max(synonyms of codon_i)
```

where `f` is the codon's usage frequency within its synonymous group. CAI is the
geometric mean of the weights over all coding codons:

```
CAI = exp( (1/L) * Σ ln(w_i) )
```

CAI ranges 0–1; the all-optimal sequence scores 1.0. A useful reading: >0.8 is
well-adapted, <0.5 suggests likely poor heterologous expression.

```python
import math

def calculate_cai(dna, usage, codon_to_aa):
    """usage: {aa: {codon: freq}} for one organism; codon_to_aa: {codon: aa}."""
    logs = []
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i+3]
        aa = codon_to_aa.get(codon)
        if aa is None or aa not in usage:
            continue
        syn = usage[aa]
        fmax = max(syn.values())
        if fmax == 0:
            continue
        freq = syn.get(codon, 0.0) or 1e-3      # floor rare codons to avoid log(0)
        logs.append(math.log(freq / fmax))
    return math.exp(sum(logs) / len(logs)) if logs else 0.0
```

## Codon usage tables

Provide, per organism, a `{amino_acid: {codon: fraction}}` table where the
fractions within each amino-acid group sum to ~1.0. Curated high-expression
tables (Kazusa-derived) are available for **`ecoli`**, **`yeast`**, **`human`**,
and **`cho`**. Structure (E. coli excerpt):

```python
CODON_USAGE = {
    "ecoli": {
        "F": {"TTT": 0.42, "TTC": 0.58},
        "L": {"TTA": 0.06, "TTG": 0.06, "CTT": 0.10, "CTC": 0.10,
              "CTA": 0.02, "CTG": 0.66},
        "M": {"ATG": 1.00},
        "K": {"AAA": 0.76, "AAG": 0.24},
        "*": {"TAA": 0.64, "TAG": 0.07, "TGA": 0.29},
        # ... all 20 aa + stop ...
    },
    # "yeast", "human", "cho" ...
}
```

You also need the standard 64-codon `{codon: amino_acid}` table for translation
and CAI (the inverse of the biological genetic code). The **optimal codon** for
an amino acid is `max(usage[aa], key=usage[aa].get)`.

Different hosts differ sharply — e.g. arginine's `AGA` is the top codon in yeast
(0.48) but rare in E. coli (0.04, where `CGT`/`CGC` dominate). Always select the
table that matches your expression host.

## Full optimization pipeline

Optimizing for CAI alone can create synthesis problems (extreme GC, restriction
sites, homopolymers). Run these four steps in order; each only swaps a codon for
a **synonymous** one, so the encoded protein never changes.

1. **Optimal-codon replacement** — replace every codon with the host's most
   frequent synonym (or back-translate the protein directly).
2. **Restriction-site removal** — eliminate cloning-enzyme recognition sites
   (default BsaI `GGTCTC`/`GAGACC`, BpiI `GAAGAC`/`GTCTTC`, both strands) by
   swapping an overlapping codon to a lower-ranked synonym that breaks the site.
3. **GC-content correction** — slide a window (default 30 bp, step by codon) and,
   where local GC falls outside 40–60%, swap codons toward the synonym that
   moves GC closest to 0.50 while staying in range.
4. **Homopolymer breaking** — remove runs >5 identical bases (which cause
   synthesis and sequencing errors) by swapping an overlapping codon.

```python
def optimize_sequence(dna, organism, usage, codon_to_aa):
    codons = [dna[i:i+3] for i in range(0, len(dna) - 2, 3)]
    codons = [best_codon(codon_to_aa[c], organism, usage) if c in codon_to_aa
              else c for c in codons]
    codons = remove_restriction_sites(codons, organism, usage, codon_to_aa)
    codons = fix_gc_content(codons, organism, usage, codon_to_aa,
                            target_min=0.40, target_max=0.60, window=30)
    codons = fix_homopolymers(codons, organism, usage, codon_to_aa, max_run=5)
    return "".join(codons)
```

Each constraint step iterates (cap at ~50 passes) because fixing one violation
can introduce another. Synonymous alternatives for a codon are the other codons
of its amino acid, sorted by usage descending: prefer the highest-CAI synonym
that still satisfies the constraint.

### Constraint-fix helper shape

```python
def synonymous_codons_for(codon, organism, usage, codon_to_aa):
    aa = codon_to_aa.get(codon)
    if aa is None or aa not in usage:
        return [codon]
    return sorted(usage[aa], key=usage[aa].get, reverse=True)

def gc_content(dna):
    return sum(b in "GC" for b in dna.upper()) / len(dna) if dna else 0.0
```

Restriction-site and homopolymer fixers locate the offending region, map it to
overlapping codon indices (`start // 3` … `(end-1)//3 + 1`), and try each
synonym until a swap clears the local motif — re-scanning after each pass.

## Input handling & verification

- **Detect DNA vs protein.** If the sequence contains only `ACGTN` it is DNA;
  if the non-DNA characters are all valid one-letter amino acids it is protein.
  Protein input is back-translated first, then run through the pipeline.
- **DNA length not a multiple of 3** — trim trailing bases and warn; do not pad.
- **Translation-preservation check (mandatory).** Translate input and output and
  compare; if the protein changed, the optimization is invalid — a swap escaped
  the synonymous group. Fail loudly.
- **Ambiguous residues** (`B`, `X`, `Z`, `U`) have no codon mapping — reject or
  require the caller to resolve them; do not silently substitute.
- Report the final CAI, GC%, remaining restriction sites, and homopolymer runs
  so the user can judge the CAI-vs-manufacturability trade-off.

## Edge cases & limits

- **Selenocysteine / pyrrolysine** and non-standard codes are unsupported.
- The GC fixer optimizes *local* windows greedily; it will not always reach a
  global GC target if the protein composition forbids it — report the achieved
  value rather than looping forever.
- Restriction-site removal only covers the enzymes you list; add the recognition
  motif (and its reverse complement) for any additional cloning enzyme.
- This is codon **selection**, not full sequence design — it does not model mRNA
  secondary structure near the RBS, ramp/rare-codon effects, or internal
  Shine-Dalgarno sequences. For those, treat the output as a strong first draft.
