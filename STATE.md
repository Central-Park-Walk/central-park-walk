# STATE — cpw / london-plane

**The London plane developmental grower** — `scripts/plane_grower.py`. Grow a plane tree from a
seed by simulating development, and let the crown, caliber and depth *emerge*. Full history lives
in the memory file `project_london_plane_crown_mould.md`; this is the snapshot.

## Where we are

**iter-11 DONE** (`621fd52`) — the tip budget was measured against an independent ground truth and
**the premise was wrong.** The armature's tip count is 2.37× / 1.47× / 1.14×, i.e. right where it
was accused; the "`l` has 2.1× too few tips" reading was an **artifact** of asking the pipe layer's
own demand whether the pipe layer was being fed enough.

The parameter-free test is the finding: hand the pipe layer the **true** twig count (no fitted
constant — `DBH_CALIB` cancels, `R0` is a physical bud radius) and the two-sided caliber error
**survives a perfect tip budget**: 1.36× / 0.87× / 0.68×. So the defect is not how many tips we
grow, it is **what the pipe layer does with them.**

## NEXT — iter-12 = HEARTWOOD

Shinozaki's pipe model sizes **sapwood** by leaf area. This grower equates the *whole* cross-section
with sapwood, so its trunk *is* its plumbing. A real trunk is plumbing **plus a dead heartwood core
whose fraction grows with age** — which is exactly why real leaf area scales ~DBH^1.4 and not
DBH^2.3. Right two-sided sign, size-dependent, published rather than invented.

**Derive before coding.** Required exponent is p = 1.37.

## The rails (each one cost a session; do not re-litigate)

- ⛔ **No scalar can fix a two-sided error.** `R0`, `DBH_CALIB`, `R_TIP`, a constant `N_def` are all
  uniform multipliers on DBH — they slide the tiers together and can only *centre* a splay. The sign
  pattern of the residual tells you the **rank** of the fix.
- ⛔ **LAI cannot rescue 2.3.** It would have to run 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0
  and LAI 12 is closed-canopy rainforest. Checked; it does not bear the load.
- ⛔ **The crown was never 2× too wide** — the tier ages were guessed. Five width mechanisms were
  built and refuted against an artifact. **Never add a sixth.**
- ⛔ **The shed rule, `MAX_CAT` and the reiteration rate are EXONERATED.** Do not tune them for this.
- ⛔ **`N_def` accumulating with a tip's own age is REFUTED by our own source** — C&E measure A4/A5
  self-pruning in 1–4 yr, so the spray is in steady state by ~4 yr.
- ⚠ **Suspect the CLOCK before the MECHANISM.** That has now been the answer twice (iter-10:
  `NURSERY_YEARS = 7`; the `s` crown "0.21×" was a clock error, not a mechanism error).
- ⚠ **`s` is a SEPARATE, smaller defect.** A constant `R_TIP` floors DBH at 2·R_TIP = 10.3 cm at any
  age, and `s`'s whole census DBH is 12.7 cm — the sapling is pinned near the floor and cannot be
  thin. **Do not expect one term to mend both**; that expectation produced the five refuted width
  mechanisms.

## Instrument limit

Seed variance: **126% on `s` span, ~100% on `n_tips` at 8 seeds.** Nothing finer than ~10–15% is
measurable — do not chase a difference smaller than that.

## Do not ship

Criterion vi is unmet.

## Open, for Chris

Two abandoned agent branches hold unmerged work (**ginkgo**, **magnolia**).
