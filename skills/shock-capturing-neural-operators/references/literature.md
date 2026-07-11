# Beyond FNO: representations that handle discontinuities

The interventions in this skill harden an FNO but keep its truncated-Fourier
core, so a high-band error floor remains on truly sharp shocks. When the
per-band diagnostic in [diagnostics.md](diagnostics.md) shows high-band error
refusing to fall, the representation itself is the ceiling. These directions
attack the discontinuity more fundamentally — annotated so you can choose the
next step rather than tune the current one forever.

| Approach | Reference | Why it helps with shocks |
|---|---|---|
| Wavelet Neural Operator (WNO) | Tripura & Chakraborty, 2022 | Wavelet bases are localized in space *and* scale, so a jump is a few large coefficients instead of a slowly decaying Fourier tail — natural for discontinuities |
| Fourier Continuation operators (FC-PINO) | arXiv:2211.15960 | Polynomial continuation into a periodic extension domain gives a principled non-periodic boundary treatment; strictly better than reflection padding when implemented well |
| Convolutional Neural Operator (CNO) | Raonic et al., NeurIPS 2023 | Drops the spectral assumption entirely; band-limited convolutions with proper up/down-sampling avoid Gibbs by construction |
| Godunov / entropy-satisfying losses | arXiv:2405.11674 | Bakes the entropy condition and Rankine-Hugoniot jump relations into the loss so the operator learns *physical* shocks, not just least-squares fits |
| DCT/DST spectral bases | arXiv:2507.21757 | Cosine/sine transforms encode Neumann/Dirichlet boundaries directly, replacing the FFT's periodicity assumption for non-periodic domains |

Practical order of escalation:
1. Exhaust the in-skill interventions first (gated block, reflection padding,
   resolution, H1 + frequency loss). They are cheap and often enough for
   moderate viscosity.
2. If high-band error persists on genuinely sharp fronts, try a **CNO** or
   **WNO** — a different representation, not a patched FNO.
3. If boundaries are the dominant error source, move from reflection padding to
   **Fourier Continuation** or a **DCT/DST** basis.
4. If the operator produces non-physical (entropy-violating) shocks — wrong
   shock speed, spurious expansion shocks — add a **Godunov / entropy** loss
   term regardless of backbone.

All of these are research-grade; none is a drop-in replacement for the FNO
workflow in `neural-operator`. Prototype on a single well-understood Riemann
problem before committing a full training pipeline to a new backbone.
