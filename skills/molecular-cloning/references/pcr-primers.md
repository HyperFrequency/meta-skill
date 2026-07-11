# PCR Amplicon Prediction & Primer Design

Covers capability 1 (`simulate_pcr`) and capability 2 (`design_primers`). PCR
simulation needs only Biopython; primer design needs `primer3-py`.

---

## 1. PCR amplicon prediction

The model: find every place each primer can bind (allowing a few mismatches),
then pair a forward-strand binding of the forward primer with a
reverse-strand binding of the reverse primer that sits downstream, and report
the span between them as a candidate amplicon.

Two things to get right:

- The **reverse primer is given 5'→3' as ordered**. It anneals to the sense
  strand, so before searching you reverse-complement it and look for that
  sequence on the forward strand.
- Allowing mismatches (`max_mismatches`) surfaces **off-target products** —
  useful, because a primer pair that yields one clean band in silico but three
  when you allow 2 mismatches is a warning about specificity.

```python
from Bio.Seq import Seq
from Bio.SeqUtils import MeltingTemp as mt


def find_primer_binding(template, primer, max_mismatches=2):
    """Return [(position, strand, mismatches), ...] for a primer on both strands.

    position is a 0-based index into the forward strand of `template`.
    A hit on '-' means the primer sequence matches the reverse-complement
    strand at that forward-strand coordinate.
    """
    template_str = str(template).upper()
    primer_str = str(primer).upper()
    rc_template = str(template.reverse_complement()).upper()
    plen = len(primer_str)

    sites = []
    # Forward strand
    for i in range(len(template_str) - plen + 1):
        mismatches = sum(a != b for a, b in zip(primer_str, template_str[i:i + plen]))
        if mismatches <= max_mismatches:
            sites.append((i, "+", mismatches))
    # Reverse strand (search the RC, then translate back to fwd coordinates)
    for i in range(len(rc_template) - plen + 1):
        mismatches = sum(a != b for a, b in zip(primer_str, rc_template[i:i + plen]))
        if mismatches <= max_mismatches:
            pos = len(template_str) - i - plen
            sites.append((pos, "-", mismatches))
    return sites


def simulate_pcr(template, fwd_primer, rev_primer, max_mismatches=2,
                 min_len=50, max_len=10000):
    """Predict amplicons for a primer pair on a template.

    fwd_primer / rev_primer are Bio.Seq, both given 5'->3' as ordered.
    Returns a list of amplicon dicts, sorted implicitly by discovery order.
    """
    fwd_sites = find_primer_binding(template, fwd_primer, max_mismatches)
    rev_rc = Seq(str(rev_primer)).reverse_complement()
    rev_sites = find_primer_binding(template, rev_rc, max_mismatches)

    amplicons = []
    for f_pos, f_strand, f_mm in fwd_sites:
        if f_strand != "+":
            continue
        for r_pos, r_strand, r_mm in rev_sites:
            if r_strand != "-":
                continue
            if r_pos <= f_pos:
                continue
            end = r_pos + len(str(rev_primer))
            amp_len = end - f_pos
            if min_len < amp_len < max_len:
                amplicons.append({
                    "start": f_pos, "end": end, "length": amp_len,
                    "fwd_mismatches": f_mm, "rev_mismatches": r_mm,
                    "sequence": str(template[f_pos:end]),
                })

    fwd_tm = mt.Tm_NN(fwd_primer)
    rev_tm = mt.Tm_NN(rev_primer)
    print(f"Fwd Tm {fwd_tm:.1f} C | Rev Tm {rev_tm:.1f} C | "
          f"deltaTm {abs(fwd_tm - rev_tm):.1f} C")
    print(f"Predicted amplicons: {len(amplicons)}")
    for i, a in enumerate(amplicons, 1):
        print(f"  {i}: {a['length']} bp (pos {a['start']}-{a['end']}, "
              f"mm fwd={a['fwd_mismatches']} rev={a['rev_mismatches']})")
    return amplicons
```

### Notes and failure modes

- **No amplicon returned.** Usually primer orientation: the forward primer must
  match the sense strand 5'→3'. Increase `max_mismatches`, or confirm the target
  is actually present in the template.
- **`Tm_NN` needs a `Seq`, not a bare string.** Pass `Seq(...)`. Defaults assume
  nearest-neighbor thermodynamics at standard salt; for non-default Na⁺/Mg²⁺,
  pass `mt.Tm_NN(seq, Na=..., Mg=..., dNTPs=...)`.
- **Circular templates.** This linear scan does not wrap the origin. For a
  plasmid where the amplicon straddles position 0, duplicate the sequence
  (`template + template`) before searching and take hits in the first copy.
- **Cost.** The scan is O(len(template) × len(primer)) per primer. Fine for
  plasmids and short amplicons; for chromosome-scale templates, index first or
  use a real aligner.

---

## 2. PCR primer design with primer3

`primer3-py` wraps the Primer3 C library. The modern binding is
`primer3.bindings.design_primers(seq_args, global_args)` (older releases expose
`designPrimers` with the same argument shape — call whichever your installed
version provides).

```python
import primer3


def design_primers(template_seq, target_start, target_length,
                   product_size_range=(200, 500), tm_target=60, num_return=5):
    """Design ranked PCR primer pairs flanking a target region.

    template_seq: DNA string.
    target_start / target_length: the region the amplicon must contain (0-based).
    Returns a list of primer-pair dicts, best (lowest penalty) first.
    """
    result = primer3.bindings.design_primers(
        seq_args={
            "SEQUENCE_TEMPLATE": template_seq,
            "SEQUENCE_TARGET": [target_start, target_length],
        },
        global_args={
            "PRIMER_NUM_RETURN": num_return,
            "PRIMER_OPT_SIZE": 20,
            "PRIMER_MIN_SIZE": 18,
            "PRIMER_MAX_SIZE": 25,
            "PRIMER_OPT_TM": tm_target,
            "PRIMER_MIN_TM": tm_target - 5,
            "PRIMER_MAX_TM": tm_target + 5,
            "PRIMER_MIN_GC": 40,
            "PRIMER_MAX_GC": 60,
            "PRIMER_PRODUCT_SIZE_RANGE": [list(product_size_range)],
            "PRIMER_MAX_SELF_COMPLEMENT": 6,
            "PRIMER_MAX_SELF_END": 3,
            "PRIMER_MAX_HAIRPIN_TH": 47,
        },
    )

    pairs = []
    for i in range(result.get("PRIMER_PAIR_NUM_RETURNED", 0)):
        pair = {
            "left_seq":  result[f"PRIMER_LEFT_{i}_SEQUENCE"],
            "right_seq": result[f"PRIMER_RIGHT_{i}_SEQUENCE"],
            "left_tm":   result[f"PRIMER_LEFT_{i}_TM"],
            "right_tm":  result[f"PRIMER_RIGHT_{i}_TM"],
            "left_gc":   result[f"PRIMER_LEFT_{i}_GC_PERCENT"],
            "right_gc":  result[f"PRIMER_RIGHT_{i}_GC_PERCENT"],
            "product_size": result[f"PRIMER_PAIR_{i}_PRODUCT_SIZE"],
            "penalty":      result[f"PRIMER_PAIR_{i}_PENALTY"],
        }
        pairs.append(pair)
        print(f"Pair {i + 1}: {pair['product_size']} bp, "
              f"penalty {pair['penalty']:.2f}")
        print(f"  Fwd {pair['left_seq']}  (Tm {pair['left_tm']:.1f}, "
              f"GC {pair['left_gc']:.0f}%)")
        print(f"  Rev {pair['right_seq']}  (Tm {pair['right_tm']:.1f}, "
              f"GC {pair['right_gc']:.0f}%)")
    return pairs
```

### Key global_args knobs

| Key | Meaning | Typical |
|-----|---------|---------|
| `PRIMER_OPT_TM` / `PRIMER_MIN_TM` / `PRIMER_MAX_TM` | melting temperature window | 60 / 57 / 63 |
| `PRIMER_MIN_GC` / `PRIMER_MAX_GC` | GC% window | 40 / 60 |
| `PRIMER_OPT_SIZE` / `MIN` / `MAX` | primer length | 20 / 18 / 25 |
| `PRIMER_PRODUCT_SIZE_RANGE` | list of `[min, max]` spans | `[[200, 500]]` |
| `PRIMER_MAX_SELF_COMPLEMENT` / `_SELF_END` | dimer avoidance | 6 / 3 |
| `PRIMER_MAX_HAIRPIN_TH` | max hairpin Tm (°C) | 47 |
| `PRIMER_NUM_RETURN` | how many pairs to rank | 5 |

- **Returns no primers?** Constraints are too tight for the template. Widen the
  Tm range, raise `PRIMER_MAX_SIZE`, or loosen GC bounds. Ensure there is enough
  flanking sequence outside `SEQUENCE_TARGET` for primers to sit in.
- **Adding restriction/overhang tails** (e.g. a `GGATCC` BamHI site for
  downstream cloning): append the tail to the returned primer sequence — it does
  not anneal, so exclude it from the Tm the polymerase sees during early cycles.
- Rank by `penalty` (lower is better); it aggregates Tm, GC, size, and
  self/pair-complementarity deviations.
