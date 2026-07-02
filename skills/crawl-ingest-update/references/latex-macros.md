# LaTeX macro expansion table

The canonicalizer (`scripts/canonicalize.py`) expands a small set of shorthand
macros **before** parsing display math through `pylatexenc` →
`latex2sympy2_extended` → `SymPy.srepr`. Expansion collapses notational variants
so two papers writing `\R` and `\mathbb{R}` canonicalize to the same `srepr`.

Expansion never touches the stored markdown — display math stays byte-for-byte.
The expanded form is used only to compute the canonical `srepr` sidecar.

## Default table

These defaults live in `DEFAULT_MACROS` inside `scripts/canonicalize.py`. Keep
the two in sync if you edit either.

| Macro         | Expansion                              | Group          |
| ------------- | -------------------------------------- | -------------- |
| `\R`          | `\mathbb{R}`                           | Number sets    |
| `\N`          | `\mathbb{N}`                           | Number sets    |
| `\Z`          | `\mathbb{Z}`                           | Number sets    |
| `\Q`          | `\mathbb{Q}`                           | Number sets    |
| `\C`          | `\mathbb{C}`                           | Number sets    |
| `\Rplus`      | `\mathbb{R}_{+}`                        | Number sets    |
| `\dd`         | `\mathrm{d}`                           | Differentials  |
| `\partial_t`  | `\frac{\partial}{\partial t}`          | Differentials  |
| `\partial_x`  | `\frac{\partial}{\partial x}`          | Differentials  |
| `\E`          | `\mathbb{E}`                           | Operators      |
| `\Var`        | `\text{Var}`                           | Operators      |
| `\Cov`        | `\text{Cov}`                           | Operators      |

## Substitution rules

- Only standalone macros are expanded — a macro is matched when it is **not**
  followed by another letter (`\Rate` is left intact even though it starts with
  `\R`). See `expand_macros()` in `scripts/canonicalize.py`.
- Unknown / author-defined macros are left untouched. If `pylatexenc` then fails
  to parse, the equation yields `canonical_srepr: null` rather than an
  exception — the equation is kept as-is.

## Adding macros

Pass a YAML override file to the canonicalizer; it is merged on top of the
defaults (overrides win):

```bash
python scripts/canonicalize.py 01-raw/<sha256>-<slug>.md --macros my-macros.yaml
```

```yaml
# my-macros.yaml — keys are the macro, values the LaTeX expansion
\\foo: \\bar
\\Ind: \\mathbf{1}
```

Per-vault defaults can also be declared in the brain config frontmatter
(`latex_macros:` block) and rendered into a YAML file for the `--macros` flag.

See `references/latex-canonicalization.md` for the full canonicalization
contract this table feeds into.
