# Genomic Tokenizers

`gtars.tokenizers` converts genomic regions into discrete **tokens** against a
fixed vocabulary ("universe") of intervals — the preprocessing step for
region-embedding and transformer models on genomic data. This module is the
Rust core that the **geniml** library uses for tokenization.

> Signatures are illustrative — verify with `help(gtars.tokenizers)` on your
> installed version. The tokenizer types and constructor shapes have changed
> across releases; confirm before depending on a specific one.

## Concept

A tokenizer is defined by a **universe** of reference regions. Tokenizing a
query region maps it to the universe interval(s) it corresponds to (by overlap),
yielding token id(s). Consistency of the universe across train/eval is what makes
tokens comparable — always tokenize every split against the *same* universe.

`TreeTokenizer` uses an interval-tree index over the universe for fast lookups.

## Build a tokenizer

```python
from gtars.tokenizers import TreeTokenizer

tok = TreeTokenizer.from_bed_file("universe.bed")        # universe from BED
tok = TreeTokenizer.from_config("tokenizer_config.yaml") # from a config file
```

## Tokenize regions

```python
token  = tok.tokenize("chr1", 1000, 2000)                # one region
tokens = [tok.tokenize(c, s, e) for (c, s, e) in regions] # batch

token.id                                                 # integer token id
token.chromosome, token.start, token.end                 # source coordinates
tok.vocab_size                                           # universe size
```

Prefer batch tokenization and pre-load the tokenizer once for repeated calls —
constructing it parses and indexes the whole universe.

## Handoff to geniml / a model

```python
from gtars.tokenizers import TreeTokenizer

tok    = TreeTokenizer.from_bed_file("universe.bed")
tokens = [tok.tokenize(r.chromosome, r.start, r.end) for r in region_set]

# Feed token ids into a geniml region-embedding model, or into your own
# embedding layer sized to tok.vocab_size. Train the model with the
# `transformers` / `pytorch-lightning` skills — gtars stops at tokenization.
```

## Configuration file

```yaml
# tokenizer_config.yaml
type: tree
resolution: 1000        # token resolution in base pairs
chromosomes: [chr1, chr2, chr3]
options:
  overlap_handling: merge
  gap_threshold: 100
```

## Gotchas

- **Universe drift.** Tokenizing different data splits against different
  universes makes ids incomparable. Freeze one universe and reuse it.
- **Out-of-universe regions.** A query that overlaps nothing in the universe
  maps to a special/unknown token (or none). Handle that case before feeding a
  model with a fixed embedding table.
- **Multi-overlap regions.** A query spanning several universe intervals may
  produce several tokens; know whether your model expects one token per region
  or a sequence.
- **Coordinate base** (0-based half-open BED) must match between universe and
  queries, or overlaps — and therefore tokens — shift.
