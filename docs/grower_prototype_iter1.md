# London plane developmental grower — F6 prototype, ITERATION 1

**Status: prototype RUNS; mechanisms wired and topologically correct; 3 real bugs found &
fixed; 5 F6 criteria PARTIALLY met with specific diagnosed shortfalls. Awaiting review.**

Design of record: [`grower_reiterate_design.md`](grower_reiterate_design.md) (F7 = both birth
modes, F1 amendment ratified 2026-07-10). Code: `scripts/plane_grower.py` (new, isolated — the
frozen `leafback_skeleton.py` is untouched). Measurement + render harness: `tmp/grower_measure.py`
(gitignored). Renders: `tmp/grower_iter1_{s,m,l}.png`.

This is the F6 gate: **prove the year-stepped process on the m-tier skeleton, leafless, before
any mesh / perf / cards.** It is deliberately not a finished tree.

---

## What the grower does (per design)

A year-stepped developmental simulation. Each year every living axis grows one **annual module**
(§8, GAP-RHYTHM: a module = one year, monocyclic); the apex aborts and the distal-most lateral
**relays with a small kink** (the only source of crookedness). Laterals are emitted
**acrotonically** in the module's distal spiral zone (§4); most axillary buds stay **dormant**
(proleptic — available to Mode-2 later). Firing is by **relay dominance `D`** (§2): `D` decays,
and when it crosses `Φ_fork` the axis **forks into 2–3 co-equal reiterates and ends** — *a fork
IS a reiteration*. `D` resets lower each wave and terminates the recursion at the periphery (`D→0`,
so `max_order` is an OUTPUT). Radius is the **pipe-model ratchet** (§5, monotone max over history —
a shed limb keeps its girth in every ancestor). Posture is by **category** (§7: A1 orthotropic;
A2–A5 plagiotropic set-point + sag − righting). A **shadow-propagation light grid** (F1) drives the
**shed rule** (§7.3: `light/size < τ` → shed subtree, keep radius) and modulates `D`. Both **birth
modes** are implemented (F7): `TERMINAL_FORK` (crown builder) + `LATENT_BUD` (old-wood re-erection).

**F6 scope decision (recorded):** the prototype grows the **woody armature only — A1 trunk,
A2 primaries, A3 secondaries** (`MAX_CAT=3`). The A4/A5 short-shoot + twig layer is the
space-filling FOLIAGE layer (design §7.1, §9.2) and is deferred; being **leafless**, the terminal
A3 tips are the light-gathering proxy.

---

## Three real bugs found and fixed (this is what iter-1 is for)

1. **Over-ramification (124 k live nodes).** Growing an axis at *every* spiral-zone axil down
   through A5 gave ~7^order explosion. Fix: `BRANCH_GRADE` (a small number of buds release per
   module; rest dormant) + `MAX_CAT=3` armature scope. → sane node counts.
2. **Runaway vertical growth (tree reached ~30 m at H=14.4).** Reiterate leaders were gated by the
   *seedling's* 6-year AU-establishment window and had no height bound. Fix: short establishment
   for reiterate leaders (`REITER_MIN_AGE`) + crown-envelope **soft height cap** driving `D→0` as
   the apex nears H (§6). → height bounded.
3. **★ Floating-crown islands (zombie axes).** `_kill_subtree` marked shed *nodes* dead but not the
   `Axis` objects inside the subtree; those zombie axes kept growing, appending live nodes onto dead
   parents — a crown of disconnected islands that *looked* full but was a topology artifact. Fix:
   shedding now also kills every axis whose apex it severs. **This is the integrity-trace lesson in
   action** ([[lessons_critic_role_pipeline]]): the pretty render was wrong; component-tracing caught
   it. Use a connectivity check, never gestalt.

---

## The five F6 criteria — honest scoring

| # | criterion | verdict | evidence |
|---|---|---|---|
| (i) | emergent primary count + heights | **PARTIAL** | count emerges (s 14 / m 12) but skews to many low limbs; no distinct 2–3 master fork yet (C&E predicts 2–3). Not tuned to a number (F5 respected). |
| (ii) | AC-14 caliber gradient EARNED | **PARTIAL–GOOD** | taper along a limb is real & visible (trunk 190 → primary 64 → twig, all from the ratchet, nothing imposed). Across-primary *lower=thicker*: **s tier corr −0.62 ✓**; m tier not differentiated (primaries cluster low, co-equal). |
| (iii) | clear bole from shedding | **PARTIAL** | a bole emerges from the shed rule (mechanism works, cb is an OUTPUT) but too low: cb_frac s 0.14 / m 0.10 vs measured ~0.30. |
| (iv) | crooks at module boundaries | **MECHANISM ✓, magnitude GAP** | turning is concentrated at year nodes (2.3° at boundary vs 0.00° interior). Correct by construction; 2.3° reads straight — but `θ_relay` is an un-closed GAP (Genoyer), not a free knob. |
| (v) | emergent DBH vs census | **NOT YET** | iter-1 IMPOSES DBH via the fit scalar (fits median exactly, trivially). F2's emergent-DBH + census-shape check needs the ratchet un-rescaled + all 3 tiers; deferred to iter-2. |

Cross-tier (leafless armature, one seed):

| tier | H | DBH(fit) | live nodes | primaries | cb_frac |
|---|---|---|---|---|---|
| s (young, 12 yr) | 10.0 | 7.0 in | 4 800 | 14 | 0.14 |
| m (middle, 20 yr) | 14.4 | 15.0 in | 6 524 | 12 | 0.10 |
| l (mature, 35 yr) | 22.0 | 28.0 in | **86** | 0 | — |

## ★ The #1 iter-2 blocker: the shed rule is not in EQUILIBRIUM

The l tier (35 years) **collapses to 86 live nodes** — a bare stick. The longer the run, the more
shedding wins: it is a slow one-way ratchet toward bare, not a sustainable crown. The same collapse
produced the earlier m-tier 129-node run before the light budget was softened. **The light↔shed↔D
loop must reach a standing-crown equilibrium** (a shed limb is replaced by new growth at the lit
periphery) rather than monotonically stripping the tree. This is the top thing iter-2 must fix, and
it gates a believable l-tier veteran (the *arbre du passé*, where `LATENT_BUD` and the arch cascade
live).

## Other iter-2 targets (all diagnosed, none mysterious)
- **Clear bole too low** (0.10–0.14 vs 0.30): low A2 laterals survive that should be shed; couples to
  the shed-equilibrium fix (τ, shadow strength, and the height at which `D` first collapses).
- **First fork too low / into thin secondaries** rather than 2–3 thick masters: the trunk's `D`
  collapses by ~age 6 (self-shading of the apex), so `Dchild < D_STOP` → the first fork is already
  pauperized. Want the trunk to hold dominance longer and fork into a few **cat-1 masters**.
- **Limbs too straight / weak arch**: posture (sag−righting) is wired but produces little visible
  curvature at this scale; the arch **cascade** (§7.2, reiterate-at-arch-summit + dieback) is not yet
  exercised. `θ_relay`, `θ_GSA`, and the sag/righting constants are all GAPs (Genoyer / Huang).
- **Crown open/vase, not domed**: expected — the A4/A5 foliage/twig layer that fills the dome is
  deferred (F6 scope). Re-judge crown fill only once that layer is added.

## What is genuinely established
The year-stepped process **runs, is bounded, is topologically connected, and produces a legible
trunk→primary→secondary hierarchy with earned taper and an emergent (if low) clear bole** — from
mechanism, not authoring. The "pom-pom of equal sticks" and "garden-hose arc" are gone. Every number
that is not from Caraglio & Édelin is labelled `[PROV]`/`[GAP]`; the outputs above are predictions to
be checked against the census and Genoyer 1999, not tuned results.

**Next:** review this checkpoint, then iter-2 = the shed-equilibrium fix (top priority), higher/
stronger first fork into masters, and the DBH-emergent + census-shape validation. No mesh / perf /
cards until the five criteria pass on the skeleton.
