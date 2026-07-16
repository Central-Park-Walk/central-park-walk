# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-40: THE R²-vs-R³ GATE DIAGNOSIS IS REFUTED. The sapwood "deficit" is biology on TWO fronts.

Chris's iter-39 REDIRECT had three claims; iter-40 verified the LOAD-BEARING one (the gate exponent) against
the actual wiring, per his instruction "if the R³ is entering somewhere else, the diagnosis moves." It moved.
Instrument `scripts/iter40_scaling.py` logged the shed gate's OWN two terms over one l-tree ontogeny
(`tmp/iter40_scaling.{npz,png}`). **Cost does NOT outrun income:** `d log(nwood)/d log(income)=0.85` (twigs
0.57) — the gate does NOT condemn bigness. **income ∝ R^2.76, NOT R²** (thick Beer–Lambert rind, not a
silhouette; steepens with size; confirmed cross-tier R^2.0–2.6). **twigs ∝ R^1.56, NOT R³** (interior IS
pruned; nwood 19140 vs ntip 273 = scaffold, not twigs, is the R^2.3 term). Only LATE (yr70–104) does nwood
edge ahead (slope 1.35): income/nwood peaks ~1.07 @yr81, erodes ~20% to 0.86 @yr104 — mild, not catastrophic.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** /n_tips divisor dropped; n_tips 135–273.
2. **★★★ SAPWOOD "DEFICIT" — now BIOLOGY on two fronts, NOT a gate defect.** iter-39: no knob we own fixes it.
   iter-40: the income-R²/cost-R³ mechanism that made it a *gate* problem is REFUTED — income scales nearly as
   steeply as cost. sap_frac is ABSENT from the shed gate (raw count, unweighted). ⇒ likely a fidelity feature
   (thin shell on a dead core), to VALIDATE vs census, not a defect to fix. See NEXT.
3. **★ THE GATE IS NOT CONDEMNING BIGNESS on the S≡1 baseline.** l tree reaches full size (H 23.4m, 273 tips).
   Do NOT code a shed-gate interior-pruning fix — its premise (R²-shell income) is refuted. Size-law/R_TIP-prior
   all DEAD/refuted (#6). S≡1 baseline ships (l DBH 1.25×).

## NEXT — CHRIS'S CALL. The sapwood decline is looking like REAL BIOLOGY. Adjudicate, don't fix.

Two fidelity tracks, both INDEPENDENT of the (non-)gate problem — pick one, or park:
- **(A, cheapest) Validate sap_frac(age) vs a census sapwood-area-vs-age curve.** If real planes go DBH^1.5–2
  sublinear-in-basal-area (Chris: "robust as allometry gets"), the "deficit" dissolves into fidelity. Needs a
  published sapwood-area allometry on disk (`tmp/papers/`), NOT a fitted knob. This likely CLOSES board #2.
- **(B) τ_heartwood as an ONTOGENETIC fidelity knob** (Chris claim 2): convert a pipe to c→0 and drop it from
  the maintenance sum once older than N rings from the cambium, N fit to the sapwood-area allometry. Ring-age
  senescence, NOT conductance (iter-39 proved conductance can't reach trunk heartwood). Improves heartwood
  fidelity; will NOT change the gate (sap_frac absent from it) — do it for the wood, not the economy.
- The ~20% late-life ratio erosion (yr>80) needs the SAME defect-vs-biology question (old trees senesce).
⚠ Do NOT: adopt the R_TIP prior (#6), re-open shade/C/size-law, or code a shed-gate fix. First act next
session = Chris picks A/B/park; if A/B, read the on-disk sapwood-area allometry BEFORE coding (no fitted k).

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ q/K & HEART_RATIO ARE OUTPUTS.** `Q_MASS=2/E_M`, `c_H=c_S` DERIVED, not knobs. `C_NDEF=None` ON
  PURPOSE. Emergent R_TIP overshoots BECAUSE q is un-tunable. `c_H=c_S` is wrong-but-immaterial (iter-39/40).
- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES** (36/37) — the fold lived in the DYNAMICS, not the identity. DEAD.
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS (re-proved iter-40):** DO NOT nest `nohup … &` inside a `run_in_background` tool — the harness
  tracks the wrapper shell (exits in ms after echo) → FALSE "completed" notification while the real job runs
  detached. Recover with ONE `tail --pid=<pid>` waiter (never poll). Better: let run_in_background own the
  python directly (no nohup/&). One l-tree grow ≈ 17 min.
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022 (heartwood), Hellström 2018, WBE. Need a
  sapwood-AREA-vs-age/size allometry for track A — check these first, may already be in Aye/Shinozaki.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
- Distilled 2026-07-15 (commit 45043f1): iters 34–39 lessons promoted to global rules; raw → `ledger_archive/2026-07.md`.
