# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-38: POSITION B REFUTED (#6). Fold CUT (real win) — but R_TIP overshoots caliber.

Position B (`S = C_NDEF·M_sub^Q_MASS`, no n_tips divisor) is coded (commit 4e404c8) and TESTED end-to-end.
**Two clean wins:** (1) **the fold is cut** — n_tips stayed 135–215 across every grow, never 1; every tree
finite (l: DBH 139 cm, H 23.6 m, not iter-36's 2.8 m exploded trunk). (2) C pinned cleanly, C_NDEF=0.008442,
**gate passed** (`d log M/d log C=0.55`, no bifurcation). **But the size-law OVERSHOOTS** and the pre-
registered "not overshooting" clause fails → refutation #6:

- **DBH at l = 1.96× census** (l trunk ~2× too thick); m→l DBH lever 1.73× census. RESOLVED overshoot.
- sapwood frac 1.99×→0.75×→**0.23×** s→m→l. DECOMPOSED: F_S 78→174→122 vs F_H (heartwood) 0→248→**975**
  (8:1 at l) — the fraction collapse is HEARTWOOD, not vanishing sapwood.
- Both trace to ONE cause: S>1 at l ⇒ larger R_TIP ⇒ thicker DBH (pipe) AND larger `c_heart∝r_tip²`.
  R_TIP emerging from mass overshoots at l and **cannot be tuned out — q is an OUTPUT.**

`C_NDEF` left **`None`** (inert; S≡1 baseline still ships). Position B code KEPT as this refutation's named
home (mirrors K_NDEF/MASS_CAP). Bench cached `tmp/iter38_bench.npz` (`--load` to re-report).

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** Dropping the /n_tips divisor cut it:
   n_tips 135–215, never 1, across the full 5×{s,m,l} bench. The fold is dead regardless of the size-law.
2. **★★ SIZE-LAW: EMERGENT-S HANDLE REFUTED (iter-38, #6).** Routing size into R_TIP via S=C·M^q settles
   directionally but OVERSHOOTS (l DBH 1.96× census); q is an OUTPUT, un-tunable. New direction: impose
   R_TIP as a census/WBE-shaped allometric PRIOR (Chris's call — see NEXT). This subsumes old #2/#3.
3. **★ R_TIP is the handle — but IMPOSED, not emergent.** iter-38 proved emergent R_TIP overshoots; the
   prior sets R_TIP to hit census DBH directly, like the area-preserving pipe is imposed.
4. **HEARTWOOD 0→248→975 (8:1 at l)** over-fills — AMPLIFIED by any large r_tip (`c_heart∝r_tip²`).
   Leaf-unit LOSS rate, ⛔ NOT `HEART_RATIO`. Couples to #3; an imposed R_TIP must fix this too.
5. **`s` DBH 0.57× census** — under Position B the sapling trunk went thin (S<1 floors R_TIP small).
   An imposed census-shaped R_TIP would set the small end directly. Folds into #3.

## NEXT — iter-39: CHRIS'S CALL — adopt the R_TIP-as-allometric-PRIOR direction? (canonical change)

Refutation #6 fired per iter-37's pre-registered stopping rule: **do NOT open a 7th emergent-loop.** The
recommended direction (iter-37 + iter-38 evidence) is to make **R_TIP an imposed allometric prior** —
R_TIP(size) set to hit census DBH directly (census/WBE-shaped, imposed exactly like the pipe), and let
mass/sapwood/heartwood emerge AROUND it. This is a **canonical design change** (emergent-S → imposed-R_TIP);
it needs Chris's sign-off before any code. When adopted, write an ADR position analysis FIRST (as iter-37
did), then code + bench. ⚠ Do not re-pin C or re-open the shade loop — those are closed.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES, NOT THE ONE YOU FRAMED** (36/37) — "n_tips cancels" was true
  in the income IDENTITY, false in the DYNAMICS; the fold lived there. DEAD now (divisor removed).
- ⛔ **★★★ q/K ARE OUTPUTS.** `Q_MASS=2/E_M` (parsed, not typed 3/4); WBE `M^(3/4)` is the VALIDATOR.
  iter-38: q un-tunable is WHY emergent R_TIP can't be de-overshot → the case for an IMPOSED prior.
- ⛔ **C_NDEF stays `None` ON PURPOSE** (refuted #6) — NOT the iter-34 "None=no-op" trap; Position B is
  meant to be inert. The Position B code is the refutation's named home (mirrors K_NDEF/MASS_CAP).
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO** (30). `plane_bench.py` 5×{s,m,l} ≈ 16 min (wall≈slowest l ~960 s);
  records `m_sub`/`S`. iter-38 cache `tmp/iter38_bench.npz`. Never fit a `-- noise --` line.
- ⛔ **★★ A GATE MUST CONFIRM THE NULL BEFORE ITS SLOPE** (36) — solve pins S(m)=1 (|S−1|<0.02) THEN reads
  conditioning. **HARNESS:** never double-background (`nohup … &` inside `run_in_background` — staged in LEDGER).
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022, Hellström 2018, WBE/Enquist. LEDGER APPEND-ONLY.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
