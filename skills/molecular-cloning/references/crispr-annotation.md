# CRISPR sgRNA Design & Plasmid Annotation

Covers capability 6 (`design_crispr_guides`) and capability 7
(`annotate_plasmid`). Biopython only.

---

## 6. CRISPR sgRNA design

Enumerate every protospacer adjacent to a PAM on both strands, then rank
candidates by a fast heuristic that encodes well-known design rules. For SpCas9
the PAM is `NGG` immediately 3' of a 20-nt protospacer.

> **Scope boundary.** This is a *design-rule filter*, not a validated on-target
> or off-target model. It does no genome alignment, so it cannot tell you a
> guide's genome-wide specificity. For production guides, feed the survivors to
> a genome-aware tool (Cas-OFFinder, CRISPOR) and an on-target model (Rule Set
> 2 / Azimuth, DeepCRISPR). Use this to shrink the candidate list, not to pick a
> final guide.

```python
from Bio.Seq import Seq
import re


def score_guide(guide_seq):
    """Heuristic 0-100 score from established sgRNA design rules (higher better)."""
    score = 50.0
    gc = (guide_seq.count("G") + guide_seq.count("C")) / len(guide_seq)
    if 0.4 <= gc <= 0.7:
        score += 10                     # favorable GC window
    elif gc < 0.3 or gc > 0.8:
        score -= 20                     # extreme GC hurts activity
    if "TTTT" in guide_seq:
        score -= 30                     # PolIII terminator: kills U6/H1 transcription
    if guide_seq[-1] == "G":
        score += 5                      # G adjacent to PAM is preferred
    if guide_seq[-2:] == "GG":
        score -= 5                      # can raise off-target rate
    rc = str(Seq(guide_seq).reverse_complement())
    if sum(a == b for a, b in zip(guide_seq, rc)) > 12:
        score -= 15                     # strong self-complementarity / hairpin
    return max(score, 0.0)


def design_crispr_guides(target_seq, pam="NGG", guide_length=20, top_n=10):
    """Enumerate and rank sgRNAs on both strands.

    target_seq: gene / exon / region string.
    pam: PAM pattern; 'N' = any base (regex-translated). SpCas9 = 'NGG'.
    Returns the top_n guide dicts, best score first.
    """
    seq = str(target_seq).upper()
    rc = str(Seq(seq).reverse_complement())
    pam_re = pam.replace("N", ".")
    plen = len(pam)

    guides = []
    for strand, s in (("+", seq), ("-", rc)):
        for i in range(len(s) - guide_length - plen + 1):
            pam_site = s[i + guide_length:i + guide_length + plen]
            if not re.match(pam_re, pam_site):
                continue
            guide = s[i:i + guide_length]
            pos = i if strand == "+" else len(seq) - i - guide_length
            guides.append({
                "sequence": guide, "pam": pam_site, "position": pos,
                "strand": strand, "score": score_guide(guide),
                "full_target": guide + pam_site,
            })

    guides.sort(key=lambda g: g["score"], reverse=True)
    print(f"{len(guides)} candidate guides; top {min(top_n, len(guides))}:")
    for i, g in enumerate(guides[:top_n], 1):
        print(f"  {i}. {g['sequence']} {g['pam']} "
              f"(strand {g['strand']}, pos {g['position']}, score {g['score']:.1f})")
    return guides[:top_n]
```

### Notes and failure modes

- **Too few candidates.** Widen the search region (whole gene, not one short
  exon). Try a relaxed PAM (`NAG` for SpCas9), or switch enzymes: Cas12a/Cpf1
  uses a 5' `TTTV` PAM and suits AT-rich targets. Adjust `pam` and note that
  Cas12a's protospacer is 3' of its PAM, not 5' — this function's PAM-after-guide
  layout assumes SpCas9-style geometry; for Cas12a, mirror the indexing.
- **PolIII terminators.** `TTTT` in the spacer terminates U6/H1 Pol III
  transcription — the scorer applies a heavy penalty; do not override it.
- **Editing-window strategy.** For knockouts, prefer guides in early, constitutive
  exons; for base/prime editing, position the edit within the enzyme's activity
  window relative to the PAM.

---

## 7. Plasmid annotation

Scan a plasmid for common features by sequence match, find ORFs above a length
threshold in all six frames, map unique restriction sites, and package it as a
`SeqRecord` you can write to GenBank.

```python
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.Restriction import Analysis, CommOnly
from Bio import SeqIO


COMMON_FEATURES = {
    "T7_promoter":   "TAATACGACTCACTATAG",
    "lac_operator":  "AATTGTGAGCGGATAACAATT",
    "RBS_consensus": "AAGGAG",
    "T7_terminator": "CTAGCATAACCCCTTGGGGCCTCTAAACGGGTCTTGAGG",
    "ColE1_origin":  "CCTGTTTTGGCGGATGAGAGAAG",
}


def annotate_plasmid(sequence, name="plasmid", min_orf_bp=300):
    """Annotate features, ORFs, and unique restriction sites; return a SeqRecord."""
    seq = Seq(sequence)
    record = SeqRecord(
        seq, id=name, name=name, description=f"{name} annotated",
        annotations={"molecule_type": "DNA", "topology": "circular"},
    )

    # Known features by exact match
    for label, pattern in COMMON_FEATURES.items():
        pos = str(seq).find(pattern)
        if pos >= 0:
            record.features.append(SeqFeature(
                FeatureLocation(pos, pos + len(pattern)),
                type="misc_feature", qualifiers={"label": label}))
            print(f"feature {label} @ {pos}")

    # Six-frame ORFs above threshold
    for strand, nuc in ((1, seq), (-1, seq.reverse_complement())):
        for frame in range(3):
            protein = str(nuc[frame:].translate())
            start = 0
            while True:
                start = protein.find("M", start)
                if start == -1:
                    break
                stop = protein.find("*", start)
                stop = len(protein) if stop == -1 else stop
                orf_bp = (stop - start) * 3
                if orf_bp >= min_orf_bp:
                    if strand == 1:
                        a, b = frame + start * 3, frame + stop * 3 + 3
                    else:
                        b = len(seq) - frame - start * 3
                        a = len(seq) - frame - stop * 3 - 3
                    record.features.append(SeqFeature(
                        FeatureLocation(min(a, b), max(a, b), strand),
                        type="CDS", qualifiers={"label": f"ORF_{orf_bp}bp"}))
                    print(f"ORF {orf_bp} bp @ {min(a, b)}-{max(a, b)} "
                          f"strand {'+' if strand == 1 else '-'}")
                start = stop + 1

    # Unique (single-cutter) restriction sites — the useful ones for cloning
    analysis = Analysis(CommOnly, seq, linear=False)
    unique = {str(e): s for e, s in analysis.full().items() if len(s) == 1}
    print(f"unique restriction sites: {len(unique)}")
    for enzyme, sites in sorted(unique.items()):
        print(f"  {enzyme}: {sites[0]}")

    return record


# Persist:
# record = annotate_plasmid(plasmid_seq, name="pMyPlasmid")
# SeqIO.write(record, "pMyPlasmid.gb", "genbank")
```

### Notes and failure modes

- **Exact-match features only.** `COMMON_FEATURES` finds literal sequences; real
  regulatory elements vary. For fuzzy/curated annotation, align against a feature
  database (e.g. the SnapGene / addgene common-feature set) or use a dedicated
  annotator. Extend the dict with your lab's standard parts.
- **ORF ≠ real gene.** A 300 bp open reading frame in an arbitrary frame is often
  spurious. Confirm the frame, look for a promoter/RBS upstream, and cross-check
  against a known CDS before trusting a called ORF.
- **Circular ORFs.** This scan does not wrap the origin; an ORF spanning position
  0 is missed. Rotate the sequence (or duplicate it) if the CDS crosses the
  origin.
- **Unique sites are the payload.** Single-cutter enzymes are what you use to
  linearize or insert; `len(sites) == 1` filters exactly those. Restrict to
  `CommOnly` so you only get enzymes you can actually buy.
