# Running `.m` Scripts from Bash / CI

How to run MATLAB and GNU Octave non-interactively, pass arguments, capture
output, and set exit codes for automation.

## Quick comparison

| Task | MATLAB | Octave |
|---|---|---|
| Headless run (CI) | `matlab -batch "cmd"` | `octave --no-gui --eval "cmd"` |
| Run a script file | `matlab -batch "run('f.m')"` | `octave --no-gui f.m` |
| Exit with a code | `exit(n)` | `exit(n)` |
| Directly executable `.m` | uncommon | common (shebang) |

Check availability first: `matlab -help | head` (a valid license is required) or
`octave --version`.

## MATLAB

### Batch mode (preferred for automation)

`-batch` runs the command and returns a process exit code, then exits — no manual
`exit` needed.

```bash
matlab -batch "run('myscript.m')"
matlab -batch "cd('/path/to/project'); run('myscript.m')"
matlab -batch "myfunc(123, 'abc')"          # call a function directly
matlab -batch "disp(2+2)"                    # one-liner
```

### Legacy `-r`

Older pattern; you must include `exit` yourself or the process hangs:

```bash
matlab -nodisplay -nosplash -r "run('myscript.m'); exit"
```

### Paths and arguments

```bash
matlab -batch "addpath(genpath('/path/to/project')); myfunc()"
matlab -batch "myfunc(${N}, '${NAME}')"      # interpolate bash vars
```

If arguments contain quotes or spaces, set environment variables and read them
inside MATLAB (`getenv('NAME')`) rather than fighting shell quoting.

### Useful flags

`-batch "cmd"` (run + exit code), `-nodisplay` (headless), `-nodesktop`,
`-nosplash`, `-r "cmd"` (must self-`exit`). Availability varies by release; run
`matlab -help` for your version.

## GNU Octave

```bash
octave --quiet --no-gui myscript.m           # run a file and exit
octave --quiet --eval "disp(2+2)"            # one-liner
octave --quiet --eval "myfunc(123, 'abc')"   # call a function
octave --quiet --eval "addpath('/lib'); myfunc()"
```

Some servers need `--no-window-system` instead of `--no-gui`. `--persist` keeps
Octave open after running (the opposite of batch behavior).

### Shebang scripts (Octave)

```matlab
#!/usr/bin/env octave
disp("Hello from Octave");
```

```bash
chmod +x myscript.m
./myscript.m
```

The shebang line supports limited arguments across platforms; if you need
`--quiet`/`--no-gui`, use a wrapper shell script instead.

## Capturing output and exit codes

```bash
matlab -batch "run('myscript.m')" > run.out 2>&1 ; echo $?
octave --quiet --no-gui myscript.m > run.out 2>&1 ; echo $?
```

Force a non-zero exit on failure by wrapping the body — this is what makes a CI
step actually fail:

```matlab
try
    run('myscript.m');
catch ME
    disp(getReport(ME));   % full stack trace (MATLAB); ME.message on Octave
    exit(1);
end
exit(0);
```

```bash
matlab -batch "try, run('myscript.m'); catch ME, disp(getReport(ME)); exit(1); end; exit(0);"
octave --quiet --eval "try, run('myscript.m'); catch e, disp(e.message); exit(1); end; exit(0);"
```

## Portable runner (MATLAB, else Octave)

```bash
#!/usr/bin/env bash
set -euo pipefail

FILE="${1:?Usage: run_mfile.sh path/to/script.m [command]}"
CMD="${2:-}"

if command -v matlab >/dev/null 2>&1; then
    if [[ -n "$CMD" ]]; then matlab -batch "$CMD"
    else matlab -batch "run('${FILE}')"; fi
elif command -v octave >/dev/null 2>&1; then
    if [[ -n "$CMD" ]]; then octave --quiet --no-gui --eval "$CMD"
    else octave --quiet --no-gui "$FILE"; fi
else
    echo "Neither matlab nor octave on PATH" >&2
    exit 127
fi
```

## Troubleshooting

- **`matlab: command not found`** — invoke by full path, e.g.
  `/Applications/MATLAB_R2024b.app/bin/matlab -batch "disp('ok')"`, or add it to
  `PATH`.
- **GUI errors on a headless server (Octave)** — add `--no-gui` or
  `--no-window-system`; graphics still export to file.
- **Relative-path failures** — `cd` into the script's directory first, or
  `cd(...)` inside before `run(...)`.
- **Quoting problems in `-batch`/`--eval`** — pass complex inputs via environment
  variables and read them inside with `getenv`.
- **Diverges between MATLAB and Octave** — isolate with a minimal `--eval`/`-batch`
  repro; the usual cause is an unsupported toolbox call
  (see [octave-compatibility.md](octave-compatibility.md)).
