---
name: matlab
version: 0.1.0
description: >-
  MATLAB and GNU Octave numerical computing for matrix and linear-algebra work,
  signal/image processing, ODEs, optimization, statistics, and publication-grade
  scientific plots. Use when writing or debugging .m scripts, translating MATLAB
  to/from Python, choosing an ODE solver or matrix decomposition, running headless
  MATLAB/Octave in CI, or keeping code portable across both interpreters. Covers
  matrices/indexing, math (linear algebra, calculus, FFT, fitting), graphics,
  file and MAT-file I/O, functions/classes/error handling, the MATLAB Engine and
  py.* bridge, and Octave compatibility gotchas. NOT for symbolic-first CAS work
  (use SymPy/Mathematica), general-purpose application code, deep-learning training
  pipelines (use the Python ML skills), or pure-Python numerics where NumPy/SciPy
  already fit — reach for those instead.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MATLAB proprietary (MathWorks); GNU Octave GPL-3.0-or-later"
---

# MATLAB / Octave Scientific Computing

## Overview

MATLAB is a numerical-computing environment whose primitive data type is the
matrix; nearly every operation is vectorized over arrays. GNU Octave is a free,
GPL-licensed interpreter that runs the large majority of MATLAB `.m` code
unchanged. Write to the common subset and one script runs under either.

This SKILL is a router: it points you at the correct function family fast and
delegates exhaustive API tables, options, and extended examples to `references/`.
Reach for it to author scripts, pick the right solver or factorization, port
code to/from Python, run headless in CI, and stay portable across both runtimes.

## When to Use This Skill

- Writing or debugging MATLAB/Octave `.m` scripts for linear algebra, signal or
  image processing, ODEs/PDEs, optimization, statistics, or curve fitting.
- Producing publication-quality 2D/3D figures and exporting vector PDF/EPS/SVG.
- Choosing between solvers or decompositions (`ode45` vs `ode15s`;
  `lu`/`qr`/`chol`/`svd`; `\` vs `inv`).
- Translating code between MATLAB and Python in either direction, or calling one
  from the other. For cross-framework strategy ports see `strategy-translator`.
- Running MATLAB/Octave non-interactively from bash or CI and checking exit codes.
- Keeping a single script portable across MATLAB and Octave.

## When NOT to Use This Skill

- Symbolic-first computer-algebra work — prefer SymPy, Mathematica, or Maple
  (Octave's `symbolic` package is only a thin SymPy wrapper).
- Deep-learning training/serving — use the Python ML skills (`pytorch-lightning`,
  `transformers`, `scikit-learn`).
- General-purpose application, web, or systems code — MATLAB is a poor fit.
- Pure-Python numerics where NumPy/SciPy/`polars`/pandas already cover the need
  and there is no MATLAB dependency.
- Simulink models (`.slx`/`.mdl`) — no Octave equivalent and out of scope here.

## Running Scripts

```bash
# MATLAB, headless, deterministic exit code (preferred for CI)
matlab -batch "run('script.m')"

# MATLAB, older pattern (must include exit yourself)
matlab -nodisplay -nosplash -r "run('script.m'); exit"

# GNU Octave, headless
octave --quiet --no-gui script.m
octave --quiet --eval "disp(2+2)"
```

Install Octave: `brew install octave` (macOS), `sudo apt install octave`
(Debian/Ubuntu), or the installer from <https://octave.org/download>. Wrap the
body in `try/catch ... exit(1); end` so failures fail the pipeline. Batch flags,
argument passing, path handling, and a portable `matlab || octave` runner are in
[references/executing-scripts.md](references/executing-scripts.md).

## Matrices and Arrays

The core of everything. `A = [1 2; 3 4]` (rows by `;`), ranges `1:0.5:10`,
`linspace`/`logspace`, and constructors `zeros`/`ones`/`eye`/`rand`/`randn`.
Indexing is **1-based** and **column-major**: `A(2,:)`, `A(:,3)`, `A(end,:)`,
logical masks `A(A>5)`, and `find`. Distinguish element-wise (`.*`, `./`, `.^`)
from matrix (`*`, `^`, `\`) operators — this is the single most common bug.
Full coverage of creation, indexing, reshaping, concatenation, sorting, and set
operations: [references/matrices-arrays.md](references/matrices-arrays.md).

## Mathematics

- **Linear algebra**: solve `Ax=b` with `x = A\b` (never `inv(A)*b`);
  decompositions `lu`, `qr`, `chol`, `ldl`, `schur`, `svd`; eigenproblems `eig`
  and `eigs`; properties `rank`, `cond`, `norm`, `pinv`.
- **Calculus**: `integral`/`integral2`/`integral3`, `trapz`; `diff`, `gradient`.
- **ODEs**: `[t,y] = ode45(@(t,y) f, tspan, y0)`; switch to `ode15s`/`ode23s`
  for stiff systems; convert higher-order ODEs to first-order systems; `bvp4c`
  for boundary-value problems; tune with `odeset`.
- **Optimization/roots**: `fminbnd`, `fminsearch`, `fzero`, `roots`,
  `lsqnonlin`, `lsqcurvefit`.
- **Statistics**: `mean`/`median`/`std`/`var`, `corrcoef`, `cov`, `prctile`,
  `movmean` and friends, `histcounts`.
- **Signal processing**: `fft`/`ifft`/`fft2`, `fftshift`, `filter`, `filtfilt`,
  `conv`/`conv2`, `xcorr`.
- **Interpolation/fitting**: `interp1`/`interp2`/`interp3`, `polyfit`/`polyval`.

Solver-selection guidance, `linsolve` options, special functions, and
worked fits: [references/mathematics.md](references/mathematics.md).

## Graphics and Visualization

`plot`, `scatter`, `bar`, `histogram`, `errorbar`, log-axis variants
(`semilogy`/`loglog`); 3D via `plot3`, `surf`, `mesh`, `contour`/`contourf`,
`imagesc`, `quiver`. Compose with `figure`, `subplot`/`tiledlayout`,
`hold on`, `yyaxis`. Annotate with `title`/`xlabel`/`legend`/`colorbar`/`xline`.
Export publication figures with `exportgraphics(gcf,'fig.pdf','ContentType',
'vector')` (R2020a+) or `print -dpdf -painters`. Line/marker specs, colormaps,
LaTeX interpreter, and export options:
[references/graphics-visualization.md](references/graphics-visualization.md).

## Data Import / Export

Prefer the high-level readers: `readtable` (mixed types), `readmatrix`
(numeric), `readcell`; write with `writetable`/`writematrix`. Native `.mat`
files via `save`/`load` (use `matfile` for partial access to huge arrays);
images via `imread`/`imwrite`. Tables support `sortrows`, `groupsummary`,
`join`, and `T.Var` access. Excel ranges/sheets, low-level `fopen`/`fread`/
`fscanf`, and path helpers (`fullfile`, `fileparts`, `dir`):
[references/data-import-export.md](references/data-import-export.md).

## Programming

Functions live in `.m` files named after the function; scripts share the base
workspace. Use `arguments` blocks with validators (`mustBePositive`, ...) for
input checking, anonymous functions `f = @(x) ...`, `try/catch ME`, `error`/
`assert`/`warning`, `tic`/`toc` and `profile` for performance, and `parfor` for
embarrassingly parallel loops. `classdef` supports value vs `handle` semantics,
inheritance, and events. Control flow, OOP, and debugging (`dbstop`):
[references/programming.md](references/programming.md).

**Performance rules that matter most:** vectorize instead of looping
(`y = sin(x)` not a for-loop), and preallocate (`y = zeros(1,n)`) before any
loop that must remain.

## Python Integration

Call Python from MATLAB with the `py.` prefix (`py.numpy.array(...)`,
`py.importlib.import_module('sklearn.linear_model')`), keyword args via
`pyargs`, and run code with `pyrun`/`pyrunfile`; convert results back with
`double`/`char`/`cell`. Call MATLAB from Python with the MATLAB Engine API
(`import matlab.engine; eng = matlab.engine.start_matlab()`), passing
`matlab.double(...)` and using `nargout=`. Note numpy is row-major vs MATLAB
column-major — transpose where layout matters. Type-conversion tables,
iteration, error handling, and `scipy.io` MAT exchange:
[references/python-integration.md](references/python-integration.md).

## Octave Compatibility

Octave runs most MATLAB code, but for portability: use `%` (not `#`) comments,
`...` (not `\`) line continuation, `end` (not `endif`/`endfor`) terminators,
single-quoted char arrays, and intermediate variables (Octave allows
`f(x)(1:10)` chaining, MATLAB does not); avoid `x++`/`x+=`. Save MAT files as
`-v7` for cross-compatibility. Detect the runtime with
`exist('OCTAVE_VERSION','builtin')`. Octave toolboxes load via `pkg load signal`.
Missing pieces (Simulink, App Designer, some `classdef` features) and the
`pkg` system: [references/octave-compatibility.md](references/octave-compatibility.md).

## Reference Files

- [references/matrices-arrays.md](references/matrices-arrays.md) — creation, indexing, reshaping, sorting, sets.
- [references/mathematics.md](references/mathematics.md) — linear algebra, calculus, ODEs, optimization, stats, signals, fitting.
- [references/graphics-visualization.md](references/graphics-visualization.md) — 2D/3D plotting, customization, vector export.
- [references/data-import-export.md](references/data-import-export.md) — CSV/Excel/MAT/image I/O, tables, low-level file I/O.
- [references/programming.md](references/programming.md) — functions, control flow, errors, performance, OOP, debugging.
- [references/python-integration.md](references/python-integration.md) — `py.*` bridge and MATLAB Engine API.
- [references/octave-compatibility.md](references/octave-compatibility.md) — MATLAB vs Octave differences and packages.
- [references/executing-scripts.md](references/executing-scripts.md) — running `.m` from bash/CI, exit codes, portable runner.

## External Documentation

- MATLAB: <https://www.mathworks.com/help/matlab/>
- GNU Octave: <https://docs.octave.org/latest/>
