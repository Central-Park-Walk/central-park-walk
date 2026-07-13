# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — see below).

## Where we are

**iter-11 DONE** (`621fd52`). The tip budget was measured against an *independent* ground truth
(twig count from leaf area — touches no pipe-model constant): the armature is **2.37× / 1.47× /
1.14×**, right where it was accused. The old "`l` has 2.1× too few tips" was an **artifact** — read
off the pipe layer's own demand, which assumes the pipe model and then blames the budget for not
feeding it.

**The parameter-free test is the finding.** Hand the pipe layer the *true* twig count (no fitted
constant) and the two-sided caliber error **survives a perfect tip budget: 1.36× / 0.87× / 0.68×.**
⇒ the defect is not how many tips we grow, it is **what the pipe layer does with them.**

**Just changed (2026-07-13):** thread bound; `STATE.md` + `LEDGER.md` seeded. No grower code touched.
The **cold start is CONFIRMED** (iter-0b): a blank session rebuilt the whole picture from this file in
three tool calls, never opening the 1400-line memory file. Iterate from here; don't go back to memory.

## Open defects

1. **★ Caliber, two-sided** — `s` too thick, `l` too thin. The live one. Required exponent **p = 1.37**, not 2.3.
2. **`s` floor (separate, smaller)** — constant `R_TIP` floors DBH at 2·R_TIP = 10.3 cm at any age;
   `s`'s census DBH is 12.7 cm ⇒ pinned near the floor, *cannot* be thin. **One term won't mend both.**
3. Criterion vi unmet ⇒ **do not ship.**

## NEXT — the one hypothesis: iter-12 = HEARTWOOD

Shinozaki's pipe model sizes **sapwood** by leaf area. This grower equates the *whole* cross-section
with sapwood — its trunk *is* its plumbing. A real trunk is plumbing **+ a dead heartwood core whose
fraction grows with age**, which is exactly why real leaf area scales ~DBH^1.4, not DBH^2.3. Right
two-sided sign, size-dependent, published not invented. **Derive before coding.**

## Rails — each cost a session; do not re-litigate

- ⛔ **No scalar can fix a two-sided error.** `R0`, `DBH_CALIB`, `R_TIP`, constant `N_def` are all
  uniform DBH multipliers: they slide the tiers together, they can only *centre* a splay. **The sign
  pattern of the residual tells you the RANK of the fix.**
- ⛔ **LAI cannot rescue 2.3** — it would need 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0.
- ⛔ **The crown was never 2× too wide** (the tier ages were guessed). Five width mechanisms built and
  refuted against an artifact — **never add a sixth.**
- ⛔ **Shed rule, `MAX_CAT`, reiteration rate: EXONERATED.** Do not tune them for this.
- ⛔ **`N_def` accumulating with a tip's own age: REFUTED by our own source** (C&E: A4/A5 self-prune in
  1–4 yr ⇒ steady state by ~4 yr).
- ⚠ **Suspect the CLOCK before the MECHANISM** — that has been the answer twice.
- ⚠ **Instrument limit:** seed variance 126% on `s` span, ~100% on `n_tips` at 8 seeds. Nothing finer
  than ~10–15% is measurable. Do not chase a smaller difference.

## Open for Chris — two abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
