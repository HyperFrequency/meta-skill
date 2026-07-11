# Datamol File I/O

Read and write molecular data across formats. `dm.read_csv` / `dm.read_excel` are
pandas-backed and return a DataFrame; **`dm.read_sdf` and `dm.read_smi` return a plain
list of `Mol` by default** (`as_df=False`). Pass `as_df=True` **and** a `mol_column`
name to those two to get a DataFrame with a molecule column. Most readers accept
`n_jobs` for parallel parsing and support remote paths through `fsspec`.

## Readers

| Function | Reads |
|---|---|
| `dm.read_sdf(path, sanitize=True, remove_hs=True, as_df=False, mol_column=None, n_jobs=1)` | SDF (Structure-Data File) — the most common chemistry exchange format. Default returns a `list[Mol]`; pass `as_df=True, mol_column="mol"` for a DataFrame where SDF tags become columns |
| `dm.read_smi(path, smiles_column="smiles", mol_column="mol", as_df=True)` | SMILES file (whitespace-delimited: SMILES then optional name/ID) |
| `dm.read_csv(path, smiles_column="smiles", mol_column=None)` | CSV; set `mol_column` to auto-build `Mol` objects from the SMILES column |
| `dm.read_excel(path, sheet_name=0, smiles_column="smiles", mol_column=None)` | Excel workbook |
| `dm.read_molblock(text)` | A single MOL block string |
| `dm.read_mol2file(path)` / `dm.read_pdbfile(path)` / `dm.read_pdbblock(text)` | Mol2 / PDB file / PDB block |
| `dm.open_df(path)` | Universal reader — auto-detects `.sdf`, `.csv`, `.xlsx`, `.parquet`, `.json` |

```python
mols = dm.read_sdf("compounds.sdf", n_jobs=-1)                        # default: a list of Mol
df   = dm.read_sdf("compounds.sdf", as_df=True, mol_column="mol")     # DataFrame with a "mol" column
mols = df["mol"].tolist()
```

## Writers

| Function | Writes |
|---|---|
| `dm.to_sdf(mols_or_df, path, mol_column=None)` | SDF from a list or a DataFrame (pass `mol_column` for a DataFrame) |
| `dm.to_smi(mols, path)` | SMILES file |
| `dm.to_xlsx(df, path, mol_columns=["mol"])` | Excel with molecules **rendered as images** in the named columns |
| `dm.to_molblock(mol)` / `dm.to_pdbblock(mol)` | MOL / PDB block string |
| `dm.save_df(df, path)` | Save DataFrame in CSV / Excel / Parquet / JSON (by extension) |

```python
dm.to_sdf(df, "clean.sdf", mol_column="mol")
dm.to_xlsx(df, "report.xlsx", mol_columns=["mol"])   # visual review file
```

## Remote Storage (fsspec)

Any path argument may be a remote URL; datamol streams it via `fsspec`. Install the
backend that matches the scheme:

| Scheme | Backend package |
|---|---|
| `s3://` | `s3fs` |
| `gs://` | `gcsfs` |
| `az://` / `abfs://` | `adlfs` |
| `http://` / `https://` | built in |

```python
df = dm.read_sdf("s3://my-bucket/library.sdf")
dm.to_sdf(mols, "gs://my-bucket/out/selected.sdf")
```

If the backend package is missing, the call raises a protocol/import error rather
than falling back to local — install it first.

## Common parameters

- `sanitize` (default `True`) — sanitize molecules on read.
- `remove_hs` (default `True`) — strip explicit hydrogens on read.
- `as_df` — DataFrame vs. list of molecules. DataFrame for `read_csv`/`read_excel`;
  **defaults to `False` (a list) for `read_sdf`/`read_smi`** — set `True` there.
- `n_jobs` — parallel parse (`-1` = all cores).
- `mol_column` / `smiles_column` — DataFrame column names.

Rows that fail to parse come back as `None` in the molecule column — filter with
`df = df[df["mol"].notna()]` before downstream steps.
