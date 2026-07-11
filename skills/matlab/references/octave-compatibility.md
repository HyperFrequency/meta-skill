# GNU Octave Compatibility

Octave runs the large majority of MATLAB `.m` code unchanged. The differences
below matter when you want a single source to run under both. When in doubt,
write to the intersection.

## Install and run

```bash
brew install octave          # macOS
sudo apt install octave      # Debian/Ubuntu
sudo dnf install octave      # Fedora

octave --gui                 # graphical
octave --no-gui script.m     # headless
octave --eval "disp('hi')"
octave-cli                   # pure command line, no graphics stack
```

## Syntax differences (write the compatible form)

| Topic | MATLAB / portable | Octave-only |
|---|---|---|
| Comment | `%` | `#` also works |
| Line continuation | `...` | `\` also works |
| Block end | `end` | `endif` / `endfor` / `endwhile` |
| Char array quote | `'text'` (no escapes) | `"text\n"` interprets escapes |
| Index after call | `t = f(x); t(1:10)` | `f(x)(1:10)` chaining allowed |
| Function def | in a `.m` file | may be defined on the command line |

Prefer single-quoted char arrays for portability; double-quoted strings differ
(MATLAB string objects since R2017a vs Octave escape interpretation).

## Operators Octave adds (avoid for portability)

```matlab
x++;   x--;   ++x;            % increment/decrement (not in MATLAB)
x += 5;   x -= 3;   x *= 2;   % compound assignment (not in MATLAB)
x .+= y;                      % element-wise compound
```

Write the explicit form instead: `x = x + 1;`.

Short-circuit note: in MATLAB, `&`/`|` also short-circuit inside `if`/`while`
conditions; in Octave only `&&`/`||` do. Use `&&`/`||` for scalar conditions and
`&`/`|` for element-wise logic to get identical behavior in both.

## Octave-only control constructs

```matlab
do                 % post-test loop; rewrite as a while loop for portability
    x = x + 1;
until (x > 10)

unwind_protect     % like try/finally; use try/catch + explicit cleanup instead
    risky();
unwind_protect_cleanup
    cleanup();
end_unwind_protect
```

## Detect the runtime

```matlab
function tf = isOctave()
    tf = exist('OCTAVE_VERSION', 'builtin') ~= 0;
end

if isOctave()
    % Octave-specific branch
else
    % MATLAB-specific branch
end
```

## File compatibility

Save MAT files as `-v7` (the default, compressed) or `-v6` for cross-tool
exchange. `-v7.3` uses HDF5 and has only partial Octave support. Basic
`save`/`load`/`dlmread`/`dlmwrite` behave the same in both.

## What Octave lacks

- **Simulink** — no equivalent; `.slx`/`.mdl` models will not run.
- **App Designer / GUIDE** — MATLAB GUI builders are absent; Octave has only
  basic `uicontrol`/`uimenu`.
- **Live scripts** — `.mlx` is MATLAB-only; use plain `.m`.
- **Many toolboxes** — some map to Octave Forge packages (below); others do not.
- **`classdef`** — supported but partial (some handle events, property
  validation, and access modifiers differ). Favor simpler OOP or struct-based
  designs for portable code.

## Octave packages

Toolbox functionality often lives in Octave Forge packages, which must be loaded
each session (or from `.octaverc`):

```matlab
pkg install -forge signal     % one-time install
pkg load signal               % load before use (per session)
pkg list                      % what is installed / loaded
pkg unload signal
```

Common package ↔ toolbox mapping:

| Octave Forge package | MATLAB toolbox |
|---|---|
| `control` | Control System |
| `signal` | Signal Processing |
| `image` | Image Processing |
| `statistics` | Statistics and Machine Learning |
| `optim` | Optimization |
| `symbolic` | Symbolic Math (wraps SymPy) |
| `parallel` | Parallel Computing |

## Testing both

```bash
matlab -batch "run('test_script.m')"
octave --no-gui test_script.m
```

Wrap the body in `try/catch` and print a clear pass/fail line so both runs are
diff-able.
