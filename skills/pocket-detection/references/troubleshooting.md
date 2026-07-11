# Troubleshooting

Symptoms you will actually hit, and the fix. The governing rule: **adjust the
method and its parameters — do not reinvent detection or scoring in ad-hoc
code.** A different `method` or one changed threshold fixes almost everything
here, and keeps the pocket record contract intact for the downstream docking
step.

## One giant pocket (> ~5000 Å³) or only a single pocket returned

The grid scan's clustering merged neighboring cavities. In order:

1. Switch to **auto** (uses P2Rank/fpocket if present — both separate sub-pockets
   better).
2. Try **fpocket** — alpha spheres naturally split sub-pockets.
3. Raise `min volume` toward 300 Å³ to drop noise, then re-run.
4. Restrict to the biologically relevant chain to exclude inter-chain cavities.

## No pockets detected

- The protein may genuinely lack a defined cavity (flat/PPI surface).
- Lower `min volume` toward ~100 Å³ and re-run.
- Verify preparation: an unstripped structure buried in solvent/heteroatoms, or a
  structure with no added hydrogens, can suppress detection.
- If it is truly featureless, hand the downstream step manual coordinates rather
  than forcing a false pocket.

## All druggability scores identical (or all > 0.9)

- The continuous 6-axis model separates similar pockets, so identical scores
  usually mean the pockets really are near-identical in size/depth/composition.
- If every pocket scores very high, the protein may simply have several strong
  sites — carry the top few forward instead of collapsing to one.
- Confirm each pocket's geometry (volume, depth, enclosure) actually differs; if
  the inputs are identical the scores should be.

## `fpocket` not found

Install it (`apt-get`/`brew`/source) or fall back to **grid**. Nothing else in
the pipeline requires fpocket.

## `P2Rank` / `prank` not found

Set `P2RANK_HOME` (or put `prank` on `PATH`) and confirm a working Java runtime,
or fall back to **grid**.

## Very large protein (> ~5000 residues) is slow

The grid scan is O(grid_points × atoms). Prefer **fpocket** or **P2Rank**, or
coarsen the grid (`grid spacing` ~1.5 Å) to trade resolution for speed.

## Pocket sits at a crystal contact

A cavity between symmetry mates is an artifact. Restrict detection to a single
biological chain; if it vanishes, it was packing, not a real site.

## Wrong organism / wrong construct

If the PDB `SOURCE`/`HEADER` organism disagrees with the requested target (e.g.
"human" asked, murine crystal supplied), stop and flag it. Detecting pockets on
the wrong ortholog wastes the entire downstream campaign.
