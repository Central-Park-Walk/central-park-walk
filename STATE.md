# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-28: THE RIM STARVES BESIDE A LEAK. 95% OF THE BUDGET EVAPORATES.

Read-only probe (`tmp/iter28_apices.py`, log + `tmp/iter28_raw.npz` beside it). Rails reproduce iter-27
exactly (DBH 1.09x/1.08x census · sap 22.0/13.8 · crown p50 6.67→6.22 · shed alive) ⇒ instrument sound.
**All three pre-registered predictions refuted; the survivor was not on the list.**

1. **DROOP IS EXONERATED.** `posture()` never moves existing nodes — it only rotates `ax.dirv`. At the
   rim it *raises* it (dy −0.339 → −0.266), and peripheral apices aim **outward** (out +0.24…+0.66).
2. **VIGOUR IS EXONERATED.** Peripheral vigour holds **0.69–0.83** in the late decades. Not the binder.
3. **★★★ THE RIM'S BUDGET IS WINNER-TAKE-ALL.** The rim as a class takes **60–85% of the year's pool**
   (at ~20% of apices) — yet from decade 41 its **median `l_afford/INTERNODE` is 0.000** against a max of
   **20–83**. Gini **0.83–0.96**; the **top 3 apices take 39–100%** of the rim's budget. The rest fall
   under the dormancy floor (~0.025) → dormant → `DORMANT_ABORT` kills them.
   **The widening front is three limbs.** iter-27's p100 runaway (2.2x census) and its 0.74x starved bulk
   are ONE phenomenon.
4. **★★★ AND THE WINNERS CANNOT SPEND IT.** `ext = min(1, l_afford/INTERNODE) · vigour`, and `_v` is
   zeroed every year ⇒ surplus is **discarded**. Over the `l` run: allocated **3,491,679 cm³**, spent
   **173,142 cm³** ⇒ **95.0% EVAPORATES** (98.8% by the last decade; **99.7% of it at apices over the
   clamp**). A floor, not an estimate. Not a double-count: `_v` is set only for `kind=="apex"` (line 1687).
5. **⇒ The deviation from the cited prior art IS the leak.** Palubicki: `n = floor(v)`, `l = v/n` — a rich
   apex buys **more metamers**. Here `n = GU_NODES[cat]` is **FIXED**; only `l` scales, capped. One sink,
   and it saturates. Line 1671's *"Resource is CONSERVED"* is true of the **split**, false of the **spend**.
6. **⇒ This EXPLAINS the economy's exoneration, it does not re-open it.** All twelve economic iterations
   changed the pool's SIZE; 95% of the pool is thrown away regardless of size.

## NEXT — iter-29: THE SPILL. MAKE THE CLAMP A CONSTRAINT, NOT A DISCARD.

The winners are **already at the clamp** ⇒ handing their unspendable surplus to a starving rim apex costs
them **nothing in reach**. So: in `_distribute`, an apex may be allocated at most what it can spend
(`n·π·r_tip²·INTERNODE·vigour`); the remainder **spills back** and is re-distributed among candidates
still below their clamp, iterating until the pool is exhausted or every apex is saturated.

- **★ COMPUTE THE LOOP GAIN FIRST** (rail, iter-20). Spill → more extension → more foliage → more income
  → more spill. **Do not code the term before the gain is on paper.** The `.npz` has what you need.
- **★ PRE-REGISTER**, incl. the rails expected to HOLD: DBH must not move; self-pruning stays alive; the
  p100 runaway must NOT get worse (the winners are capped, so it should not).
- ⚠ This is **not** an economic term: no gate, no light law, no denominator, no TAU. It is **conservation
  of a pool that is already allocated.** The magnitude family stays closed.
- ⚠ **`n = floor(v)` IS NOT THE FIX.** Scaling `n` was tried at iter-6: "it destroys ramification and
  grows a bare pole with a few whips." The surplus needs a *botanical* sink (more shoots / sylleptic
  laterals), or it must spill sideways. Spill first — it is the conservative one.

## Open defects

1. **★★ 95% OF THE EXTENSION POOL IS DISCARDED AT THE CLAMP** (iter-28). The root. Everything below is
   plausibly downstream — **do not chase them separately until the spill is measured.**
2. **★★ THE RIM IS DEPOPULATED** — gini 0.83–0.96, median rim apex funded at 0.000. Same root.
3. **The crown does not widen** — bulk radius 0.93x m→l where the census demands 1.34x (iter-27).
4. **Too TALL, too NARROW** — H 22.98 m at `l` = 1.20x UTD; p100 radius 2.2x census around a 0.74x bulk.
5. **`l` is ~28% short in income and wood**; caliber splay (`s 1.53, m 1.09, l 1.08`, all in `s`);
   sapwood 22.0/13.8% vs ~50% census. All plausibly downstream of (1).
6. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE ECONOMY IS EXONERATED, ALL OF IT** — numerator (22), denominator (26), light law (25),
  size-scaling (26: 0.686 vs the census's own 0.664). iter-28 **explains why**: the pool's size was never
  the binder, because the pool is thrown away. **No gate term, no light term, no new TAU.**
- ⛔ **★★ DROOP / `arch` / `DROOP_K` IS EXONERATED as the geometric root** (iter-28). So is **`vigour`**.
- ⛔ **★★ A CLAMPED SINK IS A LEAK** (iter-28) — `min(1, …)` on the only thing resource can buy discards
  the remainder silently. Audit every saturating term for what happens to the surplus.
- ⛔ **★★ A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION** (iter-27); **"the class is rich" ≠ "the member is
  funded"** (iter-28, gini 0.96). Read the percentiles.
- ⛔ **★ DO NOT CODE `M^(3/4)`.** An OUTPUT of the heartwood law we already simulate (Berry 2024).
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20).
- ⛔ **★ AN UNFITTABLE CONSTANT IS THE SIGNATURE OF A SATURATED INSTRUMENT** (iter-25).
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` 0.11 m vs `VOX` 0.6 m.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH analytic in age. **b(n) is the VALIDATOR.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17) ⇒ target a RATIO.
- ⛔ **STATICS IS EXONERATED for load-bearing** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Berry 2024 + Xu 2014 opened (web).
  **Shinozaki 1964 is still UNOPENED.**
- ⚠ **Instrument limit:** seed spread 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is measurable.
  **DBH is the tight one (9–19%).**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP`, `TWIG_DENSITY` are **None** (retired).
  A retired term reads like a live one.
- ⚠ **Runs are ~4x slower since iter-25** — m + l ≈ 8–10 min. Budget for it; run in background.
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
