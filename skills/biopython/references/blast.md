# BLAST — `Bio.Blast`

Run BLAST against NCBI's web service or a local database, then parse the hits.

> **API note.** `Bio.Blast.NCBIWWW.qblast` + `Bio.Blast.NCBIXML` (shown here) are
> the long-established, widely-documented interface and still ship in Biopython
> 1.85. Recent releases also add a newer unified `Bio.Blast` module
> (`Bio.Blast.qblast`, `Bio.Blast.parse`/`read` over BLAST XML2). If you target
> the newest API, confirm its exact signatures against the installed version's
> docs rather than assuming — this file documents the interface that is stable
> across versions. The `Bio.Blast.Applications.*Commandline` wrappers were
> **removed**; run local BLAST via `subprocess`.

## Web BLAST via `NCBIWWW.qblast`

```python
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import SeqIO

record = SeqIO.read("query.fasta", "fasta")
result_handle = NCBIWWW.qblast("blastn", "nt", str(record.seq))

# Save before parsing — qblast is slow; never re-run just to re-read
with open("blast.xml", "w") as out:
    out.write(result_handle.read())
result_handle.close()
```

You can pass a raw sequence string, a FASTA string, or an accession/GI as the
third argument.

**Programs:** `blastn` (nt↔nt), `blastp` (prot↔prot), `blastx` (translated
nt→prot), `tblastn` (prot→translated nt), `tblastx` (translated↔translated).

**Databases:** nucleotide — `nt`, `refseq_rna`; protein — `nr`,
`refseq_protein`, `pdb`, `swissprot`.

**Useful `qblast` params:**

```python
NCBIWWW.qblast("blastn", "nt", seq,
    expect=0.001,        # E-value cutoff
    hitlist_size=50,     # max hits
    word_size=11,        # seed word size
    gapcosts="5 2",      # gap open/extend
    entrez_query="Mus musculus[Organism]",  # restrict search space
)
```

## Parsing XML with `NCBIXML`

```python
from Bio.Blast import NCBIXML

with open("blast.xml") as h:
    rec = NCBIXML.read(h)          # single query
# NCBIXML.parse(h) -> iterator, for multi-query XML
```

Record / alignment / HSP fields:

```python
rec.query, rec.query_length, rec.database
for aln in rec.alignments:              # one per subject hit
    print(aln.title, aln.accession, aln.length)
    for hsp in aln.hsps:                # high-scoring pairs within the hit
        hsp.expect          # E-value
        hsp.score, hsp.bits
        hsp.identities, hsp.align_length, hsp.gaps
        hsp.query_start, hsp.query_end, hsp.sbjct_start, hsp.sbjct_end
        hsp.query, hsp.match, hsp.sbjct   # the aligned strings
```

Filter by E-value and compute percent identity:

```python
E = 1e-3
for aln in rec.alignments:
    hsp = aln.hsps[0]
    if hsp.expect < E:
        pid = 100 * hsp.identities / hsp.align_length
        print(f"{aln.accession}: E={hsp.expect:.1e}, {pid:.1f}% id")
```

## Local BLAST via `subprocess`

Requires BLAST+ tools and a local database. Build a DB with `makeblastdb`, then
run and parse the XML:

```python
import subprocess
from Bio.Blast import NCBIXML

subprocess.run(["makeblastdb", "-in", "subjects.fasta", "-dbtype", "nucl",
                "-out", "mydb"], check=True)

subprocess.run(["blastn", "-query", "query.fasta", "-db", "mydb",
                "-evalue", "0.001", "-outfmt", "5", "-out", "hits.xml"],
               check=True)

with open("hits.xml") as h:
    rec = NCBIXML.read(h)
```

`-dbtype` is `nucl` or `prot`; the binaries are `blastn`, `blastp`, `blastx`,
`tblastn`, `tblastx`.

## Tabular output (`-outfmt 6` / `7`)

Fast to parse when you do not need alignment strings:

```python
subprocess.run(["blastn", "-query", "q.fasta", "-db", "mydb",
                "-outfmt", "6 qseqid sseqid pident length evalue bitscore",
                "-out", "hits.tsv"], check=True)

with open("hits.tsv") as f:
    for line in f:
        qid, sid, pident, length, evalue, bitscore = line.split("\t")
```

Default `outfmt 6` columns: qseqid sseqid pident length mismatch gapopen qstart
qend sstart send evalue bitscore.

## Patterns

**Top-N hits as dicts:**

```python
def best_hits(rec, n=10, e=1e-3):
    out = []
    for aln in rec.alignments[:n]:
        hsp = aln.hsps[0]
        if hsp.expect < e:
            out.append(dict(accession=aln.accession, title=aln.title,
                            e_value=hsp.expect,
                            pct_id=100*hsp.identities/hsp.align_length))
    return out
```

**Fetch hit sequences** (combine with `Bio.Entrez`, see `entrez.md`):

```python
from Bio import Entrez, SeqIO
Entrez.email = "you@example.com"
for aln in rec.alignments[:5]:
    h = Entrez.efetch(db="nucleotide", id=aln.accession,
                      rettype="fasta", retmode="text")
    print(SeqIO.read(h, "fasta").description); h.close()
```

## Gotchas

- Default E-value is 10 (very permissive) — set `expect`/`-evalue` to
  0.001–0.01 for meaningful hits.
- E-value alone is not identity; filter on both for orthology work.
- `aln.hsps` can hold several HSPs per subject; `hsps[0]` is the best.
- Web BLAST is rate-limited and can take minutes — cache the XML; for bulk use
  local BLAST or a faster aligner (e.g. DIAMOND) upstream.
- Wrap `qblast` in `try/except HTTPError` for transient NCBI failures.
