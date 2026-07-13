# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-13 DONE — and its hypothesis was REFUTED.** The dead pipes are now banked as conserved AREA
(p = 2) and the live sapwood alone tapers (p = 2.3) — two banks that never meet in one metric. That
law is right and it stays. But both of its predictions failed:

    DBH vs census      iter-12: s 3.96  m 2.49  l 2.29     iter-13: s 4.81  m 3.41  l 3.11
    re-centred on m    iter-12: s 1.59  m 1.00  l 0.92     iter-13: s 1.41  m 1.00  l 0.91
    sapwood % of area  iter-12:        m ~16%  l ~10%      iter-13:        m 7.5%  l 3.7%

Girth overshoots MORE (~3.3×), and the sapwood fraction got WORSE — a 104 yr trunk is now **96%
heartwood**, where a real plane is ~50% and is noted for WIDE sapwood. The one gain: re-centred splay
1.59 → 1.41. **The metric was never the fault. Do not ship.**

## Open defects

1. **★ The model banks too much dead wood.** Every dead branch's full living section is kept forever,
   so heartwood grows without bound while the live crown does not. This is THE defect; 2–4 are
   downstream of it and cannot be read until it is fixed.
2. **`DBH_CALIB` is stale** (fitted heartwood-free) — the one legitimate re-centring scalar. Refit
   ONCE, and only *after* (1). It cannot fix (1); see the rails.
3. **Caliber splay, residual** — re-centred s 1.41 / l 0.91. `l` is home; **`s` is the one left.**
4. **`s` floor** — constant `R_TIP` floors DBH at 2·R_TIP at any age, and `s`'s census DBH is 12.7 cm,
   so `s` is pinned near the floor and *cannot* be thin. **One term won't mend both this and (3).**
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-14: BANK LOST LEAF UNITS, NOT DEAD BRANCH SECTIONS. The paper is READ.

⚠ **"KUBO ET AL. 2022" NEVER EXISTED.** The real paper is **Aye, Tin Nwe; Brännström, Åke; Carlsson,
Linus (2022), "Prediction of tree sapwood and heartwood profiles using pipe model and branch thinning
theory", *Tree Physiology* 42(11):2174-2185** — the same volume:page we had, under a **fabricated
author name**. iter-12 and iter-13 were both built on a *guess* at its mechanism. It is now READ
(full text + all 8 equations; local copy in `tmp/papers/`, gitignored — re-fetch: **PMC9652016**,
`https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9652016/fullTextXML`). **Every "Kubo" claim
below is superseded.**
⚠ Its equations are **GIF images**, not text — a text-only read returns the prose with all the numbers
silently deleted. That is almost certainly how the guessing started. **Look at the equations.**

**Its model** (branch thinning = *Hellström et al. 2018*, not Kubo; pipe model = Shinozaki 1964):

    (1) A(h)   = c · F(h)                     pipe model of plant form
    (5) F_S    = live leaf units above h   ⇒  sapwood area = c_S · F_S
    (6) F_H    = LOST leaf units above h   ⇒  heartwood area = c_H · F_H
    (7,8) trunk share = κ^(log2 g(h,n)) · area      κ = pipes kept per ramification

**THE FIX — it is a COUNTING change, not a new mechanism.** The paper banks **lost LEAF UNITS**: each
leaf unit that dies contributes **one pipe of area c_H, once, ever.** `ratchet()` banks each dead
branch's **whole cross-section** — which already contains that branch's own heartwood, which contains
its dead children's sections. **A recursive double-count.** Unbounded heartwood growth is the
signature of that recursion, not of a bad constant — which is why no scalar could ever move it
(consistent with the rails, and it explains them).

⚠ **c_H ≠ c_S.** The paper carries **two** pipe-area constants, fitted separately (its Table 1). Our
"dead pipes frozen at full living diameter" assumes `c_H = c_S`. That is an assumption we CHOSE, not
one the paper makes — and "**No new constant**" (LEDGER iter-12) is simply false. c_H is the second
constant, and it is the natural knob for the sapwood fraction (plane ≈ 50%, wide sapwood).

**We do not need Eqs 2-6 at all.** They are Hellström's *statistical* bookkeeping, there to ESTIMATE
live/lost leaf counts for a tree you cannot simulate. **We simulate** — so we count F_S and F_H
directly off the real skeleton as it grows and sheds, and we get κ for free from the actual topology.
*Simulate the process; let the appearance emerge.* One new constant (c_H), no fitted α/d/μ/κ.

**Ground truth to hit:** sapwood ≈ 50% of basal area at 104 yr (not 4%), DBH splay to ~1.0.
**The `s` floor (defect 4) is still separate and will NOT be fixed by this.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★ No scalar can move the SAPWOOD FRACTION — `DBH_CALIB` CANCELS.** Live sapwood scales as
  `R_TIP·n_live^(1/p)`, the dead bank as `R_TIP²·Σ n_c^(2/p)`; the ratio is R_TIP-free. The 96%
  heartwood is a pure STRUCTURAL statement, not a calibration error. (iter-13)
- ⛔ **No scalar can FIX a two-sided error** (`R0`, `DBH_CALIB`, `R_TIP`, constant `N_def` are uniform
  DBH multipliers) — but a scalar is the right tool to **CENTRE** one, *after* a size-dependent term exists.
- ⛔ **LAI cannot rescue p = 2.3** — it would need 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0.
- ⛔ **The tip budget is EXONERATED** (iter-11, vs an independent ground truth). So are the **shed rule,
  `MAX_CAT`, reiteration rate**, and **`N_def` accumulating with tip age** (REFUTED).
- ⛔ **The crown was never 2× too wide** — five width mechanisms built and refuted against an artifact.
  **Never add a sixth.**
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
