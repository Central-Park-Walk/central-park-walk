# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-39: BRANCH B. The sapwood deficit is AGE-STRUCTURAL, not a TAU_SHED loss-rate.

TAU_SHED swept 0.18→0.12 on the S≡1 baseline (`C_NDEF=None`, every rec `S=1.0`; R_TIP untouched). Paired
by seed (cancels the ~80% seed spread): sap_frac responds at the MEDIUM tree (+6.9 pts, RESOLVED) but is
**noise at the LARGE tree** (+1.4 ± 3.8) — exactly where the deficit is worst (0.33× census). The deficit
DEEPENS with age (0.58→0.40→0.33×) and τ's power to fix it VANISHES with age. Where τ works it RETAINS
SAPWOOD (F_S +40), never drains heartwood (F_H Δ noise). At l, F_H≈778 is 104 yr of irreversible pile — no
shed-*rate* drains it, because F_H is cumulative-forever with `c_H=c_S`. **The knob is powerless; the
defect is the heartwood MODEL.** (τ=0.06 run OOM'd mid-flight — crown never prunes → runaway; itself a
Branch-B symptom. Verdict robust without it. Bench: `tmp/iter39_tau0{18,12}.npz`, report `tmp/iter39_report.txt`.)

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** /n_tips divisor dropped; n_tips 135–215.
2. **★★★ SAPWOOD DEFICIT — RE-CLASSED (iter-39): NOT a knob we own.** Not size-law (Position B refuted #6),
   not loss-rate (TAU_SHED powerless at l). It is the Aye-2022 heartwood MODEL choice `c_H=c_S`. ← now a
   CANONICAL question for Chris, not an iteration (see NEXT). Do NOT open a 7th tuning loop on it.
3. **★ SIZE-LAW / R_TIP-as-PRIOR — DEAD.** Emergent S=C·M^q refuted (#6). Imposed R_TIP prior is a HACK
   (per-species census lookup, un-generalizable). Not to be revisited. S≡1 baseline ships (l DBH 1.25×).

## NEXT — CHRIS'S CALL (canonical, ADR-worthy). Does old disused pipe stay at full bore `c_H=c_S` forever?

Real heartwood is embolised/occluded — it does not conduct. iter-39 proved no knob we own fixes the
age-structural sapwood deficit; the question is whether the deficit is a DEFECT or REAL biology. Three
distinct positions to weigh (write the ADR before coding any):
- **(A) Keep `c_H=c_S`.** Accept sap_frac falls with age as real, and VALIDATE against a census
  sapwood-area-vs-age curve BEFORE calling it a defect at all. (Cheapest; may dissolve the "defect".)
- **(B) `c_H = k·c_S`, k<1** — heartwood carries reduced area. But k is a DERIVED quantity needing a
  published source (Aye 2022 / pipe-model literature on disk), NOT a fitted knob. Output-as-parameter risk.
- **(C) Revisit shed-to-heartwood** — should shed terminals ever have contributed full-bore pipe area?
  Ties to iter-29's c_H/c_S "leak's-twin" derivation.
⚠ Do NOT re-pin C, re-open shade, touch R_TIP, or adopt the R_TIP prior — all closed/refuted. First act
of the next session is the ADR + reading the on-disk Aye-2022 heartwood section, not code.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ q/K & HEART_RATIO ARE OUTPUTS.** `Q_MASS=2/E_M`, `c_H=c_S` — DERIVED, not knobs. `C_NDEF` stays
  `None` ON PURPOSE (refuted, not the iter-34 no-op trap). Emergent R_TIP overshoots BECAUSE q is un-tunable.
- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES** (36/37) — the fold lived in the DYNAMICS, not the identity. DEAD.
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, re-proved iter-39) — the raw two-means
  τ comparison was unresolvable; pairing by seed made it a tell. `plane_bench.py` 5×{s,m,l} ≈ 25 min/run.
- ⚠ **HARNESS (iter-39):** a subagent that BACKGROUNDS its bench then exits orphans the job from the parent's
  notifier — recover with one harness-tracked waiter on the PID, never poll. τ=0.06 OOM'd at `--jobs 8`.
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022 (heartwood), Hellström 2018, WBE. APPEND-ONLY.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
- **Distilled 2026-07-15** (commit 45043f1, maintenance): staged lessons 34–39 promoted to global rules
  (rails #44 "gain every loop" + the harness/orphan note are now Tier-0), raw → `ledger_archive/2026-07.md`.
  No science changed; iter-39 Branch B + the `c_H=c_S` NEXT question stand.
