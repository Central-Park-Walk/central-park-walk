# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-38: POSITION B REFUTED (#6). Fold CUT (real win); sapwood deficit RE-DIAGNOSED.

Position B (`S = C_NDEF·M_sub^Q_MASS`, no n_tips divisor; commit 4e404c8) tested end-to-end (solve + 5×
bench). **Win:** the fold is cut — n_tips 135–215, never 1; every tree finite (l: DBH 139 cm, not iter-36's
2.8 m trunk); C pinned clean, gate passed. **Refuted (#6):** the emergent size-law OVERSHOOTS — l DBH
1.96× census — and q is an OUTPUT so it can't be tuned out. `C_NDEF` left **`None`** (S≡1 baseline still
ships); Position B code kept as the refutation's named home. Bench cached `tmp/iter38_bench.npz`.

**Re-diagnosis (this session, w/ Chris):** the R_TIP-prior fix I recommended is a HACK (per-species census
lookup, un-generalizable). Decomposing the bench, the sap_frac deficit is HEARTWOOD over-fill (F_H 0→248→
975 vs F_S 78→174→122), a defect iter-32 already saw and iters 33–38 walked past. iter-39 tests that ↓.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** /n_tips divisor dropped; n_tips 135–215,
   never 1, across the full bench. Dead regardless of the size-law.
2. **★★★ SAPWOOD DEFICIT IS PROBABLY HEARTWOOD OVER-FILL, NOT A SIZE-LAW.** Decomposed: F_S 78→174→122 vs
   F_H (heartwood, cumulative dead terminals) 0→248→**975** (8:1 at l). iter-32 already saw both halves;
   iters 33–38 chased only sapwood (6 refutations). iter-39 pressure-tests this (see NEXT). ← now the front.
3. **★ SIZE-LAW / R_TIP-as-PRIOR — ON HOLD.** Emergent S=C·M^q refuted (#6, overshoots l DBH 1.96×). The
   imposed-R_TIP-prior fix is a HACK as first phrased (per-species census lookup, doesn't generalize) — do
   NOT pursue until #2 is resolved. If #2 confirms heartwood, DBH was ~OK emergent (S≡1 gave l 1.25×).

## NEXT — iter-39: PRESSURE-TEST — is the sapwood deficit a LOSS-RATE defect, not a size-law defect?

**Hypothesis:** the sap_frac deficit is HEARTWOOD over-accumulation, driven by the shed loss-rate
`TAU_SHED` (line 707, "the ONE free param"; F_H = cumulative shed terminals → heartwood via c_H=c_S). NOT
R_TIP. **Test (no new code, R_TIP untouched):** keep `C_NDEF=None` (S≡1 baseline), sweep TAU_SHED DOWN
from 0.18 at 2–3 values via `plane_bench.py --set TAU_SHED=<v>` (5×{s,m,l}); read sap_frac + F_H/F_S + DBH.
**Confirmed if:** sap_frac rises toward census 0.50 at m/l and F_H/F_S falls toward ~1 at a PLAUSIBLE
TAU_SHED, WITHOUT breaking crown geometry (foliage spread, DBH stay sane). **THE FORK (pre-registered):**
because F_H is cumulative-FOREVER with c_H=c_S (both DERIVED, not knobs), sap_frac may fall with age
*structurally* regardless of rate — so if it is INSENSITIVE to TAU_SHED (or needs a τ so low the crown
never self-prunes), the defect is the Aye-2022 heartwood MODEL choice (does old disused pipe stay at full
c_S bore forever?), a canonical question tied to iter-29's c_H/c_S "leak's-twin" derivation — Chris's call.
⚠ Do NOT re-pin C, re-open the shade loop, or touch R_TIP — those are closed/held. ONE knob: TAU_SHED.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES, NOT THE ONE YOU FRAMED** (36/37) — "n_tips cancels" was true
  in the income IDENTITY, false in the DYNAMICS; the fold lived there. DEAD now (divisor removed).
- ⛔ **★★★ q/K & HEART_RATIO ARE OUTPUTS.** `Q_MASS=2/E_M`, `c_H=c_S` — DERIVED, not knobs (q un-tunable is
  WHY emergent R_TIP overshoots). `C_NDEF` stays `None` ON PURPOSE (refuted, not the iter-34 no-op trap).
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO** (30) — `plane_bench.py` 5×{s,m,l} ≈ 16 min; never fit a `-- noise --`
  line. **★★ A GATE CONFIRMS THE NULL BEFORE ITS SLOPE** (36). **HARNESS:** never double-background (LEDGER).
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022 (heartwood), Hellström 2018, WBE. APPEND-ONLY.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
