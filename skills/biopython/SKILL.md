---
name: biopython
version: 0.1.0
description: >-
  Biopython (the `Bio.*` packages) is the general-purpose computational
  molecular biology toolkit for Python. Use it to manipulate DNA/RNA/protein
  sequences; read, write, and convert bioinformatics file formats (FASTA, FASTQ,
  GenBank, EMBL, PDB, mmCIF, Clustal, PHYLIP, Newick); query NCBI Entrez
  (PubMed, Nucleotide, Protein, Gene, Taxonomy); run and parse BLAST; align
  sequences with PairwiseAligner and substitution matrices; analyze 3D
  macromolecular structures with Bio.PDB; build and draw phylogenetic trees
  with Bio.Phylo; and compute sequence statistics (GC, Tm,
  molecular weight, motifs, restriction sites, codon usage). Reach for it when
  you need scriptable, low-level control or batch pipelines over raw biological
  data. NOT for quick one-off gene/accession lookups (use `gget`), for unified
  access to many bioinformatics web services at once (use `bioservices`), for
  single-cell / omics count matrices (use `scanpy` / `anndata`), or for reading
  SAM/BAM/VCF alignment files (use `pysam`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Biopython License Agreement (MIT-style) / BSD-3-Clause"
---

# Biopython: Computational Molecular Biology

## Overview

Biopython is a mature, freely available collection of Python tools for
biological computation, organized into task-specific sub-packages under the
`Bio` namespace. This skill is a **router**: it gives you the setup path, a
capability map with one-line quick-starts, and the non-obvious failure modes,
then delegates deep API surface and worked examples to `references/`.

The mental model: almost every workflow is **parse a file or fetch a record into
an object** (`Seq`, `SeqRecord`, `MultipleSeqAlignment`, `Structure`, `Tree`),
**inspect or transform that object**, then **write it back out** in some format.
Learn the object model once and each sub-package reads the same way.

Target version is Biopython 1.85 (Jan 2025), Python 3, requires NumPy.

## When to Use This Skill

Trigger when the user wants to:

- Work with biological sequences — translate, transcribe, reverse-complement,
  slice, or annotate DNA/RNA/protein.
- Read, write, or convert sequence/alignment/tree/structure file formats.
- Access NCBI databases programmatically (search, fetch, link, batch download).
- Run BLAST (web or local) and filter/parse the hits.
- Align sequences (pairwise global/local, or read multiple-sequence alignments).
- Parse and analyze PDB/mmCIF structures (distances, angles, DSSP, RMSD).
- Build or manipulate phylogenetic trees from alignments or distance matrices.
- Compute sequence stats: GC content, melting temperature, molecular weight,
  motifs/PWMs, restriction sites, ORFs, codon usage.
- Build a **custom, scriptable bioinformatics pipeline** stitching several of
  the above together.

## When NOT to Use This Skill

- **Quick one-off lookups** ("give me the sequence for BRCA1", "what is this
  Ensembl ID") — a thin wrapper like `gget` is faster and needs no boilerplate.
- **Fanning out across many web services** (UniProt + KEGG + Ensembl + ...) in
  one call — use `bioservices`.
- **Single-cell / bulk omics count matrices, embeddings, differential
  expression** — use `scanpy`, `anndata`, or `scikit-bio` for ecology/ordination.
- **Reading high-throughput alignment files** (SAM/BAM/CRAM/VCF/tabix) — use
  `pysam`; Biopython is not built for indexed read pileups at scale.
- **Deprecated command-line wrappers.** The old `Bio.*.Applications` classes
  (`ClustalOmegaCommandline`, `NcbiblastnCommandline`, etc.) were removed. Call
  external tools with `subprocess` instead — see `references/alignment.md`.

## Setup

```python
# Install (NumPy is pulled in as a dependency)
uv pip install biopython

# For ANY NCBI Entrez access, identify yourself — NCBI requires it:
from Bio import Entrez
Entrez.email = "you@example.com"      # required
Entrez.api_key = "..."                # optional: raises 3 -> 10 req/s
```

Biopython throttles Entrez requests to NCBI's limits automatically; you do not
add your own `sleep()` between calls.

## Capability Map

Each capability below has a deep reference. Read the reference before writing
non-trivial code — the quick-starts are orientation, not full API.

### 1. Sequences & file I/O — `Bio.Seq`, `Bio.SeqIO` → `references/sequence-io.md`

Create/transform sequences and stream records in any format.

```python
from Bio import SeqIO
for record in SeqIO.parse("in.fasta", "fasta"):
    print(record.id, len(record.seq), record.seq.translate(to_stop=True))
SeqIO.convert("in.gb", "genbank", "out.fasta", "fasta")
```

Covers: `Seq` methods, `SeqRecord`, format strings, memory-efficient
`index`/`index_db`, low-level FASTA/FASTQ parsers, gzip/BGZF, quality filtering.

### 2. Alignment — `Bio.Align`, `Bio.AlignIO` → `references/alignment.md`

Pairwise alignment and reading/writing multiple-sequence alignments.

```python
from Bio import Align
aligner = Align.PairwiseAligner(mode="local")
aligner.substitution_matrix = Align.substitution_matrices.load("BLOSUM62")
best = aligner.align("KEVLA", "KSVLA")[0]
```

Covers: scoring/gap params, substitution matrices, `AlignIO` formats,
consensus/PSSM, and how to shell out to Clustal/MUSCLE now that the wrappers
are gone.

### 3. NCBI databases — `Bio.Entrez` → `references/entrez.md`

Search and fetch across PubMed, Nucleotide, Protein, Gene, Taxonomy, etc.

```python
h = Entrez.efetch(db="nucleotide", id="EU490707", rettype="gb", retmode="text")
record = SeqIO.read(h, "genbank"); h.close()
```

Covers: `einfo/esearch/esummary/efetch/elink/epost/egquery/espell`, `rettype`
tables, WebEnv history for large batch downloads, XML parsing, error handling.

### 4. BLAST — `Bio.Blast` → `references/blast.md`

Run web/local BLAST and parse hits by E-value and identity.

```python
from Bio.Blast import NCBIWWW, NCBIXML
rec = NCBIXML.read(NCBIWWW.qblast("blastn", "nt", "ATCGATCGATCG"))
for a in rec.alignments[:5]:
    print(a.title, a.hsps[0].expect)
```

Covers: programs/databases, `qblast` params, HSP fields, local BLAST via
`subprocess`, tabular `outfmt 6`, best-hit/ortholog patterns.

### 5. Structures — `Bio.PDB` → `references/structure.md`

Parse PDB/mmCIF and query the SMCRA hierarchy.

```python
from Bio.PDB import PDBParser
s = PDBParser(QUIET=True).get_structure("1crn", "1crn.pdb")
d = s[0]["A"][10]["CA"] - s[0]["A"][20]["CA"]   # distance in Å
```

Covers: SMCRA navigation, coordinates/B-factors, distances/angles/dihedrals,
DSSP, `NeighborSearch`, `Superimposer`/RMSD, writing, sequence-from-structure.

### 6. Phylogenetics — `Bio.Phylo` → `references/phylogenetics.md`

Read/build/manipulate/draw trees.

```python
from Bio import Phylo
tree = Phylo.read("tree.nwk", "newick")
Phylo.draw_ascii(tree)
```

Covers: Newick/NEXUS/phyloXML, traversal, distances, pruning/rerooting,
`DistanceTreeConstructor` (UPGMA/NJ), consensus, matplotlib rendering.

### 7. Sequence analysis & utilities → `references/seq-analysis.md`

Motifs, `SeqUtils`, restriction, codon tables, population genetics.

```python
from Bio.SeqUtils import gc_fraction, MeltingTemp as mt
from Bio.Seq import Seq
print(gc_fraction(Seq("ATCGATCG")), mt.Tm_NN(Seq("ATCGATCGATCG")))
```

Covers: `Bio.motifs` (PWM/PSSM/consensus), GC/Tm/MW, `ProteinAnalysis`,
`Bio.Restriction`, `CodonTable`, ORF finding, `Bio.PopGen`, `SeqFeature`.

## Cross-Cutting Guidance

- **Iterate, don't slurp.** For large files use `SeqIO.parse` (an iterator) or
  `SeqIO.index`/`index_db`; never `list()` a multi-GB FASTA.
- **Format strings are lowercase** — `"fasta"`, `"genbank"`, `"fastq"`,
  `"clustal"`, `"phylip"`, `"newick"`. A wrong format string is the most common
  cause of `ValueError`/`EOF` on parse.
- **Close handles** from `Entrez.*` / `open()` or use `with`.
- **Cache network results locally.** Don't re-fetch the same accession or re-run
  the same BLAST; save the record/XML and reparse.
- **Copy before mutating trees/structures** (`tree.copy()`) — operations like
  `prune`, `ladderize`, `root_*` modify in place.
- **`Bio.pairwise2` and all `Bio.*.Applications` wrappers are deprecated/removed.**
  Use `Bio.Align.PairwiseAligner` and `subprocess` respectively.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ValueError` / `EOF` on parse | Format string does not match file; verify it. |
| `HTTP Error 400` from Entrez | Bad/invalid accession or missing `Entrez.email`. |
| PDB parser floods warnings | Use `PDBParser(QUIET=True)`; check structure quality. |
| Alignment "not same length" | Sequences must already be aligned for `AlignIO`/`MultipleSeqAlignment`. |
| BLAST is slow / rate-limited | Cache results; use local BLAST for bulk. |
| `ImportError` on `*Commandline` | Wrappers removed — shell out via `subprocess`. |

## Additional Resources

- Docs & tutorial: https://biopython.org/docs/latest/
- Source: https://github.com/biopython/biopython
