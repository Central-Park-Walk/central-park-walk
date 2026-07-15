# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-38: POSITION B CODED. S = C·M_sub^q, NO n_tips divisor. Solve running at hand-off.

`update_n_def` now drives `S = C_NDEF·M_sub^Q_MASS` DIRECTLY (commit 4e404c8), dropping the `/n_tips`
divisor of the iter-36 form. This cuts the fold's return arm (`d log S/d log n_tips = 0`) — the channel
iter-36 exploded through. `N_def=S·N_DEF_REF` is now PRIMARY; `T_total=N_def·n_tips` floats. `C_NDEF`
supersedes the retired `K_NDEF`. Q_MASS=0.625 unchanged (=2/E_M, a parsed OUTPUT).

**First evidence the fold is cut:** the m tier grows with **n_tips=193** (at C=0.006, S=0.61), where the
iter-36 divisor form collapsed it to **n_tips=1** at blow-up. Deterministic (cross-checked two processes).

**⚠ Solve is STILL RUNNING at hand-off** — `tmp/iter38_solve_C.py`, PID 730773 (detached), ~3 min/grow,
log `tmp/iter38_solve.log`. It root-finds C on S(m@47)=1, then measures the conditioning gate. NOT yet
read. A tracked waiter (`while kill -0 730773`) was launched to surface the result on exit.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — CUT IN CODE (iter-38), VERIFICATION PENDING.** Divisor dropped;
   n_tips=193 not 1 is the first confirmation. ⛔ Not closed until the bench shows S SETTLES.
2. **★ SIZE-LAW STILL OFF.** With S≡1 the tree was scale-free in tips; census wants sapwood ~2× larger
   at l (F_S 2.4× low at m/l). B routes the size signal into R_TIP via S>1 at l — verify at the bench.
3. **★ R_TIP vs F_S degeneracy** — B IS the R_TIP handle (size-dependent R_TIP off M_sub, no n_tips loop).
4. **HEARTWOOD 1.77→2.63×** over-fills with size — leaf-unit LOSS rate, ⛔ NOT `HEART_RATIO`. After #1.
5. **`s` DBH floor** — DBH floored at `2·R_TIP` at any age (uniform-R_TIP floor). After #1.

## NEXT — iter-39: READ THE SOLVE, gate, then BENCH. Then judge SETTLE + sapwood tracking.

1. Read `tmp/iter38_solve.log`: the pinned **C_NDEF** and the gate `d log M/d log C` (PASS ≈2.67, REFUTED ≫10).
2. If gate PASSES: `python3 scripts/plane_bench.py --set C_NDEF=<root> --out tmp/iter38_bench.npz` (5×{s,m,l},
   ~20-25 min). Judge: does S SETTLE (S(s)<1, S(m)=1, S(l)>1)? Does F_S track census UPWARD at l?
3. If PASS on both → freeze C_NDEF in `plane_grower.py` (replace the `None`) and commit.
4. **⛔ PRE-REGISTERED STOPPING RULE (iter-37):** this is Position B's ONE shot. If C sits near a bifurcation
   (conditioning ≫10) OR S fails to settle OR sapwood doesn't track → **refutation #6.** Do NOT open a 7th
   loop. Hand back to Chris: make R_TIP an allometric PRIOR (census/WBE-shaped), imposed like the pipe.

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
