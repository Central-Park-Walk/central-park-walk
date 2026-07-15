# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-34: THE SIZE-LAW IS SWITCHED OFF. `S ≡ 1` AT EVERY TIER — MEASURED.

iter-34 read the deferral economy out of one grow per tier (`tmp/iter34_ndef.py`, no fit). Result is
bit-identical across s/m/l:

| tier | S | N_def | r_tip | m_sub kg | A_sap cm2 |
|---|---|---|---|---|---|
| s | **1.0000** | 21.723 | 15.252 mm | 107 | 81 |
| m | **1.0000** | 21.723 | 15.252 mm | 1404 | 242 |
| l | **1.0000** | 21.723 | 15.252 mm | 14104 | 960 |

STATE's iter-34 hypothesis ("N_def too high per tip at m/l") is **FALSIFIED at the premise**: N_def
does not run high — it does not run at all. `update_n_def()` short-circuits on `MASS_CAP is None`
(RETIRED iter-20), so `S` never leaves 1.0 and `R_TIP` is uniform. The iter-15/19/20 machinery has
been **inert for 14 iterations**, and iter-21's sub-linear replacement was never coded. `m_sub`
(107→14104 kg) shows the numerator the law would feed from IS computed every year, wired to nothing.

⇒ **The F_S 2.4x deficit is the signature of the ABSENT size-law, not a mis-valued N_def.** `S` is the
sole size-dependent term feeding sapwood, and it drives BOTH `R_TIP` and the per-tip load. Off, the
model can only say "bigger ⇒ more sapwood" by growing more tips — which census forbids (tips ~1.1x off
at `l`, sapwood ~2x off).

## The board (n=5; only a `** RESOLVED **` line is a tell)

1. **★★ THE SIZE-LAW IS OFF (`MASS_CAP=None`).** This subsumes the whole "F_S wrong-shaped" story
   (iter-33). Restoring `S>1` at m/l lifts `R_TIP` → lifts sapwood at m/l — the shape census wants.
2. **★ iter-33's R_TIP exoneration is CONDITIONAL** — it killed a UNIFORM R_TIP only. A SIZE-DEPENDENT
   R_TIP (`R_TIP ~0.87/1.49/1.40`) hits census sapwood exactly as well as `F_S ~0.72/2.48/2.17` does;
   same retired term (`S`), two handles. Biology (older tip ⇒ more real twigs) favors the R_TIP handle.
3. **★ HEARTWOOD AREA 1.77x → 2.63x** — over-fills with size. Suspect the RATE of leaf-unit LOSS that
   feeds it; ⛔ NOT `HEART_RATIO`. Take it after the size-law is back.
4. **`s` broken separately** — DBH floored at `2*R_TIP` = 10.3 cm at any age (the uniform-R_TIP floor).
- **NOT tells:** crown r_p50 (needs n~7) · height (1.01/1.03x — rail) · foliage count (90–112% spread).

## NEXT — iter-35: DERIVE the sub-linear N_def numerator (iter-21's open problem). DESIGN, not a fit.

**Hypothesis to earn:** a size-dependent `N_def` that is SUB-LINEAR in `m_sub` gives `S>1` at m/l,
raising `R_TIP` and thus sapwood into census shape, WITHOUT the tip explosion census forbids.
**This is the careful session, and the rails are loaded:** (a) ⛔ iter-20 — linear-in-mass is a
transcritical bifurcation (loop gain ~1); the numerator MUST be sub-linear and **the whole-crown
loop gain computed BEFORE the line is written**. (b) ⛔ **DO NOT code `M^(3/4)` as a parameter** — it
is an OUTPUT; `b(n)=beta*(n+1)^d` (Hellström) is the VALIDATOR, never an input. (c) ⚠ WBE/Enquist is
NOT on disk (`tmp/papers/` has Shinozaki, Aye, Hellström; Berry+Xu web) — OPEN it before coding.
Likely warrants an ADR. Probably a `/song-prep`-shaped design session, then a code iter.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ A LAW GUARDED BY `if CONST is None: return` IS A NO-OP** (iter-34). Verify a named term is
  live by RUNNING and reading its value, not by reading the equation. `MASS_CAP=None` made the size-law
  inert for 14 iters while STATE cited it as active.
- ⛔ **★★★ DECOMPOSE A RATIO BEFORE YOU READ ITS SHAPE** (iter-32). Two errors that cancel look like one
  small error — DBH's 1.05x hid sapwood 0.45x and heartwood 1.77x.
- ⛔ **★★★ A UNIFORM SCALAR CANNOT MAKE A TIER-VARYING SHAPE** (iter-10/33) — but a SIZE-DEPENDENT one
  can, and `S` is exactly that. The iter-33 exoneration was of the UNIFORM case only (see board #2).
- ⛔ **★★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (iter-30). `plane_bench.py`: n seeds × tiers in
  parallel (5×{s,m,l} ≈ **20 min wall**; a 1-seed 3-tier read ≈ **17 min**). Baseline cached
  **`tmp/iter31_bench.npz`** (dbh/h/rp50/rp90/nfol/sap/F_S/F_H per seed). `--load` re-reports free;
  `--set K=V` for a paired fit. **Never fit against a `-- noise --` line.**
- ⛔ **★★ HEART_RATIO IS NOT A KNOB** — fix what FEEDS the bank (rate of leaf-unit loss), not c_H.
  `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **★★ ECONOMY STRUCTURE EXONERATED** — numerator(22), denominator(26), light law(25); only SCALE
  refit. **STATICS(21) · DROOP/vigour(28) EXONERATED** · crown-at-`m` deficit was NOISE(31).
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (20). `K(n)=alpha(n+1)^d` makes DBH analytic
  in age; **b(n) is the VALIDATOR, not an input.**
- ⚠ **NEVER cite a paper you have not OPENED.** On disk (`tmp/papers/`): Shinozaki 1964 I+II, Aye 2022,
  Hellström 2018. Berry 2024 + Xu 2014 opened (web). **WBE/Enquist is NOT yet on disk.**
- ⚠ **LEDGER is APPEND-ONLY;** its entry ships in the same commit as the change.

## Housekeeping

- ALPHA = 1.026e-5 PROVISIONAL — fitted on DBH@m alone (the number most corrupted by cancellation).
  Treat ALPHA as unfitted.
- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
