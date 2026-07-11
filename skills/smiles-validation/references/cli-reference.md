# `validate.py` CLI Reference

The bundled `scripts/validate.py` exposes the three checks (validate, compare,
verify) plus a batch mode. It prints a human-readable summary to stdout and,
with `--output`, writes the full structured result as JSON.

## Flags

| Flag                   | Type   | Meaning                                                        |
| ---------------------- | ------ | ------------------------------------------------------------- |
| `--smiles`             | str    | Single SMILES to validate.                                    |
| `--original`           | str    | Original SMILES (comparison / modification baseline).         |
| `--proposed`           | str    | Proposed / edited SMILES to compare against `--original`.     |
| `--check-modification` | str    | Natural-language claim about the edit to verify.              |
| `--input`              | path   | CSV of SMILES for batch validation.                           |
| `--smiles-col`         | str    | Column name in the CSV (default `SMILES`).                    |
| `--output`            | path   | Write full JSON result here (all modes).                      |

Mode is selected by which flags are present: `--smiles` → validate;
`--original` + `--proposed` → compare (add `--check-modification` to also
verify); `--input` → batch. `--check-modification` requires both `--original`
and `--proposed`.

## Output schemas

### validate

```json
{
  "smiles": "c1ccccc1",
  "valid": true,
  "issues": [],
  "canonical": "c1ccccc1",
  "num_atoms": 6,
  "num_heavy_atoms": 6,
  "mw": 78.1,
  "formula": "C6H6"
}
```

`valid` is `true` only when RDKit parses **and** sanitizes the string. When
`false`, `canonical`/`num_atoms`/… are absent and `issues` explains why
(`RDKit parse failure`, `Sanitization error: <msg>`, unbalanced brackets, etc.).
On a valid molecule, `issues` may still carry advisory warnings (tiny/huge
molecule, `MW > 1000`).

### compare

```json
{
  "tanimoto": 0.1667,
  "scaffold_preserved": true,
  "mcs_atoms": 6,
  "atom_delta": 1,
  "classification": "de_novo_design"
}
```

- `scaffold_preserved` — `true`/`false` from comparing generic Murcko
  scaffolds, or `null` when a scaffold could not be derived (e.g. acyclic).
- `mcs_atoms` — atom count of the maximum common substructure (0 if none or if
  the 10 s MCS timeout fired).
- `atom_delta` — `proposed.GetNumAtoms() - original.GetNumAtoms()` (heavy +
  explicit atoms).

### Classification thresholds

| Tanimoto (Morgan r=2, 2048 bits) | `classification`           | Reading                          |
| -------------------------------- | -------------------------- | -------------------------------- |
| >= 0.6                           | `lead_optimization`        | Same series, decorated core.     |
| 0.4 - 0.6                        | `significant_modification` | Core partly changed.             |
| < 0.4                            | `de_novo_design`           | Effectively a new molecule.      |

These cutoffs are heuristics tuned for medicinal-chemistry triage, not hard
truths — treat a value near a boundary as ambiguous and inspect the scaffold
and MCS as corroborating evidence.

### modification

```json
{
  "claim": "Added hydroxyl group",
  "checks": [{"group": "hydroxyl", "expected": "added", "passed": true}],
  "verified": true,
  "note": null
}
```

`verified` is `true` only if every mapped check passed, `false` if any failed,
and `null` (`INCONCLUSIVE`, with a `note`) when no structural check maps to the
claim's wording.

### batch

`--input` produces a JSON array of `validate` results (one per row) and prints
a `validated N: X valid, Y invalid` tally.

## Modification verification logic

The claim string is lowercased and scanned for group keywords and a direction
verb:

- **Direction** — `add`/`introduc`/`insert` → expect the group present in the
  proposed and absent in the original; `remov`/`delet` → present in original,
  absent in proposed; `replac` → present in proposed; otherwise → present.
- **Group** — matched by keyword to a SMARTS/SMILES query:

| Keywords                       | Query pattern         |
| ------------------------------ | --------------------- |
| hydroxyl, oh, hydroxy          | `[OH]`                |
| fluorine, fluoro, f            | `[F]`                 |
| chlorine, chloro, cl           | `[Cl]`                |
| bromine, bromo, br             | `[Br]`                |
| amine, amino, nh2              | `[NH2]`               |
| methyl, ch3                    | `[CH3]`               |
| nitro, no2                     | `[N+](=O)[O-]`        |
| cyano, nitrile, cn             | `C#N`                 |
| pyridine                       | `c1ccncc1`            |
| piperazine                     | `C1CNCCN1`            |
| morpholine                     | `C1COCCN1`            |

This is a deliberately small, high-precision keyword table: it verifies the
common single-group edits an optimization loop makes. A claim it does not
recognize returns `INCONCLUSIVE` rather than a false pass — that is the
intended conservative behavior, not a bug. Extend the table for domains with
other recurring motifs, and remember short keys like `f`/`cl`/`cn` can match
inside unrelated words, so keep claim strings specific.

## Failure modes and troubleshooting

- **`Error: rdkit ... required`** — install RDKit: `pip install rdkit` (the
  legacy `rdkit-pypi` package is unmaintained; do not use it).
- **Batch mode `ModuleNotFoundError: pandas`** — `pip install pandas`.
- **Wrong CSV column** — pass `--smiles-col <name>`; the default is `SMILES`.
- **A modification check unexpectedly `INCONCLUSIVE`** — the claim wording did
  not hit the keyword table; rephrase using a listed keyword or add the motif.
- **`scaffold_preserved: null`** — one molecule is acyclic or otherwise has no
  Murcko scaffold; rely on Tanimoto and MCS instead.
- **`mcs_atoms: 0` on clearly related molecules** — the 10 s MCS timeout likely
  fired on a large/symmetric pair; raise the timeout in the script if you need
  the exact core.
- **Everything looks valid but a downstream tool rejects it** — compare
  canonical SMILES; the two tools may perceive aromaticity or tautomers
  differently. See the gotchas in `rdkit-api.md`.
