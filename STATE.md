# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**★★ iter-18 DONE — THE GATE IS OPEN. The size term is ADMISSIBLE, and it is not what we thought it was.**
A pure measurement (`tmp/iter18_gain_probe.py`, output in `tmp/iter18_gain_probe.out`) — no mechanism
changed, no constant touched. Two findings, one of them structural:

- **★ THE LEVER CANCELS. `N_cap ∝ r³/lever ≡ M_sub` — the SUBTENDED MASS, identically.** On a
  statics-bound node `r³ ∝ |V|` and `lever ≡ |V|/M_sub` by its own definition. "Cantilever capacity"
  was never a third mechanism: it is **the mass the node already holds up**, i.e. **history** — wood
  laid down in past years, which this year's income cannot bid up. That is the exogenous quantity.
- **★ LOOP GAIN = 0.69** (mass-weighted, on binding load-bearing wood), and it **never exceeded 0.866**
  in 127 binding tier-years. The ceiling is **structural**: leaf 1.000 / pipe 0.870 / statics ≤ 0.667,
  so a mass-weighted mean can only reach 1 if the mass went all-leaf — against a **measured 96% wood**
  share of the moment (iter-8 §5's assertion, finally measured, and right).
- **Why iter-16 got 1.30 and this gets 0.69 — ONE EXPONENT.** Off a **pipe** radius `r³ ∝ T^(3/p)`: a
  **cube** law, gain 1.30, runaway. Off **statics** `r³ ∝ |V| ∝ mass ∝ T^(2/p)`: a **square** law, gain
  ≤ 0.870, regulator. **iter-16 was refuted by the cube, not by the cantilever.**
- **Unfitted, the scale landed on the ground truth:** `M_sub`(root) **s 113.2 / m 848.6 / l 2782.2 kg**
  ⇒ **m→l = ×3.28**, against ×3.09 (Hellström) and ×2.71 (census). Inside the instrument floor of the
  better one. **An observation, not a result — iter-19 pre-registers against it, it does not celebrate it.**

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — still THE defect, still `N_def`.** Economy is scale-free in
   tips (`docs/grower_saturation_diagnosis.md`). iter-15 confirmed the *cure* (size-dependent `N_def` on
   BOTH sides — took `s` from 5.15× to 1.15×) and refuted its numerator (`V_crown`, gain > 1); iter-16
   refuted the next (cantilever on a PIPE radius, gain 1.30). **iter-18 has now cleared the third at gain
   0.69 — the numerator is `M_sub`.** Ground truth: real tips ×~3.0 m→l ⇒ sapwood ≈ 50% at 104 yr.
2. ~~`DBH_CALIB` stale~~ — **CLOSED, iter-17.**
3. **Caliber splay** — `s 1.54, m 1.00, l 1.01`. One-sided, all in `s`. Same thing as defect 4.
4. **`s` floor** — (1) from the other end: a constant `N_def` over-serves the sapling. Free when (1) lands.
   ⚠ `M_sub(s)/M_sub(m) = 0.133` — whether that is the cure or an **over**-correction is iter-19's to predict.
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-19: CODE IT. `N_def ∝ M_sub`, on BOTH sides, normalized at the m-anchor.

The gate is passed; the mechanism is named. What iter-19 must get right, in order:

- **⛔ DO NOT gate the term on "where statics binds."** Statics binds in only **2 of `s`'s 16 years** and
  **never at the bole** (the root is pipe-bound in every tier-year). Read `r³/lever` on a *pipe*-set radius
  and you are back on the **cube law and the 1.30 runaway — iter-16 rebuilt by accident.** Code **`M_sub`
  directly**: defined every node, every year, and *equal* to the statics capacity wherever statics binds.
- **Ride it on the RATIO** `S(t) = N_def(t)/N_DEF_REF`, exactly as iter-15 did with `V_crown` — `S ≡ 1` at
  the m-anchor, so the whole iter-9/iter-17 calibration (`ALPHA`, `DBH_CALIB`, `SHADOW_A/B`, `TAU`) is
  preserved unchanged. It **re-expresses** the constants; it does not re-fit them.
- **BOTH sides — the light AND the ledger** (`S_IN_LIGHT`). A ledger-only `N_def` cannot break the fixed
  point; that is iter-15's finding and it still holds.
- **★ PRE-REGISTER, before running:** `s`, `m` and `l` DBH, the sapwood fractions, and — the one that
  decides it — **what `N_def(s)/N_def(m) = 0.133`-ish does to defect 4.** Name the rails you expect to
  HOLD, and read the refutation for what it *exonerates*.

## Rails — each cost a session; do not re-litigate

- ⛔ **★ `N_def` MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, hull or voxels; iter-15) — positive
  feedback on income, measured from its own product. **COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM.**
  This rail has now been *used in anger three times* (V_crown refuted; cantilever-on-a-pipe refuted at
  1.30; `M_sub` CLEARED at 0.69). It works. Keep it.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age — a parameter in an
  output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn `HEART_RATIO`
  down to buy sapwood.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (measured holding in iter-17: sapwood
  18.3/9.9/4.7 → 20.9/9.5/4.4 under a 3.37× thinning). A scalar may **CENTRE** and **UN-SUPPRESS**; it may
  never **FIX**. `DBH_CALIB` is spent. **The remaining error is structural, and it is (1).**
- ⛔ **LAI cannot rescue p = 2.3** (needs 2.45 → 6.96 → 12.18; plane is 4.0–6.0). ⚠ Note `p = 2.3` is also
  what puts 1.0 *between* the cube gain (1.30) and the square gain (0.87) — it is load-bearing twice now.
- ⛔ **EXONERATED — do not re-indict:** the tip budget (iter-11), the shed rule, `MAX_CAT`, the reiteration
  rate, and `N_def` accumulating with tip AGE. **The crown was never 2× too wide** — five width mechanisms
  built and refuted. No sixth.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13. Aye 2022
  and Hellström 2018 are read (`tmp/papers/`, gitignored). Aye's equations are **GIF images** — a text-only
  fetch silently deletes every number.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
