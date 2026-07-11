# Gene Circuit Simulation

Deterministic ODE models of the three canonical synthetic gene circuits, solved
with `scipy.integrate.solve_ivp`. Each gene contributes an mRNA equation and a
protein equation; regulation enters through Hill functions. All models carry a
degradation/dilution term so intracellular species decay as cells divide.

## Common structure

For a gene with mRNA `m` and protein `p`:

```
dm/dt = (regulated transcription) - delta_m * m
dp/dt = beta * m               - delta_p * p
```

- `delta_m`, `delta_p` — mRNA and protein degradation rates (protein is usually
  more stable: `delta_p < delta_m`).
- `beta` — translation rate; commonly set to `delta_p / delta_m` to
  non-dimensionalize.
- `alpha` / `alpha_max` — maximal transcription rate.
- `alpha0` — basal transcription (promoter leakiness).
- `n` — Hill coefficient (cooperativity); `K` — repression/activation threshold.
- Growth dilution `mu` is folded into the decay terms (`delta + mu`) or written
  explicitly as `+ gamma`. Never drop it — omitting dilution inflates steady
  states.

## Repressilator (3-gene ring oscillator)

Elowitz & Leibler ring: gene 1 is repressed by protein 3, gene 2 by protein 1,
gene 3 by protein 2. Six ODEs.

```python
def repressilator_odes(t, y, p):
    m1, m2, m3, p1, p2, p3 = y
    a0, a, n, K = p.get("alpha0", 0.03), p.get("alpha", 5.0), p.get("n", 2.0), p.get("K", 1.0)
    dm, dp = p.get("delta_m", 1.0), p.get("delta_p", 0.2)
    b = p.get("beta", dp / dm)
    h = lambda x: a / (1.0 + (x / K)**n) + a0        # Hill repression
    return [h(p3) - dm*m1, h(p1) - dm*m2, h(p2) - dm*m3,
            b*m1 - dp*p1, b*m2 - dp*p2, b*m3 - dp*p3]
```

Sustained oscillation requires strong repression (high `alpha`), cooperativity
(`n ≥ 2`), and tight protein/mRNA timescale separation. A good default initial
condition is asymmetric, e.g. `[0.5, 0.3, 0.1, 2.0, 1.0, 0.5]` — a symmetric
start can sit on the unstable fixed point.

## Toggle switch (2 mutually repressing genes)

Gardner–Cantor–Collins bistable switch. Four ODEs; gene 1 repressed by protein
2 and vice versa. Bistability needs cooperativity (`n > 1`) and comparable,
strong repression.

```python
def toggle_switch_odes(t, y, p):
    m1, m2, p1, p2 = y
    a1, a2 = p.get("alpha1", 6.0), p.get("alpha2", 6.0)
    n1, n2 = p.get("n1", 2.5), p.get("n2", 2.5)
    K1, K2 = p.get("K1", 1.0), p.get("K2", 1.0)
    dm, dp, a0 = p.get("delta_m", 1.0), p.get("delta_p", 0.2), p.get("alpha0", 0.03)
    b = p.get("beta", dp / dm)
    return [a1 / (1 + (p2/K2)**n2) + a0 - dm*m1,
            a2 / (1 + (p1/K1)**n1) + a0 - dm*m2,
            b*m1 - dp*p1, b*m2 - dp*p2]
```

## Inducible promoter (single gene, activated)

One gene whose transcription is activated by an inducer through a Hill function;
includes explicit growth dilution `mu`. Two ODEs.

```python
def inducible_odes(t, y, p):
    m, prot = y
    amax, Ki, n = p.get("alpha_max", 10.0), p.get("K_ind", 5.0), p.get("n", 2.0)
    ind = p.get("inducer", 0.0)
    dm, dp, mu, a0 = p.get("delta_m", 1.0), p.get("delta_p", 0.2), p.get("mu", 0.01), p.get("alpha0", 0.05)
    b = p.get("beta", dp / dm)
    act = amax * ind**n / (Ki**n + ind**n) + a0
    return [act - (dm + mu) * m, b*m - (dp + mu) * prot]
```

## Integration

Use non-default tolerances — these systems are moderately stiff near switching:

```python
import numpy as np
from scipy.integrate import solve_ivp

def simulate(func, y0, t_span, params):
    t_eval = np.linspace(t_span[0], t_span[1],
                         max(2000, int((t_span[1]-t_span[0]) * 20)))
    sol = solve_ivp(func, t_span, y0, args=(params,), t_eval=t_eval,
                    method="RK45", rtol=1e-8, atol=1e-10,
                    max_step=(t_span[1]-t_span[0]) / 500)
    if not sol.success:
        raise RuntimeError(f"integration failed: {sol.message}")
    return sol
```

If `RK45` stalls ("excess work done"), switch `method="BDF"` or `"Radau"`
(implicit, for stiff systems) before loosening tolerances. `max_step` caps step
size so fast transients are not skipped.

## Analysis readouts

**Oscillation period (repressilator).** Detect peaks on a protein trace and
average the last few inter-peak intervals (after transients settle):

```python
from scipy.signal import find_peaks

def estimate_period(t, signal, min_prominence=0.1):
    signal = np.asarray(signal)
    rng = signal.max() - signal.min()
    if rng < 1e-6:
        return None                                   # flat -> no oscillation
    peaks, _ = find_peaks(signal, prominence=max(min_prominence, 0.2*rng),
                          distance=len(t) // 50)
    if len(peaks) < 2:
        return None
    periods = np.diff(t[peaks])
    return float(np.mean(periods[-min(5, len(periods)):]))
```

**Toggle steady states.** Integrate to long time (`t_span = (0, 5000)`) from
many initial conditions; take the mean of the last ~50 points as the steady
state; deduplicate within a tolerance. Two distinct attractors ⇒ bistable. See
`bifurcation-analysis.md` for the convergence-checked finder used in sweeps.

**Inducible fold-induction.** Ratio of induced to basal steady-state protein:

```python
def fold_induction(params, inducer_conc):
    off = simulate(inducible_odes, [0, 0], (0, 2000), {**params, "inducer": 0.0})
    on  = simulate(inducible_odes, [0, 0], (0, 2000), {**params, "inducer": inducer_conc})
    basal   = float(np.mean(off.y[1, -100:]))
    induced = float(np.mean(on.y[1, -100:]))
    return float("inf") if basal < 1e-10 else induced / basal
```

Also useful: **time-to-90%** of steady state (`np.argmax(sol.y[1] >= 0.9*p_ss)`)
as a response-speed metric.

## Pitfalls

- **Symmetric toggle/repressilator initial conditions** land on unstable fixed
  points; perturb them to reveal the real attractor.
- **Negative concentrations** are numerical artifacts near zero — clamp with
  `max(0, x)` when reporting, and tighten `atol` if they are large.
- **Non-dimensional units.** Time and concentration are in arbitrary units
  unless you fix `delta_m` to a real rate; compare within a study, not across.
- A toggle that always ends in the same state regardless of start is
  **monostable** for those parameters — sweep repression strength to find the
  bistable window (`bifurcation-analysis.md`).
