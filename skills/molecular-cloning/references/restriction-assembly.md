# Restriction Digestion, Golden Gate & Gibson Assembly

Covers capability 3 (`restriction_digest`), capability 4 (`design_golden_gate`),
and capability 5 (`design_gibson_assembly`). Biopython only.

---

## 3. Restriction digestion

`Bio.Restriction` exposes every enzyme as an object with a `.search(seq)`
method returning **1-based** cut positions, and a batch/`Analysis` interface for
multiple enzymes at once. Handle circular molecules with `linear=False`.

```python
from Bio.Restriction import RestrictionBatch, Analysis
from Bio.Restriction import *  # brings enzyme names (EcoRI, BamHI, ...) into scope


def restriction_digest(sequence, enzymes, is_linear=True):
    """Simulate a digest and return fragment sizes (bp), largest first.

    sequence: Bio.Seq
    enzymes:  list of enzyme names, e.g. ['EcoRI', 'BamHI']
    is_linear: False for a plasmid / circular molecule
    """
    batch = RestrictionBatch()
    for name in enzymes:
        batch.add(eval(name))  # resolve the name to its enzyme object

    results = Analysis(batch, sequence, linear=is_linear).full()

    cut_sites = []
    for enzyme, sites in results.items():
        print(f"{enzyme}: {sites if sites else 'no cut sites'}")
        cut_sites.extend(sites)

    if not cut_sites:
        print(f"Single fragment: {len(sequence)} bp")
        return [len(sequence)]

    cut_sites = sorted(set(cut_sites))

    if is_linear:
        bounds = [0] + cut_sites + [len(sequence)]
        fragments = [bounds[i + 1] - bounds[i] for i in range(len(bounds) - 1)]
    else:
        # circular: n cuts -> n fragments; the last wraps past the origin
        fragments = []
        for i in range(len(cut_sites)):
            nxt = (i + 1) % len(cut_sites)
            if nxt == 0:
                fragments.append(len(sequence) - cut_sites[i] + cut_sites[0])
            else:
                fragments.append(cut_sites[nxt] - cut_sites[i])

    fragments.sort(reverse=True)
    print(f"Fragments ({len(fragments)}): {fragments}  total {sum(fragments)} bp")
    return fragments
```

### Notes and failure modes

- **`eval(name)`** resolves an enzyme name to its object because
  `from Bio.Restriction import *` pulls all enzymes into the namespace. If you
  prefer not to `eval`, build the batch from strings directly:
  `RestrictionBatch(enzymes)` also accepts a list of names.
- **1-based vs 0-based.** `.search()`/`Analysis` positions are 1-based (the cut
  is *before* that base on the top strand). If you slice the `Seq` to extract a
  fragment, subtract 1.
- **Fragment count.** Linear → `cuts + 1`; circular → `cuts`. A plasmid digested
  once linearizes into a single band equal to the plasmid length.
- **Enzyme doesn't cut where expected.** Check dam/dcm methylation sensitivity
  (the site may be protected in DNA from a standard host). Use
  `EnzymeName.isoschizomers()` to find a methylation-insensitive alternative,
  and confirm the site isn't disrupted by an upstream base.
- **Useful helpers:** `EnzymeName.is_blunt()`, `.elucidate()` (shows the cut with
  overhang), `.frequency()`, and the enzyme sets `CommOnly` (commercially
  available) and `AllEnzymes`.

---

## 4. Golden Gate assembly (Type IIS)

Golden Gate uses a Type IIS enzyme (BsaI, BsmBI/Esp3I, or BbsI/BpiI) that cuts
*outside* its recognition site, leaving programmable 4 bp overhangs. Parts
assemble in a defined order because each junction's overhang is unique. The high
-value check this function performs is verifying the overhang set is **unique
and non-palindromic** — a duplicated or self-complementary overhang causes
mis-ligation or self-ligation.

```python
from Bio.Seq import Seq

# A vetted, high-fidelity 4 bp overhang ladder (MoClo-style). Swap in your own
# from a published fidelity dataset (e.g. Potapov et al. 2018) for >4 parts.
STANDARD_OVERHANGS = ["AATG", "AGGT", "TTCG", "GCTT", "CGCT"]

RECOGNITION = {"BsaI": ("GGTCTC", "N"), "BpiI": ("GAAGAC", "NN")}


def design_golden_gate(parts, enzyme="BsaI", overhangs=STANDARD_OVERHANGS):
    """Lay out a Golden Gate assembly and validate its overhangs.

    parts: list of {'name': str, 'sequence': str} in assembly order.
    enzyme: 'BsaI' or 'BpiI' (BbsI). Determines the flanking recognition site.
    Returns a per-part plan; raises on a broken overhang set.
    """
    needed = len(parts) + 1
    if needed > len(overhangs):
        raise ValueError(f"{len(parts)} parts need {needed} overhangs; "
                         f"only {len(overhangs)} supplied")
    used = overhangs[:needed]

    # Validate: unique, non-palindromic
    for i, oh in enumerate(used):
        if oh == str(Seq(oh).reverse_complement()):
            print(f"WARNING: overhang {oh} is palindromic — may self-ligate")
        for j, other in enumerate(used):
            if i != j and oh == other:
                raise ValueError(f"duplicate overhang {oh} at positions {i},{j}")

    recognition, spacer = RECOGNITION[enzyme]
    plan = []
    for i, part in enumerate(parts):
        left, right = used[i], used[i + 1]
        flanked = f"{recognition}{spacer}{left}{part['sequence']}{right}"
        plan.append({
            "name": part["name"], "left_overhang": left, "right_overhang": right,
            "part_length": len(part["sequence"]), "flanked_length": len(flanked),
        })
        print(f"Part {i + 1} ({part['name']}): "
              f"[{left}]--{len(part['sequence'])} bp--[{right}]")

    insert_bp = sum(len(p["sequence"]) for p in parts)
    print(f"{len(parts)} parts, ~{insert_bp} bp insert, "
          f"overhang path {' -> '.join(used)}")
    return plan
```

### Notes and failure modes

- **Enzyme identity is load-bearing.** BsaI (`GGTCTC`) and BsmBI/Esp3I
  (`CGTCTC`) have different recognition sequences and cut offsets — the overhang
  you actually get depends on both the enzyme and where its site sits relative
  to the part boundary. The `flanked` string above is a schematic layout, not a
  guarantee of the cut chemistry; confirm the cut offset for your enzyme.
- **Internal sites.** Every part must be *domesticated* — free of internal
  instances of the recognition site — or it will be cut mid-part. Scan each part
  for `recognition` and its reverse complement before ordering.
- **Overhang fidelity.** Beyond uniqueness, some overhang pairs misligate at
  measurable rates. For >4 parts, pick overhangs from a published high-fidelity
  set rather than the short default ladder here.

---

## 5. Gibson assembly (overlap-based)

Gibson (and the related HiFi / NEBuilder) joins fragments that share ~20–40 bp
of identical sequence at their ends. This function generates the tailed primers
that add those overlaps: each fragment's forward primer carries the tail of the
*previous* fragment, and its reverse primer carries the reverse complement of
the *next* fragment's start.

```python
from Bio.Seq import Seq
from Bio.SeqUtils import MeltingTemp as mt


def design_gibson_assembly(fragments, overlap_length=30, anneal=20):
    """Design overlap primers for a Gibson/HiFi assembly.

    fragments: list of {'name': str, 'sequence': str} in assembly order.
               Treated as circular (last fragment overlaps the first).
    overlap_length: homology arm length (20-40 bp typical).
    anneal: template-binding length of each primer (Tm is computed on this part).
    """
    plan = []
    n = len(fragments)
    for i in range(n):
        cur = fragments[i]
        nxt = fragments[(i + 1) % n]
        prev = fragments[(i - 1) % n]

        # Forward: [tail = end of previous fragment] + [anneal to start of cur]
        fwd_tail = "" if i == 0 else prev["sequence"][-overlap_length:]
        fwd_primer = fwd_tail + cur["sequence"][:anneal]

        # Reverse: [tail = RC of next fragment start] + [RC anneal to end of cur]
        rev_tail = str(Seq(nxt["sequence"][:overlap_length]).reverse_complement())
        rev_anneal = str(Seq(cur["sequence"][-anneal:]).reverse_complement())
        rev_primer = rev_tail + rev_anneal

        fwd_tm = mt.Tm_NN(Seq(cur["sequence"][:anneal]))
        rev_tm = mt.Tm_NN(Seq(cur["sequence"][-anneal:]))
        plan.append({
            "fragment": cur["name"], "fragment_length": len(cur["sequence"]),
            "fwd_primer": fwd_primer, "rev_primer": rev_primer,
            "fwd_tm": fwd_tm, "rev_tm": rev_tm, "overlap_length": overlap_length,
        })
        print(f"{cur['name']} ({len(cur['sequence'])} bp): "
              f"fwd {len(fwd_primer)} nt Tm {fwd_tm:.1f} | "
              f"rev {len(rev_primer)} nt Tm {rev_tm:.1f}")

    print(f"~{sum(len(f['sequence']) for f in fragments)} bp assembled (circular)")
    return plan
```

### Notes and failure modes

- **Overlap length.** 20–40 bp is the sweet spot: too short and junctions fail,
  too long and primers get expensive and prone to secondary structure. Aim for
  similar Tm at each junction overlap.
- **Linear vs circular product.** The function above wraps (last fragment joins
  the first), which is what you want when the last fragment is the vector
  backbone. For a linear product, drop the wrap on the terminal fragments.
- **Repeated sequences** anywhere in the assembly can cause mis-annealing; unique
  junction sequences are essential.
- **Minimum two fragments.** With one fragment there is nothing to overlap.
