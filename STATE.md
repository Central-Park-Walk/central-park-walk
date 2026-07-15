# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-38: POSITION B CODED + PINNED + GATE PASSED. Bench running at hand-off.

`update_n_def` now drives `S = C_NDEF·M_sub^Q_MASS` DIRECTLY (commit 4e404c8), dropping the `/n_tips`
divisor of the iter-36 form. This cuts the fold's return arm (`d log S/d log n_tips = 0`) — the channel
iter-36 exploded through. `N_def=S·N_DEF_REF` is now PRIMARY; `T_total=N_def·n_tips` floats. `C_NDEF`
supersedes the retired `K_NDEF`. Q_MASS=0.625 unchanged (=2/E_M, a parsed OUTPUT).

**SOLVE DONE (`tmp/iter38_solve.log`): C_NDEF = 0.008442**, clean monotone bracket → S(m)=1.02. GATE
PASSED — `d log S/d log C=1.37`, `d log M/d log C=0.55` (both ≪10, no bifurcation; internally consistent).
**THE FOLD IS CUT:** n_tips stayed **135–215 across every grow, never 1** (iter-36 collapsed to 1).

**⚠ BENCH RUNNING at hand-off** — `scripts/plane_bench.py --set C_NDEF=0.008442 --out tmp/iter38_bench.npz`
(task `bj6z6fege`, log `tmp/iter38_bench.log`), ~20-25 min. It is the DECIDER: does S settle across tiers
and does sapwood F_S track census upward at l? `C_NDEF` is NOT yet frozen — that waits on this bench.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — CUT IN CODE (iter-38), VERIFICATION PENDING.** Divisor dropped;
   n_tips=193 not 1 is the first confirmation. ⛔ Not closed until the bench shows S SETTLES.
2. **★ SIZE-LAW STILL OFF.** With S≡1 the tree was scale-free in tips; census wants sapwood ~2× larger
   at l (F_S 2.4× low at m/l). B routes the size signal into R_TIP via S>1 at l — verify at the bench.
3. **★ R_TIP vs F_S degeneracy** — B IS the R_TIP handle (size-dependent R_TIP off M_sub, no n_tips loop).
4. **HEARTWOOD 1.77→2.63×** over-fills with size — leaf-unit LOSS rate, ⛔ NOT `HEART_RATIO`. After #1.
5. **`s` DBH floor** — DBH floored at `2·R_TIP` at any age (uniform-R_TIP floor). After #1.

## NEXT — iter-39: READ THE BENCH (`tmp/iter38_bench.log`), then judge SETTLE + sapwood tracking.

1. Read the bench (5×{s,m,l}, C=0.008442). Judge two things: does S SETTLE (S(s)<1, S(m)≈1, S(l)>1)?
   Does F_S (sapwood) track census UPWARD at l — closing the ~2.4× board-#2 deficit, not overshooting?
2. If PASS on both → **freeze C_NDEF=0.008442 in `plane_grower.py`** (replace the `None`) and commit.
   Then the fold + size-law are both handled; board #1/#2/#3 resolve; move to heartwood (#4).
3. **⛔ PRE-REGISTERED STOPPING RULE (iter-37):** this is Position B's ONE shot. The gate already passed,
   so the live risk is SETTLE/TRACK. If S fails to settle OR sapwood doesn't track (or overshoots badly)
   → **refutation #6.** Do NOT open a 7th loop. Hand back to Chris: make R_TIP an allometric PRIOR
   (census/WBE-shaped), imposed like the pipe, and let the rest of the tree emerge around it.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES, NOT THE ONE YOU FRAMED** (36/37). §2 gated the mass loop and
  missed the fold by asserting "n_tips cancels" — true in the income IDENTITY, false in the DYNAMICS. B
  cuts that loop at the source by removing the divisor; the only loop left is the ≤q<1 mass loop.
- ⛔ **★★★ A LAW GUARDED BY `if CONST is None: return` IS A NO-OP** (34). `C_NDEF=None` now = S≡1 baseline.
  The pin must be FROZEN into the constant (not left None) or Position B ships inert like MASS_CAP did.
- ⛔ **★★★ q/K ARE OUTPUTS.** `Q_MASS=2/E_M` (parsed, not typed 3/4); WBE `M^(3/4)` is the VALIDATOR.
- ⛔ **★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (30). `plane_bench.py` 5×{s,m,l} ≈ 20-25 min (records
  `m_sub`/`S`). Baseline `tmp/iter31_bench.npz`. Never fit a `-- noise --` line.
- ⛔ **★★ A GATE MUST CONFIRM THE NULL BEFORE READING ITS SLOPE** (36) — the iter-38 solve pins S(m)=1 FIRST
  (|S−1|<0.02), THEN measures conditioning. A gate read between two exploded points is meaningless.
- ⛔ **HARNESS:** don't double-background (`nohup … &` inside `run_in_background` loses the notification —
  bit me this iter, staged in LEDGER). HEART_RATIO is not a knob; fix what feeds the bank (leaf-loss rate).
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022, Hellström 2018, WBE/Enquist. LEDGER APPEND-ONLY.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
