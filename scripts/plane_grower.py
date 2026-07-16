#!/usr/bin/env python3
"""London plane DEVELOPMENTAL GROWER — year-stepped skeleton simulation (F6 prototype, iter 1).

Design of record: docs/grower_reiterate_design.md (F7 = both birth modes, F1 amendment
ratified 2026-07-10). This is the object-model realisation the design gates on.

★ WHAT THIS IS. A *process*, not a snapshot (standing Rule 3). The crown shape, primary
count, clear bole, caliber gradient and DBH are OUTPUTS of running the tree's growth over
developmental YEARS — none of them is a parameter. Contrast the frozen one-shot
`leafback_skeleton.py::build_trunkscaffold`, which imposed N_PRIMARIES, cb_frac, DBH and a
hand-weighted caliber partition (AC-14's `w^(p/2)`, now DELETED as a "clock substitute").

★ SCOPE (F6). m tier only, LEAFLESS, skeleton only. No mesh, no perf gate, no cards. The
skeleton is emitted in the same (pos,parent,radius,strand,root) shape the skinner consumes,
so a later stage can skin it unchanged — but skinning is out of scope here.

★ MECHANISMS (each cites the design section):
  §8  annual MODULE = one year (GAP-RHYTHM closed: plane monocyclic). A module lays down
      GU_length metamers; at the year boundary the apex ABORTS and the distal-most viable
      lateral relays with a small kink — the ONLY source of natural crookedness.
  §4  ACROTONY: laterals are emitted at the axils of the module's distal spiral zone; the
      most distal is the relay, the sub-jacent ones the plagiotropic tier.
  §2  FIRING via RELAY DOMINANCE D. A FORK *IS* A REITERATION. D rises (establishment),
      then falls; when D < Phi_fork the single relay is replaced by 2-3 co-equal relays,
      each a reiterate; the bearing axis ENDS. D resets high per wave, lower each time -> 0
      at the periphery, so max_order is an OUTPUT (loop guard only).
  §1.1 the AU: A1 orthotropic trunk; A2/A3/A4 plagiotropic (module length 15/10/7/5 nodes,
      C&E-measured); A5 = short shoot (space-filling twig, sheds fast).
  §3  TWO BIRTH MODES (F7=both): TERMINAL_FORK (at an axis tip; start_order = the forking
      axis's own rung; builds the crown) + LATENT_BUD (on old wood/arch summits;
      start_order = s(u_ins) positional pauperization law; ages the tree).
  §5  the pipe-model RATCHET: radius = max over history, never decreases when a subtree is
      shed. This is what lets a low limb EARN a thick bare bole (AC-14, earned not imposed).
  §7  posture by CATEGORY (light does not steer): A1 orthotropic; A2-A5 plagiotropic
      set-point + self-weight sag - reaction-wood righting -> the ascend-then-arch profile.
  §7.3 SHED rule: light_gathered(subtree)/size < tau -> shed (keep ancestor radius). Produces
      the clear bole (cb_frac output), the open interior, the woodland form.
  F1  light (shadow-propagation voxel grid, Palubicki) modulates BOTH the shed gate AND D
      (env_release). It does NOT steer a limb's direction.

★ EVERY plane number we do not have is a labelled GAP / [PROV]. Outputs are PREDICTIONS to
be checked against the census (DBH) and Genoyer 1999 (staging), not tuned results.

Runs in SYSTEM PYTHON (numpy + scipy; scipy HANGS in Blender's bundled Python — the
documented gotcha). Frame is y-up (like leafback_skeleton); the generator rotates to z-up.
"""
import math
import numpy as np
from scipy.spatial import cKDTree, ConvexHull
from scipy.spatial import QhullError

# ---------------------------------------------------------------------------
# PARAMETERS.  measured = from Caraglio & Edelin 1990 (C&E).  [PROV]/[GAP] = not known
# for Platanus, provisional, MUST be reported as such and never presented as a result.
# ---------------------------------------------------------------------------
PIPE_POWER = 2.3          # da Vinci exponent (reused from leafback line; [PROV] for plane)
R0         = 0.004        # 4 mm terminal-bud seed radius (reused)
# ★ iter-5, residual (v): the SINGLE fitted scalar for EMERGENT DBH (§5.3, F2). Physically = the
# deferred A4/A5 foliage layer each leafless A3 tip stands in for. [FIT]
# ★ iter-9: REFIT, jointly with ALPHA, at the CENSUS-DERIVED tier ages. The old 4.37 was fitted so
# the m tier hit the census median DBH -- but it was fitted at a 20 yr m tier, and the m tier is
# really ~40 yr (see grow_tier). At the true age the same 4.37 left the trunk 3x TOO THIN (0.34x).
# The refit is a DERIVATION, not a search: R_TIP prices extension (l_afford = v/(n*pi*R_TIP^2), and
# it seeds the pipe model, so under R_TIP -> k*R_TIP with ALPHA -> k^2*ALPHA the cost per unit
# length is unchanged => length/height/crown are INVARIANT while every radius scales by k. DBH was
# 0.34x => k = 2.94. Verified: m DBH 14.7 -> 43.0 cm = 1.00x target, H and span held.
DBH_CALIB  = 3.813        # [DERIVED] 12.85 / 3.37; see the iter-17 block below.
# ★★ iter-17 — THE RE-CENTRING, AND IT IS A DERIVATION, NOT A SEARCH. The iter-9 refit above was
# made against a grower with NO HEARTWOOD. Iters 12-14 then added the heartwood ratchet, which lays
# down wood the iter-9 fit had no way to know about, and nobody re-centred: measured, the pipe came
# out 5.15 / 3.37 / 3.36x the census DBH. The SAME invariance the iter-9 refit rode on runs in
# reverse -- R_TIP -> k*R_TIP with ALPHA -> k^2*ALPHA leaves the cost of a unit of extension
# (l_afford = v/(n*pi*R_TIP^2)) unchanged, so length/height/crown are INVARIANT, the economy is
# preserved EXACTLY, and every radius scales by k. Every cross-section in the model is homogeneous
# of degree 2 in R_TIP (c_S == pi*R_TIP^2 seeds the pipe; C_HEART == HEART_RATIO*pi*R_TIP^2), so
# this is exact, not approximate -- with ONE exception, and it is the entire point: the mechanical
# radius r_mech = (4M/pi.sigma)^(1/3) does NOT scale with k, because SIGMA/GRAV/RHO_GREEN carry an
# ABSOLUTE LENGTH SCALE. The transform is exactly economy-preserving only while the support bill is
# zero -- which iter-16 measured it to be. So k = 1/3.37, taken from the m (calibration) tier.
# ⚠ IT DOES NOT FIX DEFECT 1 AND IT IS NOT ASKED TO. A scalar slides all three tiers together; it
# can only CENTRE the two-sided splay, never cure it (l. 121). What it is asked to do is STOP HIDING
# it: statics is the ONLY law in this model with an absolute length scale, and a 3.4x-too-fat pipe
# drowns it (see the iter-16 block at l. 252). This re-centring is the falsification instrument.
# ★ iter-8: DBH_CALIB is applied AT THE TIP, not as a post-hoc multiply in finalize(). The two are
# EXACTLY equivalent -- the pipe model r=(SUM r_c^p)^(1/p) is homogeneous of degree 1 in the tip
# radius, so seeding every tip at k*R0 scales every radius by k -- but the tip form says what the
# constant physically IS: one armature tip stands in for DBH_CALIB^PIPE_POWER real A4/A5 tips.
# This matters now, because the mechanical radius (below) has to be compared against the pipe radius
# the tree ACTUALLY BUILDS. Against the post-hoc-multiplied one that comparison cannot even be
# written down; against the raw one it is wrong by DBH_CALIB. See docs/grower_prototype_iter1.md.
# ⚠ THE ONE OPEN DEFECT (iter-9, sharpened by iter-10): R_TIP is a CONSTANT, but the deferred A4/A5
# system it stands in for is NOT. At the calibrated DBH_CALIB, one armature tip is priced as
# DBH_CALIB^PIPE_POWER real twigs. ⚠ iter-22: this line USED to read "12.85^2.3 = ~354", which was
# true only until iter-17 REFIT DBH_CALIB to 3.813. The live value is 3.813^2.3 = ~21.7 real twigs
# per armature tip. Every RATIO in iters 15-21 is unaffected (the factor cancels), but any ABSOLUTE
# twig count quoted from before iter-22 is 16.3x too large. It is a MATURE-CROWN number applied to
# every tip of every tree at every age, and that is still the defect.
# It is one scalar with two consequences, because R_TIP both seeds the pipe model AND prices
# extension (l_afford = v/(n*pi*R_TIP^2)): too-fat tips make the bole too thick AND make every
# internode too expensive to buy.
#
# ★ iter-10 MEASURED THE RESIDUAL AND IT IS TWO-SIDED, which is the real finding:
#     s (15 yr): DBH 1.96x  -- the young tree is too THICK
#     l (104 yr): DBH 0.73x -- the old tree is too THIN
# A constant N_def over-serves the sapling and under-serves the centenarian, in one monotone
# direction. So the fix is not a category lookup and not a smaller constant -- it is that N_def must
# GROW, and any mechanism that makes it grow correctly must push s DOWN and l UP with the SAME term.
# That is a far stronger falsification target than either defect alone; a fix that only mends s is
# refuted on l for free.
# ⛔ Do NOT "fix" this by lowering DBH_CALIB -- that scales every radius at once and re-breaks m/l.
# ⛔ Do NOT re-propose r_tip ∝ n_foliage^(1/p): already falsified on paper (every LIT tip carries the
#    same FOLIAGE_PER_TIP*FOLIAGE_LIFE = 12 markers, so it thins only SHADED interior tips -- it
#    would hurt m/l and do nothing at all for an all-lit sapling).
# ⛔ Do NOT propose "N_def ACCUMULATES with a tip's own age" (an old limb builds up a short-shoot
#    spray, a new shoot has none). It has the right two-sided sign and it is REFUTED BY OUR OWN
#    SOURCE: C&E measure A4/A5 short shoots SELF-PRUNING IN 1-4 YEARS (it is why FOLIAGE_LIFE=3
#    exists at all). The deferred spray reaches STEADY STATE in ~4 yr; it cannot accumulate for
#    decades. Refuted on paper, iter-10, before any code. Do not re-derive it.
#
# ⇒ N_def per tip really may be ~constant. Then the residual is NOT in R_TIP but in n_tips: since
#   DBH = 2*R_TIP*n_tips^(1/PIPE_POWER), s is carrying ~4.5x too many armature tips for its size and
#   l about 2.1x too few. THAT was the iter-11 question -- and iter-11 MEASURED IT AND IT IS WRONG.
#
# ★★★ iter-11 — THE TIP BUDGET IS NOT THE DEFECT. THE PIPE LAYER IS. (tmp/iter11_tip_budget.py)
# The "l has 2.1x too few tips" claim was read off the PIPE layer's own demand -- it assumed the pipe
# model, then blamed the budget for not feeding it. Measured against an INDEPENDENT ground truth (the
# real crown's twig count, from leaf area: LAI * crown area / (leaf_area * leaves_per_twig), which
# touches no pipe-model constant), the armature's tip budget is basically RIGHT where it was accused:
#     s 2.37x too many | m 1.47x | l 1.14x  (8 seeds; but n_tips seed spread is ~100%, so only s is
#                                            outside the instrument -- l is indistinguishable from 1)
# ⛔ So the shed rule, MAX_CAT and the reiteration rate are NOT indicted. Do not touch them for this.
#
# THE PARAMETER-FREE TEST, and it is the whole finding. Hand the pipe layer the TRUE twig count and
# ask what DBH it says -- DBH = 2*R0*N^(1/PIPE_POWER), R0 = 4 mm is a physical bud radius and
# DBH_CALIB cancels, so not one fitted constant is in play:
#     s 1.36x  |  m 0.87x  |  l 0.68x
# The two-sided error SURVIVES A PERFECT TIP BUDGET. It is not in how many tips we grow. It is in
# what the pipe layer does with them.
#
# ★★ AND NO SCALAR CAN EVER FIX IT. R0, DBH_CALIB, R_TIP, a constant N_def are all UNIFORM
# multipliers on DBH -- they slide all three tiers together and can only ever CENTRE a two-sided
# error on the middle one. That is exactly what the iter-9 refit did (and it was right to: at the
# time, pre-clock, the error was same-sign 0.34x on both m and l). Once an error splays either side
# of the calibration tier, the remaining fix must be SIZE-DEPENDENT. That is a statement about the
# RANK of the fix, and it is what makes this a much narrower target than "some mechanism".
# The exponent that WOULD reconcile census DBH with real leaf area, s->l, is p = 1.37, not 2.3.
# ⛔ And LAI cannot rescue p=2.3: it would have to run 2.45 -> 6.96 -> 12.18 across the tiers. The
#    literature range for plane is 4.0-6.0, and LAI 12 is closed-canopy rainforest. Refuted.
#
# ⇒ THE PIPE LAYER HAS NO HEARTWOOD, and that is the one size-dependent term it is missing. The pipe
#   model (Shinozaki) says SAPWOOD area tracks leaf area. This grower equates the WHOLE cross-section
#   with sapwood, so its trunk IS its plumbing. A real trunk is plumbing PLUS a dead heartwood core,
#   and the heartwood fraction GROWS with age -- which is precisely why real leaf area scales as
#   ~DBH^1.4 and not DBH^2.3. It makes an old trunk thicker than its pipes (l: 0.68x too thin) while
#   a sapling, nearly all sapwood, stays close to pure pipe. That is the iter-12 hypothesis, it has
#   the right two-sided sign, and it is PUBLISHED, not invented. Derive it before coding it.
#   ⚠ The `s` residual is a SEPARATE, SMALLER defect and probably not heartwood at all: a constant
#     R_TIP floors DBH at 2*R_TIP = 10.3 cm for ANY tree at ANY age, and s's whole census DBH is
#     12.7 cm. The sapling is pinned near the floor. Do not expect one term to mend both.
R_TIP      = DBH_CALIB * R0     # effective terminal-bud radius (= the deferred tips' worth)

# ★ iter-14: c_H — THE SECOND PIPE-AREA CONSTANT (Aye, Brännström & Carlsson 2022, Eq. 6; their
# Table 1 fits c_S and c_H SEPARATELY). See ratchet(). c_S is not a free constant here — the pipe
# model is seeded at the tip, so c_S == pi*R_TIP^2 (one live leaf unit's worth of pipe). c_H is the
# area of DISUSED pipe a LOST leaf unit walls off as heartwood, and it is expressed as a ratio to
# c_S because that is the only thing the pair means physically: the heartwood a dead unit leaves
# behind, per pipe it once fed. iter-12's "no new constant" was FALSE — the paper carries two, and
# assuming c_H == c_S (a dead pipe frozen at its full living bore) is a CHOICE, not the paper's.
# ★ It is NOT a fitted knob, and iter-14 declined to use it as one. Two independent routes pick the
# same value: (a) the paper's own physics — "pipes that previously connected discarded leaves or
# branches FORM the heartwood", i.e. it is the SAME pipe, disused, so c_H == c_S and their Table 1
# fits the pair separately only to absorb per-dataset scaling; (b) the CENSUS — solving the model
# for the measured m->l basal-area growth (43.2 -> 71.1 cm DBH, x2.71 in area) demands
# c_H/c_S = 1.07. Fitting c_H to the 50% sapwood target instead would demand 0.049 — the two ground
# truths pick c_H 22x apart, so ONE constant cannot serve both and this one is already spoken for.
# ⛔ Do NOT turn HEART_RATIO down to buy sapwood fraction. That is the fit the census forbids, and
#    the deficient term is the LIVE crown, not the dead bank. See STATE.md (iter-14).
# ★★ iter-32 — THE 22x DISAGREEMENT ABOVE IS A STRUCTURAL FALSIFICATION, AND IT HAS NOW BEEN READ.
# Splitting the basal area (n=5 bench, tmp/iter31_bench.npz) puts BOTH halves resolved-wrong, in
# OPPOSITE directions: SAPWOOD area 1.32 / 0.45 / 0.51x census (s/m/l), HEARTWOOD area 3.30 / 1.77 /
# 2.63x. They partly cancel, which is the only reason DBH ever read as a mild 1.05x at m.
# ⇒ route (b) above is CONTAMINATED: it solved for m->l basal-area growth while the model's sapwood
#   was carrying half its share, so the fit handed the missing growth to c_H. A CONSTANT FITTED
#   AGAINST A LEAK IS THE LEAK'S TWIN (iter-29). c_H/c_S = 1.07 is the twin; it is NOT independent
#   corroboration of route (a), and the two routes never agreed in the first place.
# ⇒ iter-14 was HALF right: the live crown IS deficient (0.5x sapwood, flat in size) -- and the dead
#   bank is ALSO over-full (1.8 -> 2.6x, worsening in size). TWO terms, two different laws.
# ⛔ Still do NOT tune HEART_RATIO. Route (a) — the paper's physics — is untouched by any of this:
#    Shinozaki 1964 Fig.8 says the disused pipe is the SAME pipe. Fix what FEEDS the bank (the rate
#    of leaf-unit loss), not the price of a unit in it.
HEART_RATIO = 1.0         # [DERIVED] c_H == c_S — the same pipe, now disused. See above.
C_HEART     = HEART_RATIO * math.pi * R_TIP ** 2      # c_H: heartwood area per LOST leaf unit
# ★ iter-42 — RING-AGE HEARTWOOD (Track B). Aye's branch-death bank alone (c_H·F_H) is the paper's
# OWN "no reusable pipes" artifact (§Discussion): a living trunk with few dead branches gets ~0
# heartwood, when biology says its innermost rings are already a dead core. Björklund 1999: sapwood
# lives ~tau YEARS (decoupled from the 3-12 yr leaf life), then ages into heartwood REGARDLESS of
# branch death. So the true sap/heart split is by RING AGE: sapwood = the wood laid down in the last
# TAU_HEARTWOOD years (the outer rings); everything older is heartwood. This RE-PARTITIONS the
# built cross-section the ratchet already produced -- it adds NO wood and does NOT touch DBH/economy
# (sap_frac is absent from the gate, iter-40). tau is a DERIVATION, not a free knob: fitted ONCE so
# the mature l-tier (104 yr, the census-representative plane) reads ~50% basal-area sapwood -- the
# ONE robust allometric target (Platanus = WIDE sapwood, ~50%). Sanity anchor: Björklund ~60 yr
# (pine). ⚠ THE ANCHOR WAS WRONG: "wide sapwood" is a WIDTH/AREA fact (many conductive rings), NOT a
# YEARS fact. A vigorous plane lays down wide rings, so it reaches wide sapwood in FEWER years than slow
# pine -- do not expect tau >= 60. The census (50% basal area) is the direct target and it wins. s (15
# yr < tau) -> ~0 heart and m (47 yr) -> some core then fall out as OUTPUTS, never retuned (the
# <=1-tuned-param hack-test). Whether ONE tau lands all three tiers is the iter-43 census overlay.
TAU_HEARTWOOD = 34        # [DERIVED iter-42] l-tier (104 yr) reads 50% basal-area sapwood at tau=34: its
                          # trunk hit sqrt(0.5) of final girth at yr 69/104 (near-linear radial growth).
                          # 2x below Björklund's ~60 yr (pine) -- see the corrected anchor note above.
# ⚠ iter-15: R_TIP and C_HEART above are now only the REFERENCE (anchor) values. The live ones are
# self.r_tip / self.c_heart, which ride on N_def(t). See the N_def block immediately below.

# ======================================================================
# ★ iter-15 — N_def: WHAT ONE ARMATURE TIP STANDS FOR, AND IT IS NOT A CONSTANT
# ======================================================================
# THE DEFECT (iter-14's finding; measured in docs/grower_saturation_diagnosis.md). The economy is
# SCALE-FREE IN TIPS. Each armature tip carries FOLIAGE_PER_TIP*FOLIAGE_LIFE = 12 foliage markers, so
# income per apex = ALPHA*12*Lbar — independent of n_tips — while cost per apex = n*pi*R_TIP^2*
# INTERNODE is ALSO independent of n_tips. Income ∝ tips, cost ∝ tips: THEY CANCEL. No growth term in
# the tip count exists anywhere in the model, so it sits at iter-9's fixed point for ever (8–25 tips
# from yr 20 to yr 104, with 30–50% of apices dormant at every age) and the live crown SATURATES:
# F_S grows x1.32 from m to l where the census demands a x2.71 basal area.
#
# THE LAW. Hellström, Carlsson, Falster, Westoby & Brännström 2018, "Branch Thinning and the
# Large-Scale, Self-Similar Structure of Trees", Am. Nat. 192(1):E37–E47 (doi:10.1086/697429) — the
# branch-thinning companion to the Aye/Brännström/Carlsson 2022 pipe-and-heartwood paper the ratchet
# already builds on. Local copy: tmp/papers/hellstrom2018_branch_thinning.pdf (gitignored).
#
#     K(n) = alpha*(n+1)^d              (their Eq. 1)  the branch CARRYING CAPACITY, in tips
#     b(n) = min{mu^n, beta*(n+1)^d}    (their Eq. 4)  tips actually borne by a branch of age n
#
# A branch multiplies its tips by mu each growth cycle and then THINS back to its capacity, so in the
# thinning region the tip count is a POWER LAW IN AGE. Fitted to Wilson (1966)'s red maple long-shoot
# counts (their Fig. 8 — the paper's only broadleaf): beta = 6.69, d = 1.44, mu = 1.42, R^2 = 0.98.
# Over OUR census ages that law predicts an m->l tip growth of (105/48)^1.44 = 3.09x, against the
# 2.71x basal-area growth the census independently demands. That is the growth term we are missing.
#
# ⛔ AND WE DO NOT IMPLEMENT IT AS (n+1)^d. Taking K(n) as a lookup on age would make DBH an ANALYTIC
# FUNCTION OF AGE — a parameter wearing an output's clothes, which is the mistake this project has
# now made four separate times (docs/standing_rules.md). The paper itself forbids it, in as many
# words (Discussion, p. E45): "The phenomenological carrying capacity assumed here is in reality
# realized through other factors, such as light or nutrient limitation." We HAVE a light field. So we
# realize the capacity through SPACE AND LIGHT, and Hellström's b(n) becomes the VALIDATOR, not the
# input:
#
#     N_def(t) = TWIG_DENSITY * V_crown(t) / n_tips(t)
#
# The deferred A4/A5 twig system one armature tip stands for is the twigs that FIT IN THE CROWN
# VOLUME THAT TIP OWNS. V_crown is the occupied-voxel volume of the live foliage cloud (read straight
# off the light grid we already build) and n_tips is the live leaf-unit count. Both are EARNED by the
# economy, so N_def is an OUTPUT. Total real tips = N_def*n_tips = TWIG_DENSITY*V_crown: the crown
# fills the space it can reach, its own shade closes the interior, and a carrying capacity EMERGES.
# Simulate the process; let the appearance emerge.
#
# ★ IT ENTERS THE LIGHT, NOT JUST THE LEDGER. Until now N_def sat only on the COST side (R_TIP =
# DBH_CALIB*R0) and in the DBH/heartwood LEDGER: a tip paid 354 twigs' worth of wood to extend and
# earned ONE tip's worth of light. A ledger-only N_def cannot break the fixed point above, because
# the fixed point is an income/cost identity and the ledger is not in it. A tip that stands for N
# twigs must INTERCEPT N twigs' worth of light and CAST N twigs' worth of shade. Same term, both
# sides. Then income per apex ∝ N_def while cost per apex ∝ R_TIP^2 ∝ N_def^(2/p), and since
# p = 2.3 > 2 THE EXPONENTS NO LONGER CANCEL. The economy stops being scale-free.
#
# Everything rides on the RATIO S(t) = N_def(t)/N_DEF_REF, so S == 1 at the anchor and the entire
# iter-9 calibration (ALPHA, DBH_CALIB, SHADOW_A/B, TAU) is preserved there UNCHANGED — only the
# SHAPE with size is new. TWIG_DENSITY is therefore NOT a new degree of freedom: it is pinned ONCE by
# demanding S(m-tier) = 1. It RE-EXPRESSES DBH_CALIB; it does not re-fit it. (Defect 2 — the one
# legitimate re-centring of DBH_CALIB — is still owed, and still comes AFTER this.)
N_DEF_REF    = DBH_CALIB ** PIPE_POWER   # = 21.7 real twigs (3.813^2.3): what one armature tip stands
                                         # for AT the anchor. iter-8's reading of DBH_CALIB, unchanged
                                         # in FORM — but ⚠ the VALUE fell 16.3x at iter-17's refit. Do
                                         # not quote "354" from an old comment; recompute it.
# [DERIVED] twigs per m^3 of crown, pinned by S(m) = 1 against the iter-14 model at the m-tier age:
# TWIG_DENSITY = N_DEF_REF * n_tips / V_crown, measured at yr 47 by tmp/iter15_anchor.py.
# Measured 2026-07-13: at the m anchor the iter-14 crown is a 215.5 m^3 hull carrying 27 live leaf
# units, so one tip owns 7.98 m^3 and must stand for N_DEF_REF = 355 twigs => 44.5 twigs/m^3, i.e.
# ~9.6 A4/A5 tips per 0.6 m cube of crown. (tmp/iter15_anchor.py re-measures it.)
#
# ⛔ OFF — iter-15 REFUTED THIS NUMERATOR, and the refutation is specific: V_crown IS NOT EXOGENOUS.
# N_def is read off the live crown; income scales with N_def; income buys the extension that GROWS
# the live crown. That is a POSITIVE FEEDBACK LOOP ON INCOME, MEASURED FROM ITS OWN PRODUCT, and it
# is unstable in both directions — the m crown sprawled to 466 m^3 against a 215 m^3 baseline, and
# the l crown then collapsed (358 m^3, or 62 m^3 with S_IN_SHADE). Crown growth m->l came out x0.77
# where it must be ~x2.7. Turning S_IN_SHADE off tames the violence but NOT the loop.
# ⚠ The SIZE-DEPENDENCE ITSELF IS RIGHT AND IT IS NOT IN QUESTION: with N_def free to be SMALL for a
#   small tree (13 twigs, not 355), the s tier went 5.15x -> 1.15x of its census DBH. That is open
#   defect 4 — the constant-R_TIP floor — moving for the first time. Keep the mechanism; the numerator
#   is what must change. It must be a quantity THIS YEAR'S INCOME CANNOT BID UP. See STATE.md.
#
# ⛔⛔ iter-16 — AND IT CANNOT BE THE CANTILEVER EITHER. THE MECHANICAL TERM IS INERT.
# iter-15's successor plan was to read N_def off the self-support capacity: the twigs the already-built
# wood CAN HOLD OUT (N_cap ∝ r^3/lever, from Hellström Eq. 10's McMahon & Kronauer basis — "the branch
# radius r grows as branch length to the power 3/2 ... M_n ∝ r^2 ∝ n^3"). Settled wood, income cannot
# bid it up. It is refuted on TWO independent grounds, neither of which required coding it:
#
#   (a) ANALYTIC — the loop gain is > 1. The pipe sets r ∝ T^(1/p) = T^0.435 (T = real twigs), so a
#       capacity r^3/lever ∝ T^(3/p) = T^1.30 GROWS FASTER THAN THE LOAD IT CARRIES. Feeding that back
#       into N_def is a RUNAWAY, not a regulator — the same error as V_crown, one derivative up.
#   (b) MEASURED — tmp/iter16_mech_probe.py, all 3 tiers, every wood node, every year. Statics NEVER
#       BINDS: median r_mech/r_pipe = 0.14 / 0.20 / 0.23 (s/m/l), max 0.65 / 1.03 / 1.03, and on the
#       "load-bearing wood" (lever > 2 m) where iter-8 claimed 42-62% binding it now binds on 9/958 and
#       26/10917 nodes — 0.2%, and by 3%. _bill_total = 0.0000 is STRUCTURAL, not a wiring bug.
#
# ★ WHY IT WENT INERT, AND THIS IS THE LEAD: THE PIPE IS 3.4x TOO FAT (defects 2/3). r_mech only falls
#   as r_pipe^(2/3) where wood mass dominates the moment, and NOT AT ALL where leaf mass does. So a
#   census-correct pipe would raise r_mech/r_pipe by 1.5x at the bole and up to 3.4x on the distal
#   limbs — where the leverage is. The over-thick pipe has been SUPPRESSING the one law in this model
#   that carries an absolute length scale. Statics is the only non-scale-free thing we own; the pipe,
#   the light-per-marker and the tip budget are all scale-free. That is why iter-17 refits DBH_CALIB
#   FIRST, reversing the order STATE has held since iter-12. See STATE.md / LEDGER 16.
#
# ★★ iter-18 — THE BLOCK ABOVE IS SUPERSEDED ON BOTH GROUNDS. THE CANTILEVER IS ADMISSIBLE, AND IT IS
#    A MASS. (tmp/iter18_gain_probe.py; LEDGER 18.) Ground (b) died with iter-17: the pipe was re-centred
#    and statics now BINDS on 55-72% of load-bearing wood. Ground (a) died with one line of algebra:
#
#      r_mech^3 ∝ |V_i|   and   lever_i ≡ |V_i| / M_sub,i   (its own definition)
#      =>  N_cap ∝ r^3 / lever  ≡  M_sub,i      -- THE SUBTENDED MASS. THE LEVER CANCELS.
#
#    So "cantilever capacity" was never a third mechanism: it is the mass the node ALREADY HOLDS UP —
#    history, wood laid down in past years, which this year's income cannot bid up. Exogenous by
#    construction. And the gain follows from WHERE r IS READ, which is the whole of iter-16's error:
#
#      r from the PIPE:    r^3 ∝ T^(3/p)              => gain 3/p = 1.30   CUBE law   -> RUNAWAY
#      r from STATICS:     r^3 ∝ |V| ∝ mass ∝ T^(2/p) => gain <= 2/p = 0.87 SQUARE law -> REGULATOR
#
#    MEASURED (elasticity recursion over the converged fixed point, all 3 tiers, 127 binding tier-years):
#    mass-weighted gain 0.63-0.75, median 0.69, MAX 0.866 — and that ceiling is structural, since every
#    component elasticity is <= 1 (leaf 1.000 / pipe 0.870 / statics <= 0.667) and the moment is a
#    measured 96% WOOD. It cannot reach 1 while wood holds the tree up. => CODE THE TERM (iter-19).
#    ⛔ BUT NOT GATED ON "WHERE STATICS BINDS": statics binds in 2 of s's 16 years and NEVER at the bole,
#       and r^3/lever on a pipe-set radius is the 1.30 cube runaway rebuilt by accident. Code M_sub
#       DIRECTLY — defined at every node in every year, and equal to the capacity wherever statics binds.
TWIG_DENSITY = None       # ⛔ RETIRED (iter-15's refuted numerator). The V_crown route is gone; the
                          # constant is kept at None only so the refutation above has a name to point at.
#
# ★★ iter-19 — THE NUMERATOR, CODED. N_def ∝ M_sub, the mass the tree already holds up:
#
#     N_def(t) = MASS_CAP * M_sub_root(t) / n_tips(t)          S(t) = N_def(t) / N_DEF_REF
#
# so the tree's TOTAL real twig count is N_def*n_tips = MASS_CAP * M_sub — the twigs its standing
# wood can cantilever out, which is iter-18's `N_cap`, with the lever cancelled. M_sub is read off
# LAST year's converged structural fixed point (structural_radius), i.e. it is wood laid down in past
# years: EXOGENOUS to this year's income, which is the whole property V_crown lacked. Measured loop
# gain 0.69 (max 0.866, structurally < 1 while wood dominates the moment). Divide by n_tips exactly as
# iter-15 did: N_def is PER ARMATURE TIP, and the division is a NEGATIVE feedback (more tips => each
# stands for fewer twigs), never a positive one.
# ⛔ NOT gated on "where statics binds" — see the iter-18 block above. M_sub is defined at every node
#    in every year and EQUALS the cantilever capacity wherever statics binds; gating it on the binding
#    set puts r on the pipe and rebuilds iter-16's 1.30 cube runaway by accident.
MASS_CAP     = None       # ⛔⛔ RETIRED (iter-20). NOT a bad constant — A BAD NUMERATOR. No value of it
                          # exists. None => the iter-17 model exactly (DBH 1.43/0.93/0.94x census,
                          # sapwood 20.9/9.5/4.4%). Keep the term CODED so the refutation has a name.
#
# ⛔⛔ iter-20 — `N_def ∝ M_sub` IS STRUCTURALLY REFUTED. THE LINEAR-IN-MASS NUMERATOR HAS NO STABLE
#     INTERIOR FIXED POINT. Do not re-pin it, do not re-solve it, do not "just try a lower cap".
#
# ★ THE ALGEBRA, WHICH SHOULD HAVE COME BEFORE THE CODE (it is one line):
#
#       N_def * n_tips  ==  MASS_CAP * M_sub          <- THE n_tips DIVISION CANCELS IN THE TOTAL.
#
#   The tree's TOTAL real twig count — the thing that actually earns the light income — is therefore
#   proportional to ITS OWN STANDING MASS, with no n_tips in it at all. Income drives mass accretion,
#   so dM/dt ∝ MASS_CAP * M: a LINEAR POSITIVE FEEDBACK ON MASS whose rate constant IS MASS_CAP.
#   ⇒ The "negative feedback through n_tips" iter-19 leaned on is a REDISTRIBUTION, NOT A REGULATOR.
#   The only thing bounding the loop was self-shading — and shade is cast at MARKER resolution, so as
#   n_tips collapses the shade evaporates while the income does not. The regulator dies exactly when
#   it is needed.
#
# ★★ MEASURED (tmp/iter20_solve.py, closed-loop root-find on S(m@47yr) = 1, S_MIN already fixed):
#       MASS_CAP  2.1832 -> S(m)   0.58 | n_tips 100 | M_sub    628 kg
#       MASS_CAP  2.2105 -> S(m)   1.14 | n_tips  65 | M_sub    877 kg
#       MASS_CAP  2.2568 -> S(m)   9.73 | n_tips  12 | M_sub   1601 kg
#       MASS_CAP  3.1443 -> S(m) 1102   | n_tips   7 | M_sub  66648 kg   (a 66-TONNE "tree")
#   d log S / d log MASS_CAP ≈ 80-130 at the root ⇒ LOOP GAIN g ≈ 0.99, NOT the 0.69 of iter-18.
#   It is a TRANSCRITICAL BIFURCATION at MASS_CAP ≈ 2.205, not a calibration: below it the tree starves
#   onto the floor, above it it explodes. iter-18's gain was computed for ONE tip's radius; the loop
#   that actually runs is the WHOLE CROWN's leaf count against the WHOLE TREE's mass, and its gain is 1.
#
# ★★ AND THE THREE TIERS CANNOT BE SANE AT ONCE — the real killer (tmp/iter20_measure.py @ 2.2059):
#       s (15yr) DBH 0.52x census, S = 0.054 — STILL PINNED ON THE FLOOR, F_H = 0 (starved)
#       m (47yr) DBH 0.76x census, S = 0.769 — does not even reproduce its own solved root of 1.000
#       l (104yr) DBH 33.6x census (a 23.9 METRE trunk), S = 51817 — DIVERGED
#   A constant that gives the m tier its anchor detonates the l tier, BY CONSTRUCTION: bigger tree =>
#   more mass => more leaves => more mass. Age IS the bifurcation parameter. And note m's 0.769: at an
#   amplification of ~100, the fixed point is FINER THAN THE MODEL'S OWN NOISE. Unsolvable, not unsolved.
#
# ⇒ iter-21: THE NUMERATOR MUST BE SUB-LINEAR IN MASS. Total leaf ∝ M^q with q < 1 is the only shape
#   that can have g < 1 robustly (q is then a factor ON the gain, and the standard allometry puts leaf
#   mass ∝ M^(3/4) — WBE/Enquist, WHICH MUST BE OPENED AND READ BEFORE IT IS CODED, not cited from
#   memory). ★ COMPUTE THE LOOP GAIN OF THE WHOLE-CROWN LOOP, NOT ONE TIP'S, BEFORE WRITING THE LINE.
S_MIN        = 1.0 / N_DEF_REF   # = 0.046. ★ iter-20: A TIP CANNOT STAND FOR LESS THAN ONE REAL TWIG.
                          # The old 0.02 put N_def at 0.4 twigs/tip — not a small number, an incoherent
                          # one — and bound the sapling there for 16 years. Inert while MASS_CAP is
                          # None; it is the floor's DEFINITION, not a tuning knob, so it ships anyway.
#
# ★★ iter-36 — THE SUB-LINEAR NUMERATOR, CODED (ADR docs/adr_grower_size_law_numerator.md, Position A).
#     T_total = K_NDEF * M_sub^Q_MASS        N_def = T_total / n_tips        S = N_def / N_DEF_REF
#
# The linear MASS_CAP*M_sub form was a transcritical bifurcation at q=1 (iter-20). The fix, gated on
# paper BEFORE the line (ADR §2): make the crown's TOTAL twig count SUB-LINEAR in standing mass,
# T_total ∝ M^q with q<1, so the whole-crown loop gain g = d log I/d log M ≤ q < 1 (income I ∝ S·L,
# the n_tips cancels, self-shading makes light-per-marker non-increasing). Conditioning is then
# d log M*/d log K = 1/(1-q), FINITE — where the linear form's was ∞ (iter-20's measured 80-130).
#
# ⛔ Q IS AN OUTPUT, NOT A PARAMETER (the trap this project has fallen into 5x). q is the RATIO of two
#    measured structural exponents the model already owns — it is NOT the typed number 3/4:
#      · PIPE_AREA_EXP = 2 : area-preserving pipe, T_total = (r_base/r_tip)² ∝ r_base² (da Vinci /
#        Shinozaki 1964; the ratchet builds it). EXACT — a conserved cross-section, not a fit.
#      · E_M : the model's OWN measured mass–radius exponent, M_sub ∝ DBH^E_M. Measured (not typed)
#        from the iter-31 bench DBH × iter-34 m_sub read, 3 tiers, no new grow:
#            s: DBH 0.1927 m, M_sub  107.0 kg      m: DBH 0.4548 m, M_sub  1404.3 kg
#            l: DBH 0.8870 m, M_sub 14103.9 kg  ⇒  slope d log M/d log DBH = 3.199.
#    ⇒ Q_MASS = 2/E_M = 0.627. WBE/Enquist ideal (elastic similarity M∝r^(8/3)) gives 2/(8/3)=0.75 —
#    the SANITY BRACKET, not the input. Both < 1 with margin ≥0.25; the gate (conditioning ≈ 3-4),
#    not this exponent, is what certifies stability. ⚠ WBE paper flags real trees run steeper than
#    2/3 at small scale ⇒ we MEASURE E_M off the model, we do not type 8/3. Change either exponent and
#    q moves with it — that is the whole point (ADR §3). Self-consistency of E_M under the live S-law
#    is a NEXT-iter check (the bench now records m_sub); a large shift is a finding, not a blocker.
PIPE_AREA_EXP = 2.0       # area-preserving pipe: T_total ∝ r_base². EXACT (conserved section).
E_M           = 3.199     # [MEASURED] M_sub ∝ DBH^E_M, iter-31 bench × iter-34 read (3 tiers). See above.
Q_MASS        = PIPE_AREA_EXP / E_M   # = 0.625 — the OUTPUT. q<1 ⇒ loop gain <1 (ADR §2). NOT typed.
K_NDEF       = None       # ⛔⛔ RETIRED (iter-36). The sub-linear DIVISOR form (T_total=K·M^q, N_def=
                          # T_total/n_tips) is CODED and correct in MASS — but it EXPLODES anyway, for a
                          # reason ADR §2 missed: the S→shade→n_tips→(÷n_tips)→S fold. None => that whole
                          # form is inert. Superseded by C_NDEF (Position B) below; kept as the fold's name.
#
# ★★ iter-38 — POSITION B, CODED (ADR docs/adr_grower_size_law_numerator.md §6, ADOPTED). Drive S
#     DIRECTLY off standing mass, with NO live n_tips divisor — this CUTS the fold's return arm
#     (d log S/d log n_tips = 0), the channel iter-36's divisor form diverged through:
#
#         S = C_NDEF * M_sub^Q_MASS        N_def = S * N_DEF_REF   (PRIMARY)   T_total = N_def*n_tips (floats)
#
#     S still enters shade AND income (sampling-consistent, iter-15), but n_tips no longer feeds back
#     into S, so the only loop left is the ≤q<1 MASS loop iter-36 confirmed tame (gain q·d log M/d log S).
#     C_NDEF is pinned by the SAME closed-loop demand: grow the m tier with a given C, adjust C until it
#     ends its anchor year at S=1 (tmp/iter38_solve_C.py). GATE (ADR §6.4): conditioning d log M/d log C
#     ≈ 1/(1-q) ≈ 3 at the root; REFUTED if ≫10 (the mass loop is secretly near q=1). Losing a limb now
#     genuinely loses its twigs (no unphysical n_tips redistribution). See STATE.md board #1/#3.
C_NDEF       = None       # [PENDING PIN] Position B coefficient, S = C_NDEF·M_sub^Q_MASS. None => S≡1
                          # baseline (the iter-17 working model). Pinned by tmp/iter38_solve_C.py, then frozen.
#
# ⛔⛔ iter-36 — POSITION A IS STRUCTURALLY REFUTED, AND SUB-LINEARITY-IN-MASS IS NOT THE CURE.
#     tmp/iter36_run.log: NO stable S(m)=1 fixed point exists. S stays < 0.5 up to K≈31, then EXPLODES
#     discontinuously — K 31.09 → S 0.499 (n_tips 362), K 31.14 → S 94 (n_tips 1). A 0.16% step in K
#     flips S by 190×. The bench at the false "root" landed m at S=15.9 (not 1), l at a 2.8 m trunk
#     (S=87), foliage spread 400%, seeds BIFURCATING (some explode, some don't).
#
# ★ THE ALGEBRA ADR §2 GOT WRONG — "THE n_tips CANCELS" IS FALSE IN THE DYNAMICS.
#   The explosions coincide with n_tips COLLAPSING to 1, NOT with mass runaway (M_sub is SMALL at the
#   blown-up points, ~850 kg). The real loop is not through mass at all:
#
#       S ↑  →  S_IN_SHADE casts MORE shade per marker  →  interior foliage dies  →  n_tips ↓
#             →  S = K·M^q / n_tips  ↑  →  MORE shade  →  ...            (positive feedback, gain > 1)
#
#   ADR §2 cancelled n_tips in the INCOME identity (I ∝ T_total·ℓ̄) — valid — and concluded the
#   whole-crown gain is ≤ q < 1. But n_tips is a FUNCTION OF S (through the shade S casts), so it does
#   NOT cancel in the DYNAMICS: there is a SECOND loop, S→shade→n_tips→S, whose gain the q<1 mass
#   analysis never bounded. The sub-linear numerator tamed the loop the ADR studied and left untouched
#   the loop that actually diverges. iter-20's linear trace shows the SAME n_tips collapse (100→65→12→7)
#   — this instability predates the sub-linear form and is orthogonal to it. (iter-15 already flagged it:
#   "S_IN_SHADE off tames the violence but NOT the loop.")
#
# ⇒ iter-37: the size-law must be made robust to the n_tips/shade channel BEFORE any numerator can
#   stand. Candidates for the re-derivation (board #1): decouple S from the shade it casts (shade at a
#   FIXED reference density, not S-scaled); or cap dS/dt per year; or drive R_TIP directly off M_sub
#   (bypassing the n_tips divisor entirely). COMPUTE THE GAIN OF THE S→shade→n_tips LOOP first — on
#   paper — exactly as the mass loop was gated. Do NOT re-pin K.
# The two sides S acts on, separable ON PURPOSE — the iter-15 refutation is a statement about WHICH
# side breaks, and you cannot make that statement without being able to switch them independently.
S_IN_LIGHT   = True       # a marker INTERCEPTS the light of the N_def twigs it stands for
S_IN_SHADE   = True       # ...and CASTS their shade. ⚠ This is the destabilising one — see LEDGER 15.

# --- ★ iter-8, POSITION A: SELF-SUPPORT COST (ADR docs/adr_grower_crown_bound.md; falsification
# docs/grower_selfsupport_falsification.md). The crown-width bound is not in Palubicki (whose
# Discussion says outright they "ignored passive bending of branches under their weight") and not in
# C&E (which has no lengths). It is BIOMECHANICAL: a vertical axis is a column in compression and
# pays ~nothing to stand up; a horizontal limb is a CANTILEVER and must lay down d^3 ∝ M·L/sigma of
# wood just to hold itself out. Until iter-7 the grower got that wood FREE (radius was computed in
# finalize() AFTER the fact; the economy only bought internode LENGTH), so reach cost nothing and
# nothing bounded it. Now the economy buys WOOD VOLUME, and the support bill is paid out of the same
# finite pool as extension -> reach is priced, height is not, and the asymmetry falls out of
# statics rather than out of a fitted constant. Measured (size-controlled, R2 0.96): support wood
# ~ lever^+1.09 vs light income ~ lever^+0.27 => cost/income ~ lever^+0.82.
# These are PUBLISHED constants, not fits.
RHO_GREEN  = 900.0        # kg/m3, green Platanus wood (basic SG ~0.47 at ~90% MC). Wood Handbook.
MOR_GREEN  = 45.0e6       # Pa, modulus of rupture, green American sycamore (~6500 psi).
SAFETY     = 4.0          # trees hold a constant safe stress ~MOR/4 (Mattheck; Niklas).
SIGMA      = MOR_GREEN / SAFETY     # 11.25 MPa allowable bending stress
GRAV       = 9.81
LEAF_KG    = 0.010        # kg per foliage marker. Wood dominates the moment; see falsification §5.

# --- module / growth-unit lengths, in NODES (metamers). C&E measured for A2..A5. ---
GU_NODES = {1: 14,        # A1 trunk. [GAP-A1GU] — C&E's cell is BLANK; do NOT interpolate
            2: 15,        # A2  measured C&E
            3: 10,        # A3  measured C&E
            4: 7,         # A4  measured C&E
            5: 5}         # A5  measured C&E (short shoot)
INTERNODE = 0.11          # metamer length, m. [PROV] — no plane number; set so the m-tier
                          # trunk reaches ~14 m over the establishment window.
GROUND_FLOOR = 0.15       # m; a drooping limb rests just above soil, never grows underground. [PROV]

# ★ F6 SCOPE: grow the WOODY ARMATURE only (A1 trunk, A2 primaries, A3 secondaries). The
# A4/A5 short-shoot + twig layer is the space-filling FOLIAGE layer (design §7.1, §9.2) and
# is deferred — this prototype is LEAFLESS, so its terminal A3 tips ARE the foliage proxy.
MAX_CAT = 3               # deepest apparent order grown as skeleton (A3). A4/A5 = foliage layer.
# BRANCH_GRADE: how many axillary buds of a module's spiral zone RELEASE as growing branches
# this year (the rest stay dormant — proleptic; available to LATENT_BUD later). [PROV/GAP-grade]
BRANCH_GRADE = {1: 2, 2: 1, 3: 0}
# ★ iter-3: the BASE EFFECT (§4). "The first n_base modules of any axis bear few, weak laterals;
# vigour rises acropetally out of the establishment zone." The trunk's first few modules stay
# BARE, so the permanent crown starts above the establishment zone -> the CLEAR BOLE emerges as an
# output (cb ~ where the bare zone ends), instead of the trunk sprouting a permanent limb in year
# 1 at h~1.4 that never sheds and pins cb at 0.10. Applies to every axis (each limb gets its own
# bare proximal zone — the design's "bare proximal limb"), but it matters most on the trunk.
BASE_MODULES = 3          # first N modules of an axis bear no released laterals (base effect). [PROV]

SPIRAL_FRAC = 0.60        # distal fraction of a module that bears laterals (acrotony). [PROV]
DIVERG_SPIRAL = 137.5     # 2/5 spiral phyllotaxis divergence for orthotropic A1 (~144); use
                          # golden as the continuous stand-in [PROV-ish; C&E says spiral 2/5]

# --- ★ iter-6: the BORCHERT-HONDA RESOURCE ECONOMY (Palubicki 2009 §4.2, the "priority model").
# THE FIX for the iter-5 slab. Until now grow_module() did `n = GU_NODES[cat]`: every axis extended a
# fixed module every year regardless of light, so limb length -- and hence CROWN RADIUS -- was a
# de-facto PARAMETER (the 5th OUTPUT-not-parameter; see docs/adr_grower_resource_economy.md).
# We had implemented Palubicki's shadow grid and skipped the half that makes it mean anything.
#
# The economy: light Q accumulates BASIPETALLY to the base; the tree's total resource is
# v_base = ALPHA * Q_base -- FINITE AND SHARED. It flows back ACROPETALLY, split at each axis among
# its own apex and the child axes it supports, by the priority model:
#       v_i = v * (Q_i * w_i) / SUM_j(Q_j * w_j)
# ranked by mean light per bud (Q_i / nbuds_i), with the terminal bud placed FIRST while apical
# control lasts. As the bud count grows, per-apex v FALLS. Extension stops when the light the tree
# actually captured can no longer pay for it -> lateral reach is EARNED, with no cap anywhere.
#
# ★ ADR position B: we do NOT adopt the paper's n = floor(v) for the METAMER COUNT -- that would
# discard C&E's MEASURED, species-specific growth units (the reason this is a plane and not a generic
# self-organizing tree), AND it destroys ramification: every metamer is a lateral bud site, so scaling
# n away grows a bare pole with a few whips (measured -- see iter-6 in the prototype doc). C&E's
# GU_NODES stays the metamer count. Resource is spent on the INTERNODE LENGTH instead, which is what
# the paper's l = v/n really controls: a starved bud lays down its FULL set of buds on a short shoot.
# Density (n) and reach (l) are thus decoupled -- which is the whole trick.
#
# ⚠ THE RESOURCE ALONE DOES NOT BOUND THE CROWN. Because the allocation telescopes to
# light-proportional, a bud's share is ~the light its own leaves caught, so a bud at the sunlit
# PERIPHERY keeps f~1 forever: light-based extension REWARDS lateral runaway. The bound comes from
# C&E's ONTOGENETIC PAUPERIZATION (see grow_module) -- D_clean's geometric decay makes an axis's total
# extension a convergent series. Radius is bounded as an OUTPUT of the A1..A5 differentiation sequence.
# ★ iter-8: v IS NOW A WOOD VOLUME (m^3/yr), not an abstract resource. That single change is what
# lets self-support be PRICED: thickening (holding the limb out) and extension (reaching further)
# are both m^3, so they compete for one pool at no invented exchange rate. It also RETIRES V_SAT --
# an apex no longer saturates at a fitted resource level, it saturates when it can afford C&E's full
# internode, and the price of an internode is just the wood in it (pi*R_TIP^2*l). So the economy
# still has exactly ONE fitted scalar, and it is now the photosynthetic yield.
ALPHA      = 1.026e-5 # [DERIVED] iter-30: 0.45 * 2.281e-5. ★★ THE LEAK WAS THE CALIBRATION. Every
                     # value below was fitted against a `_distribute` that DISCARDED 95% of its pool
                     # at the apex clamp (iter-28 measured it; iter-29 conserved it). Once the spill
                     # made the budget real, income was 2.2x too rich: DBH ran 1.41x (m) / 1.89x (l)
                     # census. Re-derived by SWEEP (tmp/iter30_alpha_sweep.log, prereg
                     # tmp/iter30_prereg.md), solved under BOTH ground truths at once — census DBH
                     # *and* the m->l lever — because satisfying either alone proves nothing.
                     # ⚠ AND THE iter-11 RAIL DOES NOT APPLY HERE, which is the finding. "No uniform
                     # scalar can fix a size-dependent error" is true of R0/R_TIP/DBH_CALIB — static
                     # multipliers on DBH. ALPHA is not one: it multiplies INCOME, and income
                     # COMPOUNDS developmentally (poorer tree -> fewer apices -> less light -> fewer
                     # apices still). So it bites l harder than m and it BENDS THE LEVER:
                     #     k:          1.00    0.65    0.45    0.30
                     #     DBH m:     1.41x   1.17x   1.12x   0.91x
                     #     DBH l:     1.89x   1.38x   1.15x   1.00x
                     #     DBH lever:  2.21    1.95   [1.69]   1.81      <- census 1.65
                     # k = 0.45 lands BOTH tiers inside the instrument (DBH seed spread 9-19%), with
                     # height 1.02x/1.04x and crown r_p50 0.91x/1.05x census. Not fitted finer: the
                     # +12/+15% residual IS the instrument, and one seed cannot resolve it.
                     # ⛔ Do NOT cut further. At k = 0.30 the tree STARVES: H 0.79x/0.83x, crown
                     #    0.67x/0.81x -- DBH looks perfect (0.91x/1.00x) on a tree that is a stick.
                     #    DBH alone will happily certify a starved tree; that is why we solve on two.
                     # Was, before iter-30: 2.281e-5 -- iter-17: 2.59e-4 * k^2, k = 1/3.37. The
                     # PARTNER of the DBH_CALIB re-centring above — thinning the tip by k without
                     # dividing ALPHA by k^2 would have made every internode 11x cheaper and grown a
                     # monstrous tree. One scalar, two constants; see the iter-17 block at DBH_CALIB.
                     # That pairing STILL HOLDS — iter-30 rescales the pair's shared free scalar, it
                     # does not unpick it. Was, before iter-17:
                     # [FIT] m^3 of wood per unit of light gathered per year. v_base = ALPHA*Q_base.
                     # Replaces V_SAT (which it also subsumes: the two were degenerate).
                     # ★ iter-9: 3.0e-5 -> 2.59e-4 = 3.0e-5 * k^2, k = 2.94. NOT an independent fit --
                     # it is the partner of the DBH_CALIB refit above. R_TIP prices extension as
                     # 1/R_TIP^2, so thickening the tip by k without paying ALPHA*k^2 would have
                     # shrunk the tree ~9x. The pair is one calibration with one free scalar (k),
                     # pinned by the census DBH. See docs/grower_prototype_iter1.md iter-9.
EXT_MIN    = 0.02  # [PROV] below this extension fraction the bud cannot extend at all -> dormant.
W_MAX      = 1.0    # priority weights, Palubicki Fig. 8c / Fig. 9 (their published values).
W_MIN      = 0.02   # [FIT] the HABIT knob: large weights on a few branches => excurrent (their
                    # published 0.006 makes conifers); flatter => decurrent. A plane is decurrent.
KAPPA      = 0.5    # rank fraction over which w falls W_MAX -> W_MIN. Bigger kappa = more excurrent.
APICAL_OFF_YEAR = 12  # [PROV] apical control (terminal bud first in the priority list, irrespective
                      # of its light) is REMOVED after this year. Palubicki: this is what drives the
                      # "progression from the excurrent form of the young tree to the decurrent form
                      # of the old tree" (citing Barthelemy & Caraglio -- C&E's own school). ONE
                      # threshold gives the whole tier progression: s (10 yr) never loses it and stays
                      # excurrent (correct for a sapling); m and l lose it and spread.
APICAL_K   = 1.0    # ★ iter-7: the STRENGTH of apical control on the split. The share is
                    # Q * rank_weight * D_clean**APICAL_K, so this is the exponent on relay
                    # dominance -- the one knob that says how hard a leader outbids a subordinate
                    # lateral for the same finite pool. K=0 is iter-6 (light alone: the crown cannot
                    # be bounded, a peripheral bud keeps f~1 forever); K=1 was iter-7's first cut and
                    # measured too WEAK (m spread 20.2 m vs a 12-18 m reference, H 13.1 vs 14.4 --
                    # both errors have the SAME sign, which is what says the fault is strength and
                    # not placement). Raising it pauperizes the periphery WITHOUT starving it,
                    # because resource is conserved: what the lateral does not get, the leader does.
DORMANT_ABORT   = 3   # [PROV] consecutive years at n=0 (resource cannot buy even one metamer) before
                      # the apex aborts. Palubicki's 4th bud fate. Shed (Takenaka) still removes the
                      # whole branch separately once it becomes a net liability.

# --- angles ---
THETA_RELAY_DEG = 4.0     # kink of the relay ("prolongement", near-straight). [PROV/GAP-θrelay]
THETA_LATERAL_DEG = 60.0  # insertion angle of subjacent laterals ("ouvert"). [PROV]
# ★ iter-4: MODERATELY ASCENDING set-point (62° from vertical = ~28° above horizontal). iter-3's
# 60° CLIMBED forever because the posture pinned the tip to the set-point (right=RIGHT_K/r blew up
# at thin tips) so the arch never formed — a 26 m relay chain rose +13 m into the light. The fix is
# NOT a flat set-point (that gave dead-straight horizontal spokes) but a working ASCEND-THEN-ARCH:
# a young limb holds this ascending set-point; as it lengthens, self-weight sag wins and the tip
# DROOPS, so the limb arches over and comes DOWN under the master crown, where the downward shadow
# can overtop and shed it (the shed-driven bole, §7.3). See posture() for the load-vs-righting law.
THETA_GSA_DEG = 62.0      # plagiotropic gravitropic set-point from vertical, A2-A5. [PROV/GAP-θGSA]

# --- relay dominance D / firing (§2). ---
AU_MIN_AGE   = 6          # SEED trunk establishment: no crown-fork before the AU is attained.
                          # C&E: "AU attained in first 6 years." (structural, from source)
REITER_MIN_AGE = 1        # a REITERATE leader is born mature (low D); iter-4: a ceiling master must
                          # be able to round over after ONE module (age 2 let it overshoot H by ~3 m).
H_SOFT_FRAC  = 0.42       # crown-envelope soft cap (§6): a leader's D collapses as its apex
                          # nears H, so vertical extension stops near the target height. [PROV]
# ★ iter-4: the crown ROUNDS OVER near H (§6 envelope as a soft bound). Two coupled effects above
# CEIL_FRAC*H: (a) growth bends toward horizontal (grow_module) so no axis climbs far past H, and
# (b) an orthotropic leader that forks AT the ceiling yields PLAGIOTROPIC crown branches (the dome),
# NOT new climbing masters — whereas one that forks lower (room above) still makes orthotropic
# sub-masters. Without this the establishment-rise fix just moved the runaway from A2 chains to a
# stack of orthotropic master waves climbing to ~1.4×H. CEIL_FRAC [PROV].
CEIL_FRAC    = 0.82
D0_SEED      = 1.0        # seed trunk establishment PEAK (rises to this, then decays)
D_DECAY_AGE  = 0.13       # per-module dominance decay AFTER establishment (crown-building
                          # "diminution progressive de la dominance"). [PROV/GAP-γ]
PHI_FORK     = 0.34       # D threshold below which the axis forks. [PROV/GAP-Φfork]
# ★★ iter-4: the ESTABLISHMENT RISE (§2.1). C&E gives D a THREE-phase trajectory:
#   early sympodial (low) -> ESTABLISHMENT (RISING: "la dominance d'un relais unique est de plus
#   en plus marquée, l'acrotonie augmente") -> crown-building (falling -> forks).
# iter-1..3 modelled ONLY the falling limb (D monotone-decayed from birth), so every fork child
# was born already BELOW Phi_fork and re-forked at REITER_MIN_AGE -> pauperized to twigs -> NO
# persistent masters (the #1 iter-4 blocker). The rise is exactly what C&E says a fork element does:
# "chaque élément des fourches présente D'ABORD une forte acrotonie et une grande dominance ...
# il y a ENSUITE diminution." So a newborn master REBUILDS acrotony (rises to its wave peak), holds
# a single dominant orthotropic leader through establishment, THEN decays and forks. The peak is set
# per wave (D_RESET * parent_PEAK -> lower each wave -> 0 at the periphery: "d'une vague à l'autre le
# caractère dominant ... diminue pour devenir NUL"), so scaffold DEPTH is an OUTPUT that terminates
# on its own. (This reconciles §2.1's three-phase narrative with §2.2's decay-only formula, which
# had dropped the rising limb.)
EST_FLOOR    = 0.85       # ★ D at birth as a fraction of the wave PEAK. C&E: a fork element has
                          # "D'ABORD une forte acrotonie et une grande dominance ... ENSUITE
                          # diminution" — i.e. born STRONG, then decays. So EST_FLOOR is HIGH (the
                          # "rise from low" is the seedling's juvenile phase, gated by AU_MIN_AGE, not
                          # a fork element's). This is what makes the master persist: born well above
                          # Phi_fork, it holds a dominant leader while D decays, and only forks when
                          # decay (or hcap near H) brings D_eff under Phi. With headroom (l tier, hcap
                          # ~1) it establishes several modules; at the ceiling (m/s, hcap<1) it rounds
                          # over after one — so scaffold depth is tier-dependent and emergent. [PROV]
# The SEED trunk starts at (near) full dominance — its juvenile establishment is already handled by
# the AU_MIN_AGE fork gate — so it gets a SHORT rise window and is decay-dominated, forking near
# iter-3's ~11 m. The RISE matters for the fork CHILDREN, which are born low (child_peak) and must
# rebuild acrotony to persist as masters. A long seed window delayed the trunk fork up to 0.87*H,
# eating the headroom masters need. [PROV]
EST_WINDOW_SEED   = 1
EST_WINDOW_REITER = 5     # a reiterate leader re-establishes over this many modules. [PROV]
D_RESET      = 0.60       # a newborn wave's establishment PEAK = D_RESET * parent_peak. Lower each
                          # wave -> the scaffold self-terminates at the periphery. [PROV/GAP-D0]
D_MASTER_MIN = 0.30       # a fork child whose wave PEAK >= this is an orthotropic MASTER (cat-1,
                          # "branche maîtresse comparable au tronc"); below it the fork elements are
                          # terminal PLAGIOTROPIC secondaries (cat MAX_CAT). Replaces iter-3's birth-D
                          # D_STOP test — the decision is now on the establishment PEAK, so a master
                          # is judged by the leader it CAN build, not by its (low) birth dominance.
                          # trunk peak 1.0 -> master 0.60 -> sub-master 0.36 -> 0.22<min = terminal:
                          # ~2 orthotropic master orders then plagiotropic periphery (an OUTPUT). [PROV]
# --- ★ iter-3: env_release (§7.5, the ratified F1 amendment). Light modulates RELAY DOMINANCE:
# HIGH irradiance LOWERS D (co-equal relays -> forks early -> open-grown spreading form); LOW
# light HOLDS D high (single dominant relay -> tall woodland leader). It is a GENTLE current-
# conditions FACTOR on D (§2.2: D = D_0·decay·env_release), evaluated at the decision, NOT
# compounded annually. iter-1/2 had it INVERTED **and** compounding (`ax.D *= clip(lt/FULL,
# 0.15,1)` every year), which annihilated the self-shaded trunk apex's D to ~0 within two years
# -> the age-6 establishment fork was maximally pauperized (Dchild~0 -> cat-3 twigs, NO masters).
# With the sign corrected, a self-shaded establishment leader HOLDS its dominance and reaches the
# fork gate with D still near Phi_fork -> Dchild > D_STOP -> 2-3 orthotropic MASTERS (C&E's
# "fourche de 2 ou 3 branches maîtresses orthotropes ... complexes réitérés totaux").
ENV_LIGHT_K = 0.30       # strength of the light->D reduction. [PROV/GAP-env]
ENV_MIN     = 0.70       # env_release floor: a fully-lit apex keeps >=70% of its dominance. [PROV]
MAX_ORDER_GUARD = 7       # loop guard only; NOT a botanical cap (max_order is an output)
# ★ iter-5: LIGHT-EQUITY among near-apex buds (§2.1 acrotony / §7.5 F1-amendment). Makes masters hold
# a LONG single leader (they were forking after 1-3 modules) and makes fork multiplicity M emergent.
DOM_RING_R    = 1.2      # m; radius of the crown-plane light ring sampled around the apex. [PROV]
DOM_HOLD      = 1.10     # apex_dominance above this => the apex is an emergent leader that HOLDS
                        # (its acrotony is strong; it does NOT fork this year even if D dipped). [PROV]
DOM_D_BONUS   = 0.30     # a dominant apex's D_eff is boosted up to this fraction (bounded "acrotonie
                        # augmente") so a strong single leader establishes LONGER before decaying to
                        # the fork gate — the master "comparable au tronc". [PROV]
DOM_EQUITY_TOL = 0.06    # a near-apex bud within this light fraction of the brightest counts as a
                        # co-equal relay -> sets emergent M (2 vs 3). [PROV]

# --- posture (§7.2): ascend-then-arch. Young limb holds the ascending set-point (right » sag);
# old long heavy limb loses to its own load and the tip droops (sag » right) -> the arch. ---
SAG_K        = 0.50       # ★ iter-5: sag gain per (subtree mass * lever). Raised from 0.055 so a long
                          # heavy old limb's sag genuinely DOMINATES its bounded righting -> the tip
                          # weeps below an interior SUMMIT (a real §7.2 arch), not the iter-4
                          # ascend-then-LEVEL (which never made an interior summit, so the arch cascade
                          # could not fire and limbs ran to a 26 m reach). Young/short limbs still hold
                          # the ascending set-point (small mass*lever). [PROV/GAP-strain]
RIGHT_K      = 0.16       # ~bounded reaction-wood righting gain (iter-4: constant, not ∝1/r —
                          # the 1/r form pinned thin tips and prevented the arch). [PROV/GAP-strain]
DROOP_K      = 0.55       # how much of the un-righted (sag-losing) fraction becomes downward arch
                          # of the tip's growth direction each year. [PROV] Sets arch strength.

# --- light / shadow grid (§7.3, F1). Palubicki coarse shadow propagation. ---
VOX          = 0.6        # voxel size, m. [PROV]
SHADOW_A     = 1.0        # shadow deposited by one foliage site at its own voxel. [PROV]
SHADOW_B     = 1.4        # decay base per voxel-level below a source. [PROV]  Δs = a*b^(-Δlvl)
                          # (lower => shade reaches further down => interior actually shades out)
SHADOW_LEVELS = 9         # depth of the downward shadow cone, voxels. [PROV]
FULL_LIGHT   = 6.0        # unshaded light budget C. [PROV]
TAU_SHED     = 0.18       # shed when light_gathered/size < TAU. [PROV/GAP-τ] — the ONE free
                          # scalar we allow ourselves to fit to the measured cb_frac~0.30.

# ★★★ iter-25 — THE LIGHT LAW IS BEER–LAMBERT, NOT A CLAMPED SUBTRACTION.
#
# Until iter-25 light_at() returned `max(C - s + own, 0)` — Palubicki's published shadow
# propagation, implemented faithfully. It CLAMPS. C is an absolute constant (6.0) while `s` is an
# unbounded SUM over every foliage marker above the point. Measured on the shipped tree (iter-25c):
# the clamp sits at 7 and THE FIELD RUNS TO 30. Past 7 the law returns 0.000 at EVERY depth, so 15,
# 30 and 60 units of shade are indistinguishable — ~77% of the field's dynamic range is discarded.
#   * 73% (m) / 69% (l) of LIVE WOODY INTERNODES read EXACTLY zero light.
#   * 49% (m) / 56% (l) of LIVE FOLIAGE MARKERS read EXACTLY zero.
# The shed gate is a RATIO test on that clamped numerator, so it never measured light at all — it
# read a saturation flag. Hence: every dying limb at L = 0.00 exactly, a bimodal light field, and
# iter-24's unfittable A5 gate ("every theta in [0, 0.25] selects the same set"). AN UNFITTABLE
# CONSTANT IS THE SIGNATURE OF A SATURATED INSTRUMENT.
#
# ★ AND IT IS WHY THE TREE CANNOT SCALE. The clamp gives the crown a LIT SHELL OF FIXED OPTICAL
# DEPTH: light exists only within ~7 markers'-worth of the crown surface, and everything deeper
# earns nothing however much foliage stands there. So INCOME scales with crown SURFACE while the
# shed gate's COST — every woody internode maintained — scales with crown VOLUME. A surface-fed,
# volume-billed tree has a hard size ceiling and must amputate its own interior to stay solvent.
# That is the defect chased since iter-15: builds 2.43x, keeps 1.77x, kills 3.30x (census: 3.23x).
#
#     light_at:   max(C - s + own, 0)      ->      C * exp(-(s - own) / C)
#
# ⛔ NOT A SCALAR RE-FIT. Raising C from 6 to 60 merely MOVES the clamp, and is exactly the move
# the rails forbid (a scalar may CENTRE and UN-SUPPRESS; it may never FIX). This changes the
# FUNCTIONAL FORM: the dead zone where the regulator has ZERO authority ceases to exist at any
# depth, because dI/ds = -I/C is never zero.
#
# ★ AND IT INVENTS NO CONSTANT. k = 1/C is the UNIQUE extinction coefficient whose exponential is
# TANGENT to the old law at s = own: same value (C) and same slope (-1) there. So the LIT regime —
# where TAU_SHED, ALPHA, DBH_CALIB and the whole economy were calibrated — is preserved to first
# order, and ONLY the saturated region changes, where a dead 0.000 becomes a real, small, strictly
# positive light (s=15 -> 0.49, s=30 -> 0.04). k = 1/C is not claimed to be physical: a true canopy
# extinction (k≈0.5 per unit LAI) is unavailable to us because our shadow unit is "SHADOW_A per
# marker", not LAI, and inventing the conversion WOULD be a new constant. Matching the slope at the
# origin invents nothing. Beer–Lambert is MORE standard than the clamp, not less.
LIGHT_K = 1.0 / FULL_LIGHT   # [DERIVED] the tangency condition. NOT free, NOT fittable.

# --- ★ iter-2: the CHEAP A4 FOLIAGE light-gatherer layer (closes the light loop). ---
# The shed rule is a foliage-light rule; a leafless armature has nothing renewing light at the
# lit periphery, so shedding grinds monotonically to bare (iter-1's l-tier collapse). So each
# year every living structural TIP puts out a few transient A4 short-shoot "leaves". These are
# NOT skinned and NOT wood (excluded from the ratchet) — they exist only to gather light and
# cast shade. They shed fast (C&E: A4/A5 self-prune 1-4 yr), so a limb that stops reaching fresh
# light loses its foliage and then sheds; a limb at the lit periphery keeps re-leafing and lives.
# That birth-at-periphery / death-of-shaded-interior balance IS the crown equilibrium.
FOLIAGE_LIFE     = 3      # a leaf cohort persists this many years then abscisses. [PROV, C&E 1-4]
FOLIAGE_PER_TIP  = 4      # A4 short shoots a lit tip puts out per year. [PROV]
FOLIAGE_SPREAD   = 0.35   # how far (m) leaves sit off the bearing tip. [PROV]

# ★★ iter-24: THE A5 SHORT-SHOOT LAYER — the deferral of §7.1, paid at last. LIVE (not a
# retired term; see the kill-switch rail in STATE).
#
#   THE DEFECT IT ANSWERS (iter-23): foliage lived ONLY at armature apices, so a limb's income
#   could not grow with the limb. The shed gate counts income at TIP resolution and cost at
#   INTERNODE resolution (light(subtree) / woody_internodes(subtree) < TAU_SHED), so an l-tier
#   axis carried 8.5x more wood per live tip than an m-tier one, sat 3.4x closer to the cliff,
#   and its tips' LIFETIME halved. A real plane bears short shoots along its whole LIT length,
#   so its income scales with lit branch length. Ours did not.
#
#   THE RULE, AND IT INVENTS NO CONSTANT: a live woody internode of LAST year's wood or older,
#   standing in light >= TAU_SHED, bears short-shoot foliage at the SAME LINEAR DENSITY the
#   model already asserts for a lit shoot — a tip puts out FOLIAGE_PER_TIP markers for the
#   GU_NODES[cat] internodes of shoot it makes in a year, so
#
#       P(short shoot on a lit internode, per year) = FOLIAGE_PER_TIP / GU_NODES[cat]   (~0.27-0.40)
#
#   and the cohort self-prunes on the existing FOLIAGE_LIFE = 3 (C&E measure A4/A5 short shoots
#   self-pruning in 1-4 yr — that constant was ALWAYS this layer's, it just had nothing to prune).
#   ⚠ Only wood born BEFORE this year bears them: this year's shoot IS the tip cohort, and
#   foliating it twice would double-count. Botanically exact — a proleptic A5 short shoot breaks
#   from a lateral bud on the PREVIOUS year's wood.
#   ⛔ NOT "a full FOLIAGE_PER_TIP cohort per internode". INTERNODE is 0.11 m against VOX = 0.6 m,
#   so that is 22 markers per voxel of limb per year: a 30x inflation of an income that ALPHA and
#   TAU_SHED were calibrated against. The density is the thing that must be conserved, not the count.
#
#   ★ THE LOOP GAIN, COMPUTED BEFORE THE TERM WAS CODED (tmp/iter24_gate.py, on the shipped tree):
#   income now scales with LIT foliated length. The light field over live woody internodes is
#   BIMODAL — 40% of them stand at exactly zero light — so the gate bites on its own and EVERY
#   theta in [0.0, 0.25] selects the same set. It is not a fitted constant.
#       lit internodes   m 481 -> l 1101   = x2.29   (the lit SURFACE, x2.23 — not total wood)
#       => q = ln(2.29)/ln(3.28 mass) = 0.70   =>   amplification 1/(1-q) = 3.3x   — STABLE.
#   The 12x bifurcation regime (q = 0.92) was the one where income tracks TOTAL wood; the light
#   gate is exactly what keeps us off it, and interior self-shading is the negative feedback.
SHORT_SHOOT_LIGHT = TAU_SHED   # the SAME economic bar, one level down: a unit of wood keeps its
                               # foliage if it stands in TAU_SHED of light per unit. [DERIVED]

# --- ★ iter-3: LATENT_BUD (Mode 2), the re-erection of dormant buds on OLD WOOD (§2.3, §3.3,
# §7.2). iter-1/2's Mode 2 was INERT (reit stuck at 3-4) because its host set was only ALIVE
# cat-1 axes — i.e. the trunk, which forks and dies by age ~7, leaving no host. But the WOOD
# PERSISTS after an axis stops extending: the forked trunk, the dead masters and the plagiotropic
# limbs are all old wood bearing dormant buds. So the host set is OLD WOODY NODES on ANY axis.
# Release is POSITIONAL, not a light threshold (§2.3: "C&E ties it to POSITION and to the arch
# summit," not to a scheduled light gate) — light acts on the reiterate AFTER birth, through the
# shed rule (an overtopped re-erection is shed; one that reaches light lives). Release is biased
# LOW because C&E: "plus ils sont proches de la base des branches maîtresses ... plus ils sont
# développés" — the basal reiterates are the veteran's heavy low limbs. start_order = s(u_ins)
# (§3.3): basal insertion -> s=1 total reiterate (orthotropic, thick, big subtree); peripheral
# -> s->5 M.A.U. (a spent short shoot). This is the crown's REBUILD mechanism and the source of
# the caliber sign flip (thick reiterates low) and the veteran's arch-cascade low limbs.
LATENT_MIN_AGE  = 5      # a node is "old wood" bearing a releasable dormant bud after this many yr. [PROV]
LATENT_MIN_U    = 0.26   # ★ dormant buds on the CLEAR BOLE (u_ins < this) stay suppressed (apical
                         # dominance; the establishment zone). C&E puts the heavy reiterates "à la
                         # base des BRANCHES MAÎTRESSES", i.e. in the LOW CROWN, not on the bole.
                         # Firing above the bole lets the thick reiterates OVERTOP and shed the thin
                         # low A2s -> the bole clears AND the low crown rebuilds thick. [PROV]
LATENT_RATE     = 0.85   # release prob for a candidate at LATENT_MIN_U (scaled by the low bias). [PROV]
LATENT_LOW_BIAS = 2.5    # release weight (1-u_ins)^BIAS -> favour low-crown buds (the heavy limbs). [PROV]
LATENT_MIN_SEP  = 1.5    # m; two buds may not release within this distance the same year. [PROV]
MAX_LATENT_PER_YEAR = 4  # bounded release (ages the tree gradually, not a flush). [PROV]
LATENT_START_AGE = 8     # the tree only re-erects latent buds once it is past establishment. [PROV]

# --- ★ iter-5: the ARCH CASCADE (§7.2). C&E's veteran low limbs are "une succession de complexes
# réitérés partiels s'étant affaissés. Le complexe réitéré suivant s'est développé AU SOMMET DE
# L'ARCURE ... d: dépérissement de la partie distale de l'axe affaissé." The full loop:
#   a limb arches under its own load (posture, already wired) ->
#   a LATENT_BUD reiterate re-erects AT THE ARCH SUMMIT (epitony, upper side) ->
#   it grows up and takes the light ->
#   the distal continuation BEYOND the summit is overtopped and DIES BACK (the shed rule) ->
#   the new complex becomes the arch. repeat.
# iter-4 fired latent buds POSITIONALLY (biased low) but never AT SUMMITS, so this loop — the
# veteran's ground-sweeping-limb mechanism — was only half-exercised (the arch profile without the
# cascade). This wires the summit firing + the registered distal dieback. NOTHING here is authored:
# the summit is where posture drooped the axis, the re-erection is Mode 2, the dieback is §7.3's tau.
ARCH_MIN_AGE      = 6    # a limb must be this many modules old to have arched over. [PROV]
ARCH_DROP         = 0.9  # m; summit-minus-apex height drop that marks a real arch (not a straight limb). [PROV]
ARCH_REFRACTORY   = 3    # years before the SAME axis may sprout another summit reiterate. [PROV]
ARCH_MAX_PER_YEAR = 3    # bounded (the cascade ages the tree gradually, not a flush). [PROV]
ARCH_MIN_SUMMIT_Y = 1.5  # m; ignore summits at ground-twig height. [PROV]
ARCH_MIN_INTERIOR = 3    # summit must be at least this many nodes from the apex (a real distal continuation). [PROV]

SEED = 20260710


# ===========================================================================
# GRAPH PRIMITIVES
# ===========================================================================
class Node:
    __slots__ = ("pos", "parent", "axis", "birth", "alive", "foliage", "death_c")
    def __init__(self, pos, parent, axis, birth, foliage=False):
        self.pos = np.asarray(pos, float)
        self.parent = parent          # node index, or -1
        self.axis = axis              # owning Axis id
        self.birth = birth            # year laid down (leaf cohort year, if foliage)
        self.alive = True
        self.foliage = foliage        # True = transient A4 leaf marker (light-gatherer, not wood)
        self.death_c = 0.0            # ★ iter-15: c_H on the year this unit died — the disused pipe
                                      # area it walls off as heartwood. Stamped by _kill_subtree, and
                                      # never rewritten: a leaf unit dies once, at ONE size.


class Axis:
    """One 'strand' == one apparent-order chain (a serie lineaire). §1.2."""
    __slots__ = ("id", "cat", "order", "reit", "D", "D_peak", "est_window", "alive", "apex",
                 "nodes", "birth", "dirv", "gsa", "age", "forked", "D_at_fork", "_relay_host", "_D_eff",
                 "_last_spiral", "_dom", "_arched_at", "_v", "_dormant")
    def __init__(self, aid, cat, order, reit, D, apex, dirv, birth,
                 D_peak=None, est_window=EST_WINDOW_REITER):
        self.id = aid
        self.cat = cat                # apparent order rung 1..5 (A1..A5)
        self.order = order            # topological/apparent branching order for shading only
        self.reit = reit              # owning Reiterate id
        self.D = D                    # relay dominance (current; = D_clean each year, for diagnostics)
        self.D_peak = D if D_peak is None else D_peak   # ★ iter-4: the establishment PEAK this axis
                                      # rises to before decaying (§2.1). Set per wave (D_RESET*parent).
        self.est_window = est_window  # ★ iter-4: establishment length in modules (rise then decay)
        self.alive = True
        self.apex = apex              # node index of the active apex (or None once ended)
        self.nodes = [apex]           # node indices in growth order
        self.birth = birth
        self.dirv = np.asarray(dirv, float)
        self.gsa = None               # set-point direction target (plagiotropic axes)
        self.age = 0                  # modules grown
        self.forked = False
        self._last_spiral = []        # ★ iter-5: node ids of the last module's near-apex spiral buds
        self._dom = 1.0               # ★ iter-5: apex light-dominance vs its crown-plane neighbours
        self._arched_at = -99         # ★ iter-5: year an arch-summit reiterate last fired on this axis
        self._v = 0.0                 # ★ iter-6: BH resource allocated to this axis's apex this year
        self._dormant = 0             # ★ iter-6: consecutive years the apex could not buy a metamer


class Grower:
    def __init__(self, H, DBH_target_m, seed=SEED):
        self.H = H
        self.DBH_target_m = DBH_target_m
        self.rng = np.random.default_rng(seed)
        self.nodes = []
        self.axes = []
        self.reit_count = 0
        self._shadow, self._mn = {}, np.zeros(3)   # ★ iter-6: last year's light field (banked)
        # ★ iter-8: banked alongside the light field, and spent the same way — a year in arrears.
        # _r_prev = last year's structural girth per node (the baseline the thickening bill is
        # measured against); _bill = last year's support demand per axis, which this year's
        # allocation pays before it grows anything. Trees do thicken in arrears; so does this.
        self._r_prev = np.zeros(0)
        # ★ iter-12: the pipe radius each node carried LAST year. Two jobs, both load-bearing:
        # it makes the §5 ratchet actually monotone ACROSS years (the radius array is rebuilt from
        # zero every year, so the old max() only ever ratcheted within one bottom-up pass), and it
        # is where a DEAD child's pipe area is frozen so its parent can keep carrying it.
        self._r_hist = []
        # ★ iter-42: the BUILT structural radius of every node, snapshotted once per grown year, so the
        # ring-age partition (Track B) can read r_i(t - TAU_HEARTWOOD) -- the girth TAU years before the
        # end, i.e. the boundary between the outer sapwood rings and the aged heartwood core. Read-only
        # bookkeeping: it never feeds back into growth, so DBH/economy stay bit-identical. See finalize().
        self._radius_hist = []
        # ★ iter-13: the two components the ratchet now keeps SEPARATE, because they obey different
        # laws (see ratchet()). _r_sap = the ACTIVE pipe radius (Shinozaki, p = PIPE_POWER, live
        # children only); _a_dead = the DISUSED pipe AREA walled off as heartwood (p = 2, conserved).
        # Both are frozen at death: they are only ever rewritten for a node that is still alive.
        self._r_sap  = []
        self._a_dead = []
        # ★ iter-14: the leaf-unit census the two banks are now counted in (Eqs 5 & 6).
        self._f_live, self._f_lost = [], []
        # ★ iter-15: the DISUSED pipe AREA (not the count) lost below each node. A unit that died when
        # the tree was small walled off a SMALLER pipe than one that died last year, so heartwood can
        # no longer be a count times a global c_H — each lost unit is banked at the c_H prevailing on
        # the year it died (Node.death_c). Same law (Aye Eq. 6, c_H per lost unit), size-aware.
        self._a_lost = []
        # ★ iter-15: N_def(t) — see the constants block. S is the ratio to the anchor (S == 1 at m),
        # and it is what the light income, the shade, the tip pipe and the heartwood all ride on.
        # Both inputs are OUTPUTS of the economy, read off last year's crown.
        self.s_def   = 1.0            # S(t) = N_def(t)/N_DEF_REF
        self.n_def   = N_DEF_REF      # real twigs one armature tip stands for, this year
        self.r_tip   = R_TIP          # live tip-seed radius   = R0*DBH_CALIB*S^(1/p)
        self.c_heart = C_HEART        # live heartwood per lost unit = HEART_RATIO*pi*r_tip^2
        self._crown_vol = 0.0         # occupied-voxel volume of the live foliage cloud, m^3
        self._n_tips    = 0           # live leaf units (what grow_foliage foliates)
        self._n_short_shoots = 0      # ★ iter-24: A5 short shoots borne on older lit wood this year
        self._m_sub     = 0.0         # ★ iter-19: subtended mass at the root, kg — N_def's numerator
        self._bill = {}
        self._alloc_year = self._spend_year = self._spill_residue = 0.0   # ★ iter-29 diagnostics
        self._arch_distal = []   # ★ iter-5: (distal_root_node, host_axis) — arch-summit dieback
                                 # candidates; the shed rule kills each once its offspring overtop it.
        # seed: ground node + trunk apex one internode up
        self.nodes.append(Node([0, 0, 0], -1, -1, 0))     # ground/root, node 0
        up = np.array([0.0, 1.0, 0.0])
        self.nodes.append(Node([0, INTERNODE, 0], 0, 0, 0))  # first trunk metamer, node 1
        trunk = Axis(0, cat=1, order=0, reit=0, D=D0_SEED * EST_FLOOR, apex=1, dirv=up, birth=0,
                     D_peak=D0_SEED, est_window=EST_WINDOW_SEED)
        self.nodes[1].axis = 0
        self.axes.append(trunk)
        self.reit_count = 1

    # -- small helpers ------------------------------------------------------
    def _new_node(self, pos, parent, axis, year):
        self.nodes.append(Node(pos, parent, axis, year))
        return len(self.nodes) - 1

    def _rot_toward(self, d, target, frac):
        """Rotate unit vector d a fraction frac toward unit target (slerp-lite)."""
        d = d / (np.linalg.norm(d) + 1e-12)
        t = target / (np.linalg.norm(target) + 1e-12)
        out = (1 - frac) * d + frac * t
        n = np.linalg.norm(out)
        return out / n if n > 1e-9 else d

    def _perp(self, d):
        """Some unit vector perpendicular to d."""
        a = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(a, d)) > 0.95:
            a = np.array([1.0, 0.0, 0.0])
        p = a - np.dot(a, d) * d
        return p / (np.linalg.norm(p) + 1e-12)

    def _azimuth_dir(self, axis_dir, deg_from_axis, azimuth_deg):
        """A unit direction deg_from_axis away from axis_dir, at the given azimuth around it."""
        d = axis_dir / (np.linalg.norm(axis_dir) + 1e-12)
        u = self._perp(d)
        v = np.cross(d, u)
        a = math.radians(deg_from_axis)
        az = math.radians(azimuth_deg)
        radial = math.cos(az) * u + math.sin(az) * v
        return math.cos(a) * d + math.sin(a) * radial

    # ======================================================================
    # ONE MODULE (one year) of one axis   (§8 + §4 + §2 relay)
    # ======================================================================
    def grow_module(self, ax, year):
        # ★ iter-6. The module has TWO independent quantities and they must be spent separately:
        #
        #   n (METAMER COUNT)  -> DENSITY. Every metamer is a lateral bud site, so n is what ramifies
        #       the crown. It stays C&E's MEASURED growth unit, unscaled. (Scaling n instead was the
        #       first thing I tried: it destroys ramification and grows a bare pole with a few whips.)
        #   l (INTERNODE LENGTH) -> REACH. This is what the tree spends resource and vigour on, and
        #       what bounds crown radius. Palubicki does exactly this (n = floor(v), l = v/n): a
        #       starved bud lays down its full set of buds on a 2 cm shoot instead of a 1 m one.
        #       That is the real short-shoot/long-shoot (brachyblast/auxiblast) distinction.
        #
        # l is scaled by TWO factors, and it takes both to bound the crown:
        #   the RESOURCE share the apex can AFFORD, in m^3 of wood, AFTER its axis paid its support bill.
        #       NOT sufficient on its own: because the allocation telescopes to light-proportional,
        #       a bud's share is ~the light its own leaves caught, and a bud at the sunlit crown
        #       PERIPHERY keeps f~1 forever. Light alone therefore REWARDS lateral runaway.
        #   vigour(age)             — C&E's ONTOGENETIC PAUPERIZATION (what the axis is CAPABLE of).
        #       An axis differentiates along the A1..A5 sequence: its successive modules get less
        #       vigorous and it finally stops. This is D_clean's own rise-then-decay, which we already
        #       compute and until now spent only on the fork decision. Because the decay is geometric,
        #       an axis's total extension is a CONVERGENT series -> limb length is BOUNDED, and bounded
        #       as an OUTPUT of C&E's differentiation, not by any cap on radius.
        #
        # vigour is normalised by the axis's own D_peak ON PURPOSE, and it carries only ONE of the two
        # pauperizations: WITHIN-AXIS senescence (an axis's successive modules get less vigorous until
        # it stops — a convergent series, so a single axis's own extension is bounded). The BETWEEN-AXIS
        # pauperization — a wave-1 lateral must not reach as far as the trunk — is NOT here: it lives in
        # the dominance-weighted resource split (see _distribute). Putting it here as well, by reading D
        # on the absolute scale, double-penalizes (capability x affordability) and amputates the crown.
        # ★ iter-8: the apex's share _v is now a WOOD VOLUME (m^3), and it is what is LEFT after the
        # axis paid this year's self-support bill (see _distribute). A metamer is a cylinder of tip
        # radius R_TIP and length l, so the module costs n*pi*R_TIP^2*l -- the length it can afford
        # is a division, and C&E's INTERNODE is the ceiling on it (the species' full long shoot; a
        # bud cannot lay down more internode than its genotype has, however rich it is). That
        # ceiling is what V_SAT used to be, so V_SAT is retired: the saturation is now structural.
        n = GU_NODES[ax.cat]
        vigour = np.clip(self.D_clean(ax) / max(ax.D_peak, 1e-6), 0.0, 1.0)
        l_afford = ax._v / (n * math.pi * self.r_tip ** 2)
        ext = min(1.0, l_afford / INTERNODE) * vigour
        if ext < EXT_MIN:
            ax._dormant += 1                    # cannot extend at all this year (a dormant bud)
            return None, []
        ax._dormant = 0
        step = INTERNODE * ext
        # ★ iter-29 diagnostic: what the apex was GIVEN vs what its extension actually BUYS. The gap
        # is the leak (95.0% of the pool, iter-28). The `vigour` share of it survives the spill --
        # named, and left standing, on purpose: it is a CAPABILITY limit, not an unspent budget.
        self._alloc_year += ax._v
        self._spend_year += n * math.pi * self.r_tip ** 2 * step
        # lay down n metamers along the current (posture-updated) direction
        d = ax.dirv.copy()
        # ★ iter-4: crown rounding (§6 envelope soft bound). Above CEIL_FRAC*H, bend growth toward
        # horizontal in proportion to how far past the ceiling the apex is, so leaders dome over near
        # H instead of climbing past it. Applies to every axis; matters most for orthotropic leaders.
        y_apex = self.nodes[ax.apex].pos[1]
        ceil = CEIL_FRAC * self.H
        if y_apex > ceil and d[1] > 0.0:
            over = np.clip((y_apex - ceil) / (self.H * (1.0 - CEIL_FRAC) + 1e-6), 0.0, 1.0)
            horiz = d.copy(); horiz[1] = 0.0
            hn = np.linalg.norm(horiz)
            if hn > 1e-6:
                d = self._rot_toward(d, horiz / hn, 0.7 * over)
                ax.dirv = d.copy()
        laterals_hosts = []       # (node_id, position_in_module) for the distal spiral zone
        spiral_start = int(math.floor(n * (1.0 - SPIRAL_FRAC)))
        base_az = self.rng.uniform(0, 360)
        for i in range(n):
            p_prev = self.nodes[ax.apex].pos
            newp = p_prev + step * d
            # ★ iter-4: a drooping limb cannot grow into the ground. C&E's veteran low limbs are
            # "retombantes JUSQU'AU sol" (to the ground), so a floor of ~0 is right; below it is a
            # posture artefact. Clamp to a small floor so ground-sweeping limbs rest just above soil.
            if newp[1] < GROUND_FLOOR:
                newp[1] = GROUND_FLOOR
            nid = self._new_node(newp, ax.apex, ax.id, year)
            ax.apex = nid
            ax.nodes.append(nid)
            if i >= spiral_start:
                laterals_hosts.append((nid, i))
        # ★ iter-5: the near-apex spiral buds of THIS (top) module are the co-equal relay
        # candidates for the light-equity fork test (§2.1/§7.5). Store them for the firing step.
        ax._last_spiral = [h for (h, _) in laterals_hosts]
        # --- acrotony: emit laterals at the distal spiral zone (§4) ---
        # most-distal host is reserved for the relay; a small branching-grade of the
        # sub-jacent buds RELEASE this year (most distal first = acrotony), the rest stay
        # dormant. A5/A4 twig layer is not grown here (F6 skeleton scope, MAX_CAT).
        relay_host = laterals_hosts[-1][0] if laterals_hosts else ax.apex
        child_axes = []
        child_cat = ax.cat + 1
        grade = BRANCH_GRADE.get(ax.cat, 0)
        # base effect (§4): an ORTHOTROPIC leader's first BASE_MODULES modules bear no released
        # laterals — the bare establishment zone from which the clear bole emerges (cb an OUTPUT).
        # Restricted to cat-1 leaders (trunk, masters, total reiterates): applying it to every twig
        # over-thinned the crown fill. Plagiotropic A2/A3 ramify from their base (crown volume).
        if ax.cat == 1 and ax.age < BASE_MODULES:
            grade = 0
        if grade > 0 and child_cat <= MAX_CAT:
            # sub-jacent hosts, most-distal first (acrotony), excluding the relay host
            subjacent = list(reversed(laterals_hosts[:-1]))[:grade]
            for k, (hid, i) in enumerate(subjacent):
                az = (base_az + k * DIVERG_SPIRAL) % 360.0
                child = self._spawn_lateral(hid, ax, child_cat, az, year)
                child_axes.append(child)
        # --- year boundary: apex aborts, distal-most lateral relays with a small kink ---
        kink = math.radians(self.rng.normal(0.0, THETA_RELAY_DEG))
        az = self.rng.uniform(0, 360)
        relay_dir = self._azimuth_dir(d, math.degrees(kink), az)
        ax.dirv = relay_dir
        ax.age += 1
        # ★ iter-4: D is no longer a monotone per-year decay. Its clean age trajectory (rise during
        # establishment, then decay) is computed on demand by D_clean(); light/height modulation is
        # applied to it in step() as D_eff. ax.D is refreshed there for diagnostics.
        return relay_host, child_axes

    def _spawn_lateral(self, host_id, parent_ax, cat, azimuth, year):
        """Create a plagiotropic child axis off host_id, at THETA_LATERAL from the parent dir."""
        pdir = parent_ax.dirv
        d0 = self._azimuth_dir(pdir, THETA_LATERAL_DEG, azimuth)
        # plagiotropic set-point: tilt toward the horizontal set-point angle (§7.1)
        hostpos = self.nodes[host_id].pos
        newp = hostpos + INTERNODE * d0
        nid = self._new_node(newp, host_id, len(self.axes), year)
        child = Axis(len(self.axes), cat=cat, order=parent_ax.order + 1,
                     reit=parent_ax.reit, D=parent_ax.D * D_RESET, apex=nid,
                     dirv=d0, birth=year)
        child.gsa = self._gsa_target(d0)
        self.nodes[nid].axis = child.id
        self.axes.append(child)
        return child

    def _gsa_target(self, outward_hint):
        """Plagiotropic set-point direction: THETA_GSA from vertical, azimuth from the hint."""
        horiz = outward_hint.copy(); horiz[1] = 0.0
        n = np.linalg.norm(horiz)
        horiz = horiz / n if n > 1e-9 else self._perp(np.array([0, 1.0, 0]))
        a = math.radians(THETA_GSA_DEG)
        return math.sin(a) * horiz + math.cos(a) * np.array([0.0, 1.0, 0.0])

    # ======================================================================
    # RELAY DOMINANCE D — the three-phase trajectory (§2.1, iter-4)
    # ======================================================================
    def D_clean(self, ax):
        """Clean (light-independent) relay dominance as a function of the axis's age in modules.
        §2.1 THREE phases: RISES during establishment (acrotony builds — "la dominance d'un relais
        unique est de plus en plus marquée, l'acrotonie augmente"; a fork element "d'abord une forte
        acrotonie et une grande dominance"), THEN decays (crown building — "ensuite diminution ...
        diminution progressive"). The peak is ax.D_peak (set per wave; D_RESET*parent_peak -> 0 at
        the periphery). iter-1..3 had only the decay limb, so fork children were born below Phi_fork
        and could never establish a persistent master. env_release + hcap are applied on top in step()."""
        a = ax.age
        w = max(ax.est_window, 1)
        if a <= w:                                     # establishment: rise from EST_FLOOR*peak to peak
            return ax.D_peak * (EST_FLOOR + (1.0 - EST_FLOOR) * (a / w))
        return ax.D_peak * (1.0 - D_DECAY_AGE) ** (a - w)   # crown-building: decay from peak

    # ======================================================================
    # FIRING (§2) — a fork IS a reiteration
    # ======================================================================
    def terminal_fork(self, ax, relay_host, year, M=2):
        """D fell below Phi_fork at this axis's tip: replace the single relay with 2-3
        co-equal reiterates (start_order = the forking axis's OWN rung). The axis ENDS.
        ★ iter-5: M is now EMERGENT from light-equity among the near-apex buds (fork_multiplicity),
        passed in by the firing step — not a [PROV] coin flip."""
        d = ax.dirv
        # ★ iter-4: the wave decrement acts on the PEAK, not the (low) decayed birth-D. C&E: "d'une
        # vague à l'autre le caractère dominant ... diminue" — it is the establishment dominance that
        # falls wave to wave. A child rebuilds acrotony to child_peak, THEN forks (D_clean handles the
        # rise). Whether the child is a persistent orthotropic MASTER or a terminal plagiotropic
        # secondary is decided on child_peak (the leader it CAN build), not on its low birth dominance.
        child_peak = D_RESET * ax.D_peak
        # ★ iter-4: a leader forking AT the crown ceiling rounds the dome over into PLAGIOTROPIC
        # branches, even if its peak could sustain a master — a tree does not keep throwing vertical
        # leaders once it has reached its height. A fork with room above (D-decay, mid-crown) still
        # makes orthotropic sub-masters. This is what makes the scaffold DEPTH scale with tier: a
        # tall l tree forks masters for several waves before rounding over; a short s/m tree rounds
        # over after one, so its crown is a broad dome on a shallow fork (both emergent).
        at_ceiling = self.nodes[relay_host].pos[1] >= CEIL_FRAC * self.H
        master = (child_peak >= D_MASTER_MIN) and not at_ceiling
        child_cat = ax.cat if master else MAX_CAT     # master stays orthotropic (A1); else terminal
        new_axes = []
        for j in range(M):
            az = (j * 360.0 / M) + self.rng.uniform(-15, 15)
            fd = self._azimuth_dir(d, 22.0, az)       # [PROV] fork half-angle
            p = self.nodes[relay_host].pos + INTERNODE * fd
            nid = self._new_node(p, relay_host, len(self.axes), year)
            self.reit_count += 1
            child = Axis(len(self.axes), cat=child_cat, order=ax.order + (0 if master else 1),
                         reit=self.reit_count, D=child_peak * EST_FLOOR, apex=nid, dirv=fd, birth=year,
                         D_peak=child_peak, est_window=EST_WINDOW_REITER)
            child.gsa = None if child_cat == 1 else self._gsa_target(fd)
            self.nodes[nid].axis = child.id
            self.axes.append(child)
            new_axes.append(child)
        ax.alive = False
        ax.apex = None
        ax.forked = True
        return new_axes

    def latent_bud(self, year, shadow=None, mn=None):
        """Mode 2 (§2.3): dormant buds on OLD WOOD re-erect. The HOST SET is every old woody node
        on ANY axis — crucially the DEAD trunk and dead masters, whose wood persists after they
        stop extending — not just alive cat-1 axes (iter-1/2's inert restriction). Release is
        POSITIONAL, biased LOW (§3.3, §7.2: the basal reiterates are the veteran's heavy low
        limbs); survival is decided AFTER birth by the shed rule, not by a firing-time light gate.
        start_order = s(u_ins): basal -> s=1 orthotropic total reiterate; peripheral -> pauperized.
        Returns the reiterate leaders born this year."""
        if year < LATENT_START_AGE:                   # no re-erection before the tree matures
            return []
        pl = self._pathlen()
        maxpl = max(pl.values()) if pl else 1.0
        # gather old-wood candidates on ANY axis, with a positional (low) release weight
        cand = []
        for nid in range(len(self.nodes)):
            nd = self.nodes[nid]
            if nid == 0 or not nd.alive or nd.foliage:
                continue
            if year - nd.birth < LATENT_MIN_AGE:      # must be old wood
                continue
            u = pl.get(nid, 0.0) / max(maxpl, 1e-6)
            if u < LATENT_MIN_U:                       # the clear bole stays suppressed (see above)
                continue
            w = (1.0 - u) ** LATENT_LOW_BIAS          # low-crown bias (C&E: base of masters = most developed)
            cand.append((w, nid, u))
        cand.sort(reverse=True)                        # most-basal first (deterministic)
        births = []
        placed = []
        for w, nid, u in cand:
            if len(births) >= MAX_LATENT_PER_YEAR:
                break
            if self.rng.random() > LATENT_RATE * w:    # positional release probability
                continue
            p0 = self.nodes[nid].pos
            if any(np.linalg.norm(p0 - q) < LATENT_MIN_SEP for q in placed):
                continue                               # space the year's releases out
            placed.append(p0)
            s = self._start_order(u)                   # positional pauperization -> AU rung
            host_ax = self.axes[self.nodes[nid].axis]
            if s == 1:                                 # total reiterate: a fresh orthotropic leader
                fd = self._azimuth_dir(np.array([0.0, 1.0, 0.0]), 8.0, self.rng.uniform(0, 360))
                gsa = None
            else:                                      # partial reiterate: plagiotropic set-point
                fd = self._azimuth_dir(np.array([0.0, 1.0, 0.0]), THETA_GSA_DEG, self.rng.uniform(0, 360))
                gsa = self._gsa_target(fd)
            p = p0 + INTERNODE * fd
            cid = self._new_node(p, nid, len(self.axes), year)
            self.reit_count += 1
            # ★ iter-4: a latent reiterate also RE-ESTABLISHES (§2.1). A basal s=1 total reiterate is
            # a vigorous orthotropic leader (the veteran's heavy low limb) -> peak = D_RESET, it forks
            # like a young trunk; a pauperized s>1 partial reiterate gets a lower peak (stays a
            # plagiotropic spray). Peak, not a flat birth-D, so a basal reiterate can build a scaffold.
            peak = D_RESET if s == 1 else D_RESET * (0.7 ** (s - 1))
            child = Axis(len(self.axes), cat=s, order=host_ax.order + 1, reit=self.reit_count,
                         D=peak * EST_FLOOR, apex=cid, dirv=fd, birth=year,
                         D_peak=peak, est_window=EST_WINDOW_REITER)
            child.gsa = gsa
            self.nodes[cid].axis = child.id
            self.axes.append(child)
            births.append(child)
        return births

    def _start_order(self, u):
        """s(u_ins): 1 (total, c.r.t.) at the base -> 5 (M.A.U.) at the periphery. §3.3."""
        # linear map, rounded, clamped [1,5]; complete low, pauperized high.
        return int(np.clip(round(1 + u * 4.0), 1, 5))

    def arch_cascade(self, year):
        """★ iter-5: Mode 2 at ARCH SUMMITS (§7.2). For each arched plagiotropic limb (its apex has
        drooped >= ARCH_DROP below its own highest node), re-erect an ORTHOTROPIC reiterate at the
        summit (epitony — the upper/convex side, C&E "au sommet de l'arcure"), and register the distal
        continuation beyond the summit as a dieback candidate (the shed rule kills it once the new
        vertical complex overtops it). This is what turns a single sagging beam into the veteran's
        CHAIN of sagged complexes reaching the ground. Bounded per year; refractory per axis."""
        if year < LATENT_START_AGE:
            return []
        births = []
        cands = []
        for ax in self.axes:
            if not ax.alive or ax.cat == 1 or ax.age < ARCH_MIN_AGE:
                continue
            if year - ax._arched_at < ARCH_REFRACTORY:
                continue
            live_nodes = [n for n in ax.nodes if self.nodes[n].alive]
            if len(live_nodes) < ARCH_MIN_INTERIOR + 2:
                continue
            ys = [self.nodes[n].pos[1] for n in live_nodes]
            si = int(np.argmax(ys))                       # summit = highest live node on the axis
            summit = live_nodes[si]
            apex_y = ys[-1]
            # arched iff the summit is interior (a distal continuation exists) AND the tip drooped below it
            if si > len(live_nodes) - 1 - ARCH_MIN_INTERIOR:
                continue
            if ys[si] < ARCH_MIN_SUMMIT_Y or (ys[si] - apex_y) < ARCH_DROP:
                continue
            cands.append((ys[si] - apex_y, ax, summit, live_nodes[si + 1]))
        cands.sort(reverse=True)                          # deepest arches first (most developed limbs)
        for drop, ax, summit, distal_root in cands[:ARCH_MAX_PER_YEAR]:
            # re-erect: a fresh orthotropic total reiterate springs up from the summit (epitony)
            fd = self._azimuth_dir(np.array([0.0, 1.0, 0.0]), 8.0, self.rng.uniform(0, 360))
            p = self.nodes[summit].pos + INTERNODE * fd
            cid = self._new_node(p, summit, len(self.axes), year)
            self.reit_count += 1
            child = Axis(len(self.axes), cat=1, order=self.axes[self.nodes[summit].axis].order + 1,
                         reit=self.reit_count, D=D_RESET * EST_FLOOR, apex=cid, dirv=fd, birth=year,
                         D_peak=D_RESET, est_window=EST_WINDOW_REITER)
            child.gsa = None                              # orthotropic (re-erection, C5)
            self.nodes[cid].axis = child.id
            self.axes.append(child)
            births.append(child)
            ax._arched_at = year
            # register the distal continuation for dieback: it is overtopped by the new complex and
            # sheds via the SAME tau gate (§7.3), timing emergent (it dies when the reiterate shades it).
            self._arch_distal.append((distal_root, ax))
        return births

    # ======================================================================
    # RATCHET (§5) — radius = monotone max over history
    # ======================================================================
    def ratchet(self, radius, children):
        """★ iter-14 — SAPWOOD = LIVE leaf units; HEARTWOOD = LOST leaf units. A COUNTING law.

        Aye, Brännström & Carlsson 2022 (Tree Physiology 42(11):2174-2185, "Prediction of tree
        sapwood and heartwood profiles using pipe model and branch thinning theory", PMC9652016)
        predicts the whole sapwood/heartwood profile from branch death, on Shinozaki's pipe model
        (1964) plus Hellström et al. 2018's branch thinning. Its two load-bearing equations:

            (5)  A_S(h) = c_S * F_S(h)      F_S = LIVE leaf units above h
            (6)  A_H(h) = c_H * F_H(h)      F_H = LOST leaf units above h   (cumulative, forever)

        ⚠ It was cited here as "Kubo et al. 2022" until 2026-07-13 and had never been opened; iter-12
        and iter-13 were both built on a GUESS at its mechanism, and both were refuted. It is now
        read. The two claims those iterations made on its authority are false, and this is the fix:

          - THE BANK UNIT (Eq. 6). The unit is a LOST LEAF UNIT, and each one contributes c_H
            exactly ONCE, ever. iter-13 banked each dead branch's whole CROSS-SECTION — which
            already contained that branch's own heartwood, which already contained its dead
            children's sections. A recursive double-count. Heartwood therefore grew without bound
            (96% of a 104 yr basal area) and NO scalar could move it, because the defect was in the
            recursion, not in a constant. A count cannot recurse: a leaf unit dies once.
          - c_H != c_S. The paper carries TWO pipe-area constants, fitted separately (its Table 1).
            iter-12's "no new constant" was simply wrong. c_H is the second constant, and it is the
            knob for the sapwood fraction (Platanus is noted for WIDE sapwood, ~50% of basal area).

        We do NOT implement its Eqs 2-4: those are Hellström's STATISTICAL bookkeeping, there to
        estimate leaf counts for a tree you cannot simulate. We simulate — so we count F_S and F_H
        straight off the real skeleton, and the ramification factor kappa (its Eqs 7-8) comes for
        free from the actual topology. Simulate the process; let the appearance emerge.

        A LEAF UNIT is a woody terminal — exactly what grow_foliage() foliates (a live wood node
        with no live wood children) and exactly what the pipe model seeds at R_TIP. So:

            F_S(i) = # live wood terminals in i's subtree      -> r_sap = R_TIP * F_S**(1/p)
            F_H(i) = # dead wood terminals in i's subtree      -> A_dead = C_HEART * F_H
            TOTAL    pi * r**2 = pi * r_sap**2 + A_dead

        r_sap is algebraically identical to iter-13's p-sum recursion (the pipe model is homogeneous
        in the tip radius, so SUM_live r_sap_c**p telescopes to R_TIP**p * F_S) — the live taper law
        is UNCHANGED and still stands. Only the dead bank changed, and it is now a pure count, so it
        is monotone by construction (a killed subtree is never resurrected: _kill_subtree takes the
        whole subtree, so dead => every descendant dead). The ratchet on the TOTAL stays as a guard.

        Dead wood is still skinned as a FOSSIL: its radius is frozen at its girth on the year it
        died, never rewritten."""
        n = len(self.nodes)
        hist, r_sap, a_dead = self._r_hist, self._r_sap, self._a_dead
        f_live, f_lost, a_lost = self._f_live, self._f_lost, self._a_lost
        for arr in (hist, r_sap, a_dead, f_live, f_lost, a_lost):
            if len(arr) < n:
                arr.extend([0.0] * (n - len(arr)))
        order = self._topo_leaves_first(children)
        for i in order:
            nd = self.nodes[i]
            if nd.foliage:                            # leaves are not wood — no radius, no pipe
                continue
            # --- the leaf-unit census (Eqs 5 & 6). Foliage children carry no pipe and are skipped.
            kids = [c for c in children[i] if not self.nodes[c].foliage]
            live_kids = [c for c in kids if self.nodes[c].alive]
            if nd.alive:
                # a live terminal IS one live leaf unit (it is what grow_foliage foliates); a live
                # internode owns none of its own — it just sums what stands above it.
                fl = 1.0 if not live_kids else sum(f_live[c] for c in kids)
                fh = sum(f_lost[c] for c in kids)
                ah = sum(a_lost[c] for c in kids)
            else:
                # dead wood: no live units above it (a shed takes the whole subtree). A dead TERMINAL
                # is one lost leaf unit — counted ONCE, forever. A dead internode was never a leaf
                # unit at death; it only carries the lost units of its own dead tips. No recursion.
                # ★ iter-15: the AREA it banks is the c_H of the year it died (nd.death_c), because
                # N_def — and so c_H — grows with the tree. The count fh is kept for diagnostics.
                fl = 0.0
                fh = 1.0 if not kids else sum(f_lost[c] for c in kids)
                ah = nd.death_c if not kids else sum(a_lost[c] for c in kids)
            f_live[i], f_lost[i], a_lost[i] = fl, fh, ah
            if not nd.alive:                          # dead wood is a FOSSIL: frozen, still skinned
                radius[i] = max(radius[i], hist[i])
                continue
            r_s = self.r_tip * fl ** (1.0 / PIPE_POWER)   # ★ iter-8/15: the tip seed carries N_def(t)
            dead = ah                                     # ...and each lost unit was worth c_H(death)
            r_sap[i], a_dead[i] = r_s, dead
            r_tot = math.sqrt(r_s * r_s + dead / math.pi)
            radius[i] = max(radius[i], hist[i], r_tot)    # THE RATCHET — never decreases
            hist[i] = radius[i]                           # ...and it is remembered, so it can't
        return radius

    # ======================================================================
    # ★ iter-8 — STRUCTURAL RADIUS = max(pipe, self-support).  Position A.
    # ======================================================================
    def structural_radius(self, children, r_pipe):
        """The wood the tree must actually build: the pipe-model radius OR the cantilever radius
        its own self-weight demands, whichever is larger.

            M_i = g * || SUM_j m_j (p_j - p_i)_xz ||   over i's subtree      (bending moment)
            r_mech = (4 M / pi sigma)^(1/3)                                  (Metzger uniform stress)

        The loads are PARALLEL and VERTICAL, so the moment is a VECTOR sum: a symmetric vertical
        axis cancels to ~0 and pays nothing, while a limb held out sideways pays d^3 ∝ M·L. The
        2:1 height/width asymmetry is therefore a CONSEQUENCE of the statics, not an assumption.

        m_j depends on the radii, which depend on M, so this is a FIXED POINT -- and it must be
        solved on the STRUCTURAL radius (max of both terms), not on r_mech alone. Solving it on
        r_mech alone understates the mass by the pipe term and makes the whole mechanical demand
        look ~4x smaller than it is; that error is what made the ADR falsification's T3 report the
        mechanical term as INERT. It is not: against the pipe radius the tree really builds, it
        binds on 42-62% of load-bearing wood (lever > 2 m) and on 0% at the bole. Re-derived in
        tmp/grower_selfconsistent_check.py.

        ⚠ THE ITER-8 CLAIM ABOVE WENT STALE, AND THE HISTORY IS THE LESSON. Re-measured at the
        iter-9/iter-14 constants (iter-16, tmp/iter16_mech_probe.py), statics bound on 9/958 and
        26/10917 load-bearing nodes and exceeded the pipe by at most 3%: median r_mech/r_pipe =
        0.14 / 0.20 / 0.23, and the bill below read 0.0000 m^3 in all 104 years. The term looked DEAD.
        It was not dead — IT WAS DROWNED, by a DBH_CALIB left stale across the heartwood ratchet
        (the pipe was 3.4x too fat, and r_mech falls only as r_pipe^(2/3) where wood mass dominates
        the moment and NOT AT ALL where leaf mass does).

        ★ iter-17 re-centred the pipe (k = 1/3.37) and THE TERM WOKE UP. Same probe, unmodified:
        median r_mech/r_pipe = 0.22 / 0.56 / 0.52, max 2.54, and on load-bearing wood (lever > 2 m)
        it BINDS on 55% (m) and 72% (l) of nodes. The bill leaves zero for the first time: on l it is
        non-zero in 86 of 104 years and takes 4.8% of the annual pool at yr 20, 20.7% at yr 47 and
        49-64% past yr 60 — while remaining 0.0% at yr 10. It is the ONLY law in this model with an
        absolute length scale (SIGMA, GRAV, RHO), hence the only one that is not scale-free, hence
        the only available source of a SIZE term. Before you retire a mechanism for reading zero,
        ask what else in the model sets the scale it is measured against.
        """
        order = self._topo_leaves_first(children)     # leaves-first
        N = len(self.nodes)
        pos = np.array([nd.pos for nd in self.nodes], dtype=float)
        wood = np.array([nd.alive and not nd.foliage for nd in self.nodes])
        leaf = np.array([nd.alive and nd.foliage for nd in self.nodes])
        seglen = np.zeros(N)
        for i in range(1, N):
            p = self.nodes[i].parent
            if p >= 0:
                seglen[i] = np.linalg.norm(pos[i] - pos[p])
        r_pipe = np.asarray(r_pipe, dtype=float) * wood
        leafm = np.where(leaf, LEAF_KG, 0.0)
        kids = [[c for c in children[i] if self.nodes[c].alive] for i in range(N)]

        r = r_pipe.copy()
        for _ in range(60):
            m = np.where(wood, RHO_GREEN * math.pi * r ** 2 * seglen, 0.0) + leafm
            M_sub = np.zeros(N)                       # subtree mass
            S_sub = np.zeros((N, 3))                  # subtree first moment of mass
            for i in order:
                ms, ss = m[i], m[i] * pos[i]
                for c in kids[i]:
                    ms += M_sub[c]; ss += S_sub[c]
                M_sub[i] = ms; S_sub[i] = ss
            off = S_sub - M_sub[:, None] * pos        # SUM_j m_j (p_j - p_i)
            Mb = GRAV * np.linalg.norm(off[:, [0, 2]], axis=1)   # horizontal lever arm only
            r_mech = np.where(wood, (4.0 * Mb / (math.pi * SIGMA)) ** (1.0 / 3.0), 0.0)
            r_new = np.maximum(r_pipe, r_mech)
            if not np.all(np.isfinite(r_new)) or r_new.max() > 5.0:
                break                                 # cannot hold itself up — keep the last iterate
            d = np.abs(r_new - r).max()
            r = 0.5 * r + 0.5 * r_new                 # damped, for a stable fixed point
            if d < 1e-6:
                break
        # ★ iter-19: M_sub at the ROOT — the mass the tree already holds up, wood + foliage. This is
        # N_def's numerator (see update_n_def): it falls out of THIS fixed point for free, it is
        # HISTORY (wood laid down in past years), and it is what iter-18 measured the loop gain on.
        self._m_sub = float(M_sub[0])
        return r, seglen

    def support_bill(self, children, r_struct, r_pipe, seglen):
        """★ iter-8 — THE PRICE OF STANDING UP, per axis, this year, in m^3 of wood.

        ⚠ THE BILL IS THE MECHANICAL SURCHARGE, NOT THE WHOLE THICKENING BILL:

            surcharge_i = pi * (r_struct^2 - r_pipe^2) * L        (>0 only where statics wins)

        Charging the FULL thickening — pipe wood included — was tried first and is WRONG, in a way
        worth recording because it looks right. Pipe wood is the tree's PLUMBING: the pipe model
        makes it proportional to the leaf area it feeds, so it is self-financing, and above all it
        is LEVER-INDEPENDENT — a limb's pipe radius depends on how many tips it carries, not on how
        far out it holds them. Charging it therefore adds no crown bound at all, and it does active
        harm: the trunk's pipe bill is the largest in the tree and is charged at the ROOT, so it
        chokes the whole crown uniformly instead of taxing the limbs that overreach. Measured: no
        ALPHA existed at which H reached 14 m and the crown stayed under 18 m — the two scaled
        together, and the crown came out WIDER than iter-7 (26-34 m). The lever-independent tax
        swamped the lever-dependent one, which is the entire content of Position A.

        The surcharge is the part statics demands OVER what the plumbing would have laid down
        anyway. It is ~0 for a near-vertical axis (whose moment cancels — see structural_radius)
        and rises as lever^+1.09 (falsification T2). That asymmetry is the mechanism.

        Every axis pays its own out of its own share (_distribute), so the bills telescope and no
        wood is charged twice. A newborn section's baseline is R_TIP, not 0: the wood inside the
        tip seed was already bought as EXTENSION when the metamer was laid down (pi*R_TIP^2*l, see
        grow_module)."""
        N = len(self.nodes)
        wood = np.array([nd.alive and not nd.foliage for nd in self.nodes])
        prev = np.full(N, self.r_tip)
        n_old = len(self._r_prev)
        prev[:n_old] = self._r_prev                   # sections that existed last year keep their girth
        prev = np.where(wood, prev, 0.0)
        r_pipe = np.asarray(r_pipe, dtype=float)
        # the surcharge already standing (last year's, on last year's plumbing) is not re-charged:
        # bill only the INCREASE in mechanical excess over the pipe radius.
        excess_now = np.maximum(r_struct ** 2 - r_pipe ** 2, 0.0)
        excess_was = np.maximum(prev ** 2 - r_pipe ** 2, 0.0)
        dv = np.where(wood, math.pi * np.maximum(excess_now - excess_was, 0.0) * seglen, 0.0)
        bill = {ax.id: 0.0 for ax in self.axes}
        for i in range(1, N):
            a = self.nodes[i].axis
            if a >= 0 and dv[i] > 0.0:
                bill[a] = bill.get(a, 0.0) + float(dv[i])
        self._r_prev = np.maximum(prev, r_struct)     # the ratchet applies to the baseline too
        self._bill_total = float(dv.sum())            # diagnostics: is the mechanism biting at all?
        return bill

    # ======================================================================
    # FOLIAGE (§9.2, iter-2) — the transient A4 light-gatherer layer
    # ======================================================================
    def grow_foliage(self, year, children):
        """Every living structural TIP (a woody node with no living woody children) puts out a
        cohort of FOLIAGE_PER_TIP transient A4 leaves — this year's shoot.

        ★ iter-24: AND every OLDER live internode still standing in the light bears A5 SHORT
        SHOOTS, at the same linear density (FOLIAGE_PER_TIP per GU_NODES[cat] internodes). That
        is what makes a limb's income grow with the limb; see the SHORT_SHOOT_LIGHT block. The
        light field is LAST year's banked one (iter-6) — a bud breaks on the light it stood in
        when it was set, which is exactly the right causality."""
        n_new = len(self.nodes)       # short shoots may only sit on wood that already existed
        tips = [i for i, nd in enumerate(self.nodes)
                if nd.alive and not nd.foliage and i != 0
                and not any(self.nodes[c].alive and not self.nodes[c].foliage for c in children[i])]
        self._n_tips = len(tips)      # ★ iter-15: the live leaf-unit count — N_def's denominator
        for t in tips:
            base = self.nodes[t].pos
            for k in range(FOLIAGE_PER_TIP):
                off = self.rng.normal(0, 1, 3); off /= (np.linalg.norm(off) + 1e-9)
                p = base + FOLIAGE_SPREAD * off
                self.nodes.append(Node(p, t, self.nodes[t].axis, year, foliage=True))
        # --- ★ iter-24: the A5 short-shoot layer, on OLDER LIT WOOD ---
        tipset = set(tips)
        n_shoots = 0
        for i in range(1, n_new):
            nd = self.nodes[i]
            if not nd.alive or nd.foliage or i in tipset:
                continue
            if nd.birth >= year:                      # this year's shoot: the tip cohort IS its foliage
                continue
            if self.light_at(nd.pos, self._shadow, self._mn) < SHORT_SHOOT_LIGHT:
                continue                              # a dark internode bears no leaves — a clean bole
            cat = self.axes[nd.axis].cat if nd.axis >= 0 else 1
            if self.rng.random() >= FOLIAGE_PER_TIP / GU_NODES.get(cat, GU_NODES[MAX_CAT]):
                continue                              # the linear density, sampled
            off = self.rng.normal(0, 1, 3); off /= (np.linalg.norm(off) + 1e-9)
            self.nodes.append(Node(nd.pos + FOLIAGE_SPREAD * off, i, nd.axis, year, foliage=True))
            n_shoots += 1
        self._n_short_shoots = n_shoots               # diagnostic: is the layer bearing?

    def age_foliage(self, year):
        """Leaf cohorts abscisse after FOLIAGE_LIFE years (C&E: A4/A5 self-prune 1-4 yr)."""
        for nd in self.nodes:
            if nd.foliage and nd.alive and year - nd.birth >= FOLIAGE_LIFE:
                nd.alive = False

    # ======================================================================
    # LIGHT (§7.3, F1) — shadow-propagation voxel grid seeded by FOLIAGE
    # ======================================================================
    def build_shadow(self, children):
        """Living foliage deposits shadow into voxels below it (Palubicki cone). Returns
        (shadow dict, grid origin). Falls back to structural tips before any foliage exists."""
        src = [i for i, nd in enumerate(self.nodes) if nd.alive and nd.foliage]
        if not src:
            src = [i for i, nd in enumerate(self.nodes)
                   if nd.alive and i != 0 and not any(self.nodes[c].alive for c in children[i])]
        if not src:
            return {}, np.zeros(3)
        P = np.array([self.nodes[i].pos for i in src])
        mn = P.min(0) - VOX
        gi = np.floor((P - mn) / VOX).astype(int)
        # ★ iter-15: THE CROWN VOLUME — the space the live crown CLAIMS: the convex hull of the live
        # foliage cloud. It is N_def's numerator, and it is an OUTPUT: the tree earned every cubic
        # metre of it by paying for the extension that reached there.
        # ⚠ NOT the occupied-voxel count. Our armature carries only ~10–30 tips × 12 markers, so the
        # voxels those markers happen to touch is a measure of the SAMPLING, and it is bounded by
        # 12*n_tips voxels — which would make N_def saturate at a ceiling of its own. That is the
        # very disease iter-15 exists to cure (a fixed point in tips). The deferred A4/A5 twigs are
        # exactly the ones that FILL the space between the sampled tips, so the volume they fill is
        # the envelope, not the samples.
        self._crown_vol = self._hull_volume(P)
        # ★ iter-15: and each marker now casts the shade of the N_def twigs it STANDS FOR, not of one
        # twig. S == 1 at the anchor, so SHADOW_A/B keep their calibrated meaning there; a big tree
        # (S > 1) shades its own interior harder, and that self-shading is what closes the crown and
        # makes a carrying capacity EMERGE instead of being looked up (Hellström, Discussion p. E45).
        shadow = {}
        for (gx, gy, gz) in gi:
            for dl in range(0, SHADOW_LEVELS):
                s = (self.s_def if S_IN_SHADE else 1.0) * SHADOW_A * SHADOW_B ** (-dl)
                if s < 0.02:
                    break
                for dx in range(-dl, dl + 1):
                    for dz in range(-dl, dl + 1):
                        key = (gx + dx, gy - dl, gz + dz)
                        shadow[key] = shadow.get(key, 0.0) + s * math.exp(-(dx*dx+dz*dz)/(2*(dl+1)))
        return shadow, mn

    @staticmethod
    def _hull_volume(P):
        """Volume of the crown envelope: the convex hull of the live foliage cloud (scipy Qhull).
        Degenerate while the seedling's leaves are still coplanar/collinear — fall back to the
        bounding volume of the marker cloud, which is what a handful of leaves really claims."""
        if len(P) >= 4:
            try:
                return float(ConvexHull(P).volume)
            except QhullError:                        # coplanar seedling crown
                pass
        span = P.max(0) - P.min(0)
        return float(np.prod(np.maximum(span, VOX)))

    def light_at(self, pos, shadow, mn):
        g = tuple(np.floor((pos - mn) / VOX).astype(int))
        # the `own` term un-shades a site from its OWN deposit, so it tracks the S-scaled deposit
        # (iter-15). It is the ZERO of the optical depth: at s == own the site is unshaded and reads C.
        own = (self.s_def if S_IN_SHADE else 1.0) * SHADOW_A
        tau = max(shadow.get(g, 0.0) - own, 0.0)          # optical depth above this site
        # ★★★ iter-25: Beer-Lambert. Strictly positive at every depth — no clamp, no dead zone.
        # Tangent to the old max(C - tau, 0) at tau = 0, so the calibrated LIT regime is unchanged.
        return FULL_LIGHT * math.exp(-LIGHT_K * tau)

    def foliage_light(self, shadow, mn):
        """Light gathered by each living leaf."""
        return {i: self.light_at(nd.pos, shadow, mn)
                for i, nd in enumerate(self.nodes) if nd.alive and nd.foliage}

    # ======================================================================
    # ★ iter-5: APEX LIGHT-DOMINANCE (§2.1 "l'acrotonie augmente" / §7.5 light-equity)
    # ======================================================================
    def apex_dominance(self, pos, shadow, mn):
        """How much more light the apex gets than the crown PLANE around it at the same height.
        An EMERGENT leader poking above the crown sees its apex » its lateral neighbours -> strong
        acrotony -> a single dominant relay -> it HOLDS a long leader (C&E: "la dominance d'un relais
        unique est de plus en plus marquée"). A leader buried level in the crown sees apex ~= neighbours
        -> co-equal relays -> it FORKS (C&E: "milieu très ensoleillé -> fourches orthotropes"). This is
        the light-EQUITY the ratified F1 amendment (§7.5) names — NOT absolute light. Ratio > 1 = the
        apex wins its light; ~1 = co-equal."""
        L_apex = self.light_at(pos, shadow, mn)
        ring = []
        for az in (0.0, 90.0, 180.0, 270.0):
            a = math.radians(az)
            q = pos + DOM_RING_R * np.array([math.cos(a), 0.0, math.sin(a)])
            ring.append(self.light_at(q, shadow, mn))
        L_local = float(np.mean(ring)) if ring else L_apex
        return L_apex / (L_local + 1e-6)

    def fork_multiplicity(self, ax, shadow, mn):
        """EMERGENT M (2 or 3, C&E's "fourche de 2 ou 3"): the number of near-apex spiral buds that
        are within DOM_EQUITY_TOL of the brightest — the co-equally-lit relay candidates. Replaces
        the [PROV] coin flip. Light-equity: an even light field over the top module -> 3 co-equal
        relays; a slightly acrotonic one -> 2. Clamped to [2,3] per C&E."""
        buds = [h for h in ax._last_spiral if 0 <= h < len(self.nodes) and self.nodes[h].alive]
        if len(buds) < 2:
            return 2
        L = [self.light_at(self.nodes[h].pos, shadow, mn) for h in buds]
        Lmax = max(L)
        coeq = sum(1 for x in L if x >= Lmax * (1.0 - DOM_EQUITY_TOL))
        return int(np.clip(coeq, 2, 3))

    # ======================================================================
    # SHED (§7.3) — light_gathered/size < tau  => remove subtree, keep radius
    # ======================================================================
    # ======================================================================
    # ★ iter-6: THE RESOURCE ECONOMY (Palubicki 2009 §4.2 — extended Borchert-Honda,
    # priority model). Sets ax._v for every live axis. See the constants block.
    # ======================================================================
    def _axis_tree(self):
        """children-axis lists + the root axis, from the node parent links."""
        kids = {ax.id: [] for ax in self.axes}
        roots = []
        for ax in self.axes:
            pnode = self.nodes[ax.nodes[0]].parent
            pax = self.nodes[pnode].axis if pnode >= 0 else -1
            if pax >= 0 and pax != ax.id:
                kids[pax].append(ax.id)
            else:
                roots.append(ax.id)
        return kids, roots

    def _prio_weight(self, rank, n):
        """Palubicki Fig. 8c: piecewise-linear weight, W_MAX at the head of the priority list
        falling to W_MIN by rank fraction KAPPA. Large weights to the few most productive
        branches => more excurrent; flatter => more decurrent."""
        if n <= 1:
            return W_MAX
        x = rank / (n - 1)
        if x >= KAPPA:
            return W_MIN
        return W_MAX + (W_MIN - W_MAX) * (x / KAPPA)

    def allocate_resource(self, shadow, mn, year):
        """BASIPETAL: light gathered by living foliage accumulates to the base (Q per axis subtree,
        plus the bud count). ACROPETAL: v_base = ALPHA*Q_base is redistributed down the axis tree by
        the priority model. The tree can only spend the light it actually caught, so as the bud count
        rises the per-apex share falls and extension self-limits. Crown radius is an OUTPUT."""
        for ax in self.axes:
            ax._v = 0.0
        kids, roots = self._axis_tree()
        # --- basipetal pass: Q (light gathered) and nbuds, per axis SUBTREE ---
        q_own = {ax.id: 0.0 for ax in self.axes}
        for nd in self.nodes:
            if nd.alive and nd.foliage and nd.axis >= 0:
                # ★ iter-15: a marker INTERCEPTS the light of the N_def twigs it stands for. This is
                # the half that was missing: N_def was on the cost side and in the ledger, never in
                # the income, so a tip paid 354 twigs' worth of wood and earned one twig's worth of
                # light. With both sides scaled, income ∝ N_def and cost ∝ N_def^(2/p) — and p > 2,
                # so they no longer cancel and the tip count is no longer a fixed point.
                gain = self.s_def if S_IN_LIGHT else 1.0
                q_own[nd.axis] += gain * self.light_at(nd.pos, shadow, mn)
        order = []                                   # children-before-parents
        stack = list(roots)
        while stack:
            a = stack.pop()
            order.append(a)
            stack.extend(kids[a])
        q_sub, n_sub, cap_sub = {}, {}, {}
        for a in reversed(order):
            ax = self.axes[a]
            live_apex = 1 if (ax.alive and ax.apex is not None) else 0
            q_sub[a] = q_own[a] + sum(q_sub[c] for c in kids[a])
            n_sub[a] = live_apex + sum(n_sub[c] for c in kids[a])
            # ★ iter-29: THE CAPACITY PASS. What is the most this subtree can actually SPEND?
            # An apex's extension saturates at l_afford == INTERNODE (ext hits its min(1, .) clamp),
            # so resource allocated above that buys ZERO further reach and is silently discarded --
            # 95.0% of the whole pool, measured (iter-28). Capacity is therefore the clamp point,
            # it is additive up the axis tree, and _distribute water-fills against it.
            cap_sub[a] = (self._bill.get(a, 0.0)
                          + (self._apex_cap(ax) if live_apex else 0.0)
                          + sum(cap_sub[c] for c in kids[a] if n_sub[c] > 0))
        # BOOTSTRAP: before any foliage exists (year 1) the tree has caught no light. A seedling
        # grows on its stored reserves — give every apex enough to buy one full module.
        if not roots or sum(q_sub[r] for r in roots) <= 0.0:
            for ax in self.axes:
                if ax.alive and ax.apex is not None:
                    ax._v = GU_NODES[ax.cat] * math.pi * self.r_tip ** 2 * INTERNODE
            return
        # --- acropetal pass: distribute v down the axis tree ---
        apical = year <= APICAL_OFF_YEAR
        self._v_base = ALPHA * sum(q_sub[r] for r in roots)   # diagnostic: the whole year's pool
        self._spill_residue = 0.0        # pool above the WHOLE TREE's capacity: nothing can buy it
        for r in roots:
            self._distribute(r, ALPHA * q_sub[r], kids, q_own, q_sub, n_sub, apical, cap_sub)

    def _apex_cap(self, ax):
        """★ iter-29: the CLAMP POINT — the allocation at which l_afford == INTERNODE and this
        apex's extension saturates. One more m3 above this buys exactly zero further reach, so
        spilling it to a starving sibling costs the winner NOTHING. (vigour scales what the money
        BUYS, not what the apex can be GIVEN, so it is deliberately absent here: capping at the
        spend rather than at the clamp would shorten the module to vigour^2 -- a behaviour change,
        not a conservation.)"""
        return GU_NODES[ax.cat] * math.pi * self.r_tip ** 2 * INTERNODE

    def _distribute(self, a, v, kids, q_own, q_sub, n_sub, apical, cap_sub):
        ax = self.axes[a]
        # ★ iter-8, POSITION A — THE SUPPORT BILL IS PAID FIRST, off the top, before anything this
        # axis carries can be spent on growing. The wood that holds an axis out is not optional and
        # it is not free: it comes out of the same finite pool as extension. A near-vertical axis
        # cancels its own moment and is charged ~nothing; a limb held out 8 m pays ~22 m^3 of
        # thickening per 1 m^3 it reaches further (falsification T4), so its apex is left with
        # almost nothing and its extension collapses to a short shoot. That -- not a cap, not a
        # tropism, not a fitted taper -- is what bounds the crown.
        #
        # Each axis pays only for ITS OWN sections; every descendant axis pays its own out of the
        # share it receives, so the bills telescope to the tree's total annual thickening exactly.
        # If the bill exceeds what reaches the axis, the whole subtree gets nothing this year: it
        # is spending everything it earns on standing up. Repeat that and the shed rule takes it.
        v = max(0.0, v - self._bill.get(a, 0.0))
        if v <= 0.0:
            return
        # the candidates competing for this axis's resource: its OWN terminal bud (a single-metamer
        # branch, per the paper) and each child axis it supports.
        # ⚠ The apex's Q is the light gathered by the FOLIAGE THIS AXIS BEARS (q_own) — NOT the point
        # exposure light_at(apex). Using the point value leaks the axis's own foliage out of the
        # economy (it is inside q_sub but assigned to no candidate) and scores a single bud, on a 0..7
        # point scale, against sibling SUBTREE sums in the hundreds — so every apex is crushed by its
        # own children and the whole tree starves. With q_own, sum(candidate Q) == q_sub[a] exactly,
        # the allocation telescopes, and each bud ends up with roughly what its own leaves caught.
        cands = []                                   # (priority_key, Q, kind, id)
        if ax.alive and ax.apex is not None:
            q_apex = q_own[a]                        # one bud, so this is also its mean-light-per-bud
            cands.append((q_apex, q_apex, "apex", a))
        for c in kids[a]:
            if n_sub[c] <= 0:                        # a dead subtree buys nothing
                continue
            cands.append((q_sub[c] / n_sub[c], q_sub[c], "axis", c))   # key = mean light per bud
        if not cands:
            return
        cands.sort(key=lambda t: -t[0])
        # APICAL CONTROL (§ the excurrent->decurrent progression): while it lasts, the terminal bud
        # heads the priority list irrespective of its light. Removing it with age is what turns the
        # young excurrent leader into the old decurrent, spreading crown.
        if apical:
            for i, t in enumerate(cands):
                if t[2] == "apex":
                    cands.insert(0, cands.pop(i))
                    break
        # ★ iter-7: DOMINANCE-WEIGHTED SPLIT. The share is Q (light earned) x rank weight x D — the
        # candidate's RELAY DOMINANCE. This is where C&E's D belongs and where iter-6 was missing it.
        # iter-6 split the pool by light alone, so the split "telescoped to light-proportional": a bud
        # at the sunlit periphery kept f~1 forever and light REWARDED lateral runaway, which is why no
        # economy could bound the crown. But D is precisely apical control (the dominance of the relay),
        # and in Borchert-Honda apical control acts on the SPLIT, not on the internode. A leader (D~1)
        # now outbids a subordinate lateral (wave-1 D~0.6, wave-2 ~0.36) for the same finite pool.
        # Resource is CONSERVED: what a lateral does not get, the leader does — so this pauperizes the
        # crown periphery without starving it. (Making D a second MULTIPLIER on internode length instead
        # — capability x affordability — was tried and is wrong: it double-penalizes the axes that have
        # neither yet, drives ext under EXT_MIN at birth, and DORMANT_ABORT then amputates the outer
        # crown. Measured: every wave below the trunk died at mean age <2.3 yr of 20, spread 5.9 m.)
        # D_clean (not D_eff) on purpose: light already enters via Q, and D_clean is defined for a
        # newborn (peak * EST_FLOOR), whereas D_eff is a year stale here and unset at birth.
        wq = [t[1] * self._prio_weight(i, len(cands))
              * max(self.D_clean(self.axes[t[3]]), 1e-3) ** APICAL_K
              for i, t in enumerate(cands)]
        tot = sum(wq)
        if tot <= 0.0:
            return
        # ★★★ iter-29: WATER-FILLING, not division. THE CLAMP IS A CONSTRAINT, NOT A DISCARD.
        # Until now every candidate took its weighted share whatever it could do with it, and the
        # share above its clamp was thrown away: the rim as a class took 60-85% of the pool and its
        # MEDIAN member was funded at 0.000, because the top 3 apices took 39-100% of it (gini 0.96)
        # -- and then could not spend it (95.0% of the pool evaporated). The winners are ALREADY at
        # the clamp, so what they cannot spend is worth zero reach to them and a whole module to a
        # starving sibling. So: clip each share at the candidate's capacity, re-split the clipped
        # remainder among the candidates still below theirs, and iterate. The priority weights are
        # UNCHANGED -- they still decide who fills FIRST, which is the whole of the habit; they no
        # longer decide who is starved by a winner that had no use for the money.
        # (Palubicki 2009 §4.2 gives the surplus a botanical sink instead -- `n = floor(v)`, more
        # metamers. That was tried at iter-6 and grows a bare pole with a few whips. Spill first: it
        # is the conservative half, and it CONSERVES what the paper's split already assumed.)
        caps = [self._apex_cap(self.axes[cid]) if kind == "apex" else cap_sub[cid]
                for (key, q, kind, cid) in cands]
        alloc = [0.0] * len(cands)
        active = [i for i in range(len(cands)) if caps[i] > 0.0 and wq[i] > 0.0]
        rem = v
        while rem > 1e-15 and active:
            tw = sum(wq[i] for i in active)
            if tw <= 0.0:
                break
            spilled = 0.0
            still = []
            for i in active:
                give = rem * wq[i] / tw
                room = caps[i] - alloc[i]
                take = min(give, room)
                alloc[i] += take
                spilled += give - take
                if caps[i] - alloc[i] > 1e-15:
                    still.append(i)
            rem, active = spilled, still
        self._spill_residue += rem       # every candidate is saturated: this cannot be spent at all
        for i, (key, q, kind, cid) in enumerate(cands):
            if alloc[i] <= 0.0:
                continue
            if kind == "apex":
                self.axes[cid]._v = alloc[i]
            else:
                self._distribute(cid, alloc[i], kids, q_own, q_sub, n_sub, apical, cap_sub)

    def shed(self, light, children, year=None):
        order = self._topo_leaves_first(children)     # leaves first
        lg = {}; sz = {}
        for i in order:
            if self.nodes[i].foliage:                 # a leaf: contributes light, no "size"
                lg[i] = light.get(i, 0.0); sz[i] = 0
                continue
            l = 0.0; s = 1                            # a woody internode: size 1
            for c in children[i]:
                if self.nodes[c].alive:
                    l += lg.get(c, 0.0); s += sz.get(c, 0)
            lg[i] = l; sz[i] = s
        # decide top-down: shed a subtree whose ratio is below tau (but never node 0/trunk base)
        shed_roots = []
        for ax in self.axes:
            # only the SEED TRUNK (axis 0) is shed-protected (§7.3: "the trunk's subtree
            # gathers all the tree's light"). Every other axis — including reiterate leaders —
            # can be overtopped and shed (branch autonomy; C&E apical mortality).
            if not ax.alive or ax.id == 0:
                continue
            # ★ iter-3: one-year shed GRACE. An axis born THIS year has not yet foliated (masters
            # and latent-bud reiterates fire AFTER the year's foliation step), so its subtree
            # light is spuriously 0 -> it would shed the instant it appears. A newly-released
            # reiterate gets one season to establish before the survival gate applies. [PROV]
            if year is not None and ax.birth == year:
                continue
            root = ax.nodes[0]
            if not self.nodes[root].alive:
                continue
            ratio = lg.get(root, 0.0) / max(sz.get(root, 1), 1)
            if ratio < TAU_SHED:
                shed_roots.append((root, ax))
        for root, ax in shed_roots:
            self._kill_subtree(root, children)
            ax.alive = False
        # ★ iter-5: ARCH-CASCADE DIEBACK (§7.2). The distal continuation beyond an arch summit is a
        # subtree that is NOT its own axis root, so the per-axis gate above cannot reach it. Evaluate
        # it here on the SAME tau ratio: once the summit reiterate has grown up and overtopped it, its
        # light/size falls below tau and it dies back. Timing is emergent (it dies when shaded), not
        # scheduled. Keep the radius (ratchet) — the dead distal wood already baked its girth in.
        n_arch = 0
        still = []
        for droot, ax in self._arch_distal:
            if droot >= len(self.nodes) or not self.nodes[droot].alive:
                continue                                   # already gone (parent shed, or reprocessed)
            ratio = lg.get(droot, 0.0) / max(sz.get(droot, 1), 1)
            if ratio < TAU_SHED:
                self._kill_subtree(droot, children)
                n_arch += 1
            else:
                still.append((droot, ax))                  # not yet overtopped — re-check next year
        self._arch_distal = still
        return len(shed_roots) + n_arch

    # ======================================================================
    # POSTURE (§7.2) — plagiotropic axes sag then right; A1 stays orthotropic
    # ======================================================================
    def posture(self, radius, children):
        subtree_mass = self._subtree_mass(radius, children)
        for ax in self.axes:
            if not ax.alive or ax.cat == 1 or ax.gsa is None:
                continue
            tip = ax.apex
            if tip is None:
                continue
            # ★ iter-4: ASCEND-THEN-ARCH (§7.2). iter-3 used right = RIGHT_K/r; at a thin tip
            # (r≈R0) that is a HUGE constant that pinned every limb to its set-point, so the
            # accumulating sag could never droop the tip and the limb grew as a dead-straight spoke.
            # The faithful picture: righting capacity is ~bounded (reaction wood), while sag grows
            # with the limb's own accumulating LOAD × LEVER. So a YOUNG short limb (sag « right)
            # holds its ascending set-point; an OLD long heavy limb (sag » right) loses the contest
            # and the tip's growth direction progressively DROOPS — over years the axis traces an
            # arch (proximal rising, distal drooping, C&E's "retombantes"). The set-point is
            # moderately ascending again (GSA below), and the arch — not a flat set-point — is what
            # keeps the crown from climbing away. Alméras & Fournier: without righting it would go
            # fully weeping; the bounded right keeps a slow, non-collapsing arch.
            mass = subtree_mass.get(ax.nodes[0], 1.0)
            lever = np.linalg.norm(self.nodes[ax.apex].pos - self.nodes[ax.nodes[0]].pos)
            sag = SAG_K * mass * lever
            right = RIGHT_K                                   # ~bounded righting (was RIGHT_K/r)
            frac_to_gsa = np.clip(right / (right + sag + 1e-6), 0.05, 0.9)
            d = self._rot_toward(ax.dirv, ax.gsa, frac_to_gsa)     # pull toward ascending set-point
            # the fraction NOT righted becomes downward arch — the tip droops as load wins
            droop = np.clip((1.0 - frac_to_gsa) * DROOP_K, 0.0, 0.6)
            d = self._rot_toward(d, np.array([0.0, -1.0, 0.0]), droop)
            ax.dirv = d / (np.linalg.norm(d) + 1e-12)

    # ======================================================================
    # DERIVED-GRAPH UTILITIES
    # ======================================================================
    def _children(self, include_dead=True):
        ch = {i: [] for i in range(len(self.nodes))}
        for i, nd in enumerate(self.nodes):
            if nd.parent >= 0 and (include_dead or nd.alive):
                if include_dead or self.nodes[nd.parent].alive:
                    ch[nd.parent].append(i)
        return ch

    def _topo_leaves_first(self, children):
        order = []; seen = [False] * len(self.nodes)
        stack = [(0, False)]
        while stack:
            nid, proc = stack.pop()
            if proc:
                order.append(nid); continue
            if seen[nid]:
                continue
            seen[nid] = True
            stack.append((nid, True))
            for c in children[nid]:
                stack.append((c, False))
        return order

    def _pathlen(self):
        pl = {0: 0.0}
        # BFS from root
        order = self._topo_leaves_first(self._children())[::-1]  # root-first
        for i in order:
            p = self.nodes[i].parent
            if p >= 0 and p in pl:
                pl[i] = pl[p] + np.linalg.norm(self.nodes[i].pos - self.nodes[p].pos)
        return pl

    def _subtree_mass(self, radius, children):
        order = self._topo_leaves_first(children)
        m = {}
        for i in order:
            mi = max(radius[i], R0) ** 2
            for c in children[i]:
                mi += m.get(c, 0.0)
            m[i] = mi
        return m

    def _kill_subtree(self, root, children):
        killed = []
        stack = [root]
        while stack:
            i = stack.pop()
            self.nodes[i].alive = False
            # ★ iter-15: bank the heartwood at the size it died at, not at today's size.
            self.nodes[i].death_c = self.c_heart
            killed.append(i)
            for c in children[i]:
                if self.nodes[c].alive:
                    stack.append(c)
        # ★ also KILL every axis contained in the shed subtree — otherwise its Axis object
        # stays alive=True and keeps growing next year, appending live nodes onto dead parents
        # (the "floating crown island" bug). An axis is in the subtree iff its apex was killed.
        kset = set(killed)
        for ax in self.axes:
            if ax.alive and ax.apex is not None and ax.apex in kset:
                ax.alive = False
                ax.apex = None

    # ======================================================================
    # THE YEAR LOOP
    # ======================================================================
    def update_n_def(self):
        """★ iter-15 — N_def(t): the real A4/A5 twigs ONE armature tip stands for, this year.

        The branch carrying capacity of Hellström et al. 2018 (Eq. 1), realized the way that paper
        says it really is realized — "through other factors, such as light or nutrient limitation"
        (Discussion, p. E45) — and NOT as the age lookup alpha*(n+1)^d, which would make DBH an
        analytic function of age. It is a SIZE term, and it is an OUTPUT: what a tip stands for is
        set by what the tree has already built.

        ★ iter-19 — THE NUMERATOR. iter-15 read it off the live crown volume (N_def = TWIG_DENSITY *
        V_crown / n_tips) and that was REFUTED: V_crown is the economy's own product, so income was
        measured from what income had just bought — a positive feedback, gain > 1. iter-18 showed the
        cantilever capacity r^3/lever reduces IDENTICALLY to the subtended mass, and THAT is
        exogenous — last year's wood, which this year's income cannot bid up:

            N_def = MASS_CAP * M_sub_root / n_tips        S = N_def / N_DEF_REF

        M_sub_root is banked by structural_radius at the END of last year, exactly like the light
        field and the support bill. S then scales, in the same year and by the same factor: the light
        a marker intercepts, the shade it casts, the pipe its tip seeds (r_tip), and the heartwood it
        wills to the trunk when it dies (c_heart). Same term, every side.

        ⛔⛔ iter-20 — AND THIS NUMERATOR IS REFUTED TOO, structurally. `N_def * n_tips == MASS_CAP *
        M_sub` identically, so the crown's TOTAL leaf count is proportional to the tree's own mass and
        the n_tips division cancels: a linear positive feedback on mass, loop gain ~= 0.99, a
        bifurcation at MASS_CAP ~= 2.205, and no constant that leaves s, m and l all sane. Exogeneity
        was NECESSARY BUT NOT SUFFICIENT — M_sub is exogenous within the year and still runs away
        across the years. The numerator must be SUB-LINEAR in mass. See the MASS_CAP block up top.

        ★★ iter-36 — THE SUB-LINEAR NUMERATOR, CODED (ADR Position A). The crown's TOTAL twig count
        is now T_total = K_NDEF * M_sub^Q_MASS with Q_MASS = 2/E_M < 1 — an OUTPUT (ratio of the
        area-preserving pipe exponent 2 and the measured mass–radius exponent E_M), not a typed 3/4.
        N_def divides that by n_tips exactly as before; the sub-linearity is what makes the WHOLE-CROWN
        loop gain ≤ q < 1 (iter-19/20's linear form was q=1, a bifurcation). M_sub is still last year's
        banked structure — exogenous. See the K_NDEF/Q_MASS block at the top of the file.

        ⛔⛔ iter-36 — AND THE DIVISOR FORM IS REFUTED TOO: S=K·M^q/n_tips explodes through a SECOND loop
        the mass analysis never bounded — S→shade→n_tips↓→(÷n_tips)→S↑ (a fold, n_tips→1 absorbing state).

        ★★ iter-38 — POSITION B (ADOPTED). Drive S DIRECTLY off standing mass, dropping the /n_tips
        divisor entirely: S = C_NDEF·M_sub^Q_MASS. N_def = S·N_DEF_REF is now PRIMARY; T_total = N_def·
        n_tips floats. This sets the fold's return-arm gain d log S/d log n_tips to 0 — the shade S casts
        no longer bids S up — leaving only the ≤q<1 mass loop iter-36 confirmed tame. C_NDEF is pinned by
        the closed-loop demand S(m@anchor)=1 (tmp/iter38_solve_C.py). See the C_NDEF block up top."""
        if C_NDEF is None or self._m_sub <= 0.0:
            return                                    # anchor probe / seedling years: S stays 1
        # Position B: no n_tips divisor. S is set by standing mass alone; the fold's return arm is cut.
        self.s_def   = max(C_NDEF * self._m_sub ** Q_MASS, S_MIN)
        self.n_def   = self.s_def * N_DEF_REF
        self.r_tip   = R0 * DBH_CALIB * self.s_def ** (1.0 / PIPE_POWER)
        self.c_heart = HEART_RATIO * math.pi * self.r_tip ** 2

    def run(self, years, verbose=False):
        self.spill_log = []                 # ★ iter-29: (year, pool, alloc, spend, residue) per year
        for year in range(1, years + 1):
            self._alloc_year = self._spend_year = self._spill_residue = 0.0
            # 0. ★ iter-15: N_def FIRST — what one tip stands for is set by last year's crown, and
            #    everything this year (income, shade, pipe, heartwood) is priced against it.
            self.update_n_def()
            # 0. ★ iter-6: RESOURCE. Allocate the light the tree caught LAST year (photosynthate is
            #    banked before it is spent) among this year's apices. Finite and shared, so the crown
            #    self-limits: no cap on reach exists or is wanted. See ADR + the constants block.
            self.allocate_resource(self._shadow, self._mn, year)
            # 1. GROWTH — every alive axis with an active apex grows one module IT CAN AFFORD.
            #    An apex whose share cannot buy a single metamer stays dormant; DORMANT_ABORT years
            #    of that and it aborts (Palubicki's 4th bud fate). Shed still removes whole branches.
            live = [ax for ax in self.axes if ax.alive and ax.apex is not None]
            fork_queue = []
            for ax in live:
                relay_host, _ = self.grow_module(ax, year)
                ax._relay_host = relay_host if relay_host is not None else ax.apex
                if ax._dormant >= DORMANT_ABORT:
                    ax.apex = None                     # bud abort
            live = [ax for ax in live if ax.alive and ax.apex is not None]
            # 2. FOLIAGE — living tips put out this year's transient leaf cohort; old cohorts
            #    abscisse. Foliage is the light-gatherer/shader and the shed rule's source.
            children = self._children(include_dead=True)
            self.grow_foliage(year, children)
            self.age_foliage(year)
            children = self._children(include_dead=True)
            shadow, mn = self.build_shadow(children)
            # 3. EFFECTIVE dominance D_eff = D(clean, age-decayed) · env_release(light) · hcap.
            #    env_release (§7.5): HIGH light LOWERS D (open-grown forks early); LOW light HOLDS
            #    D (woodland leader). GENTLE, evaluated NOW (not compounded into the clean D). The
            #    crown-envelope soft cap (§6) collapses D_eff as an orthotropic apex nears H so
            #    leaders stop (by forking there — spine_top is thus an OUTPUT).
            for ax in live:
                # ★ iter-4: the clean dominance is now the three-phase D_clean (rise then decay),
                # refreshed onto ax.D for diagnostics. Establishment rise is what lets a master hold
                # a single dominant relay for a few modules before it forks (persistent scaffold).
                ax.D = self.D_clean(ax)
                apex_pos = self.nodes[ax.apex].pos
                # ★ iter-5: env_release is now LIGHT-EQUITY, not absolute light (§7.5). iter-4 used
                # absolute apex light, so ANY well-lit leader forked early — which is exactly why the
                # masters were short (1-3 modules): a master poking into the light was penalised for
                # the light that makes it a leader. C&E's fork-inducing case is a CO-EQUAL light field
                # ("milieu très ensoleillé -> fourches"), i.e. the apex NOT dominating its neighbours.
                # So high light lowers D only when the apex is co-equal (dom~1); an emergent apex that
                # dominates its crown plane (dom>1) HOLDS its dominance (acrotonie augmente) and even
                # gets a bounded D bonus, so it establishes a LONG single leader before forking.
                ax._dom = self.apex_dominance(apex_pos, shadow, mn) if ax.cat == 1 else 1.0
                lt = self.light_at(apex_pos, shadow, mn)
                equity = np.clip(ax._dom - 1.0, 0.0, 1.0)          # 0 = co-equal, ->1 = emergent
                env = np.clip(1.0 - ENV_LIGHT_K * (lt / FULL_LIGHT) * (1.0 - equity), ENV_MIN, 1.0)
                hold = 1.0 + DOM_D_BONUS * equity                  # dominant leader establishes longer
                D_eff = ax.D * env * hold
                if ax.cat == 1:                        # orthotropic leaders feel the height cap
                    y = apex_pos[1]
                    hcap = np.clip((self.H * 1.05 - y) / (self.H * H_SOFT_FRAC), 0.05, 1.0)
                    D_eff *= hcap
                ax._D_eff = D_eff
            # 4. FIRING — crown-building TERMINAL_FORK: an orthotropic (A1) leader forks once it is
            #    past establishment AND its EFFECTIVE dominance has decayed below Phi_fork. iter-4:
            #    because D now RISES then decays, a master holds D_eff above Phi_fork through its
            #    establishment window and only forks when it decays (or when hcap collapses it near H)
            #    -> it persists as a real leader instead of re-forking at age 2. The wave decrement is
            #    on the establishment PEAK (terminal_fork), so the scaffold self-terminates.
            #    ⚠ STILL A1-only forking. iter-3's UNIVERSAL forking + wave-graded D reset exploded
            #    geometrically (branching factor ramify × fork, shed can't keep up) — a documented
            #    dead-end; DO NOT re-try. See docs/grower_prototype_iter1.md iter-3/iter-4.
            for ax in live:
                if ax.cat != 1 or ax.forked:
                    continue
                est = AU_MIN_AGE if ax.id == 0 else REITER_MIN_AGE
                # ★ iter-5: an emergent leader whose apex dominates its crown plane HOLDS — it does not
                # fork even if D_eff dipped below Phi. Its acrotony is strong (a single dominant relay),
                # so it keeps extending a long single leader "comparable au tronc". It forks only when it
                # is overtopped/level (dom drops) or the height cap collapses D_eff near H (rounding over).
                # NB the seed trunk's establishment fork (age>=AU_MIN_AGE) is NOT held-suppressed — an
                # open-grown young plane DOES fork its trunk into masters; hold applies to the masters.
                held = (ax.id != 0) and (ax._dom >= DOM_HOLD) and (self.nodes[ax.apex].pos[1] < CEIL_FRAC * self.H)
                if ax.age >= est and ax._D_eff < PHI_FORK and not held:
                    ax.D_at_fork = ax._D_eff        # diagnostic only (wave decrement is on the peak)
                    M = self.fork_multiplicity(ax, shadow, mn)
                    self.terminal_fork(ax, ax._relay_host, year, M=M)
            # 5. LATENT_BUD — sparse re-erection on old wood (ages the tree); + the ARCH CASCADE
            #    (§7.2): summit re-erection on arched limbs, distal continuation registered for dieback.
            self.latent_bud(year, shadow, mn)
            self.arch_cascade(year)
            # 6. RATCHET radius (monotone), then the SELF-SUPPORT radius on top of it (★ iter-8:
            #    r = max(pipe, cantilever) — the wood the tree must actually build), then POSTURE
            #    (needs radius), then SHED (foliage light). The support BILL for the girth added
            #    this year is banked, and next year's allocation pays it before it grows anything.
            children = self._children(include_dead=True)
            radius = [0.0] * len(self.nodes)
            radius = self.ratchet(radius, children)
            r_struct, seglen = self.structural_radius(children, radius)
            self._bill = self.support_bill(children, r_struct, radius, seglen)
            radius = list(r_struct)
            self._radius_hist.append(list(radius))    # ★ iter-42: snapshot the built girth (ring-age)
            self.posture(radius, children)
            shadow, mn = self.build_shadow(children)
            nshed = self.shed(self.foliage_light(shadow, mn), children, year)
            self._shadow, self._mn = shadow, mn     # ★ iter-6: bank it — next year's growth spends it
            self.spill_log.append((year, float(getattr(self, "_v_base", 0.0)), self._alloc_year,
                                   self._spend_year, self._spill_residue, nshed))
            if verbose:
                nlive = sum(1 for ax in self.axes if ax.alive)
                nfol = sum(1 for nd in self.nodes if nd.alive and nd.foliage)
                nwood = sum(1 for nd in self.nodes if nd.alive and not nd.foliage)
                vb = getattr(self, "_v_base", 0.0)
                bt = getattr(self, "_bill_total", 0.0)
                al, sp, rs = self._alloc_year, self._spend_year, self._spill_residue
                print(f"yr {year:2d}: wood={nwood:5d} foliage={nfol:5d} axes={nlive:4d} "
                      f"shed={nshed:3d} reiter={self.reit_count:3d} "
                      f"pool={vb:8.4f} m3  support_bill={bt:8.4f} m3 ({100*bt/max(vb,1e-12):5.1f}% of pool)"
                      f"  spend/alloc={100*sp/max(al,1e-12):5.1f}%  residue={100*rs/max(vb,1e-12):5.1f}% of pool")
        return self.finalize()

    # ======================================================================
    # ★ iter-42 — RING-AGE lookup: the built girth of node i, `age` years before the final grown year.
    # ======================================================================
    def _radius_at_age(self, i, age):
        """Node i's structural radius `age` years before the end -- the sapwood/heartwood boundary
        (everything inside this radius was laid down > TAU_HEARTWOOD yr ago => aged heartwood). Returns
        0.0 if the tree (or node i) is younger than `age`: a young stem is all sapwood, no aged core."""
        h = self._radius_hist
        idx = len(h) - 1 - int(age)
        if idx < 0:                          # tree younger than `age` -> no wood is that old
            return 0.0
        snap = h[idx]
        return snap[i] if i < len(snap) else 0.0   # node i not yet born `age` yr ago -> no aged core

    # ======================================================================
    # FINALIZE -> skinner-shaped graph dict (pos/parent/radius/strand/root)
    # ======================================================================
    def finalize(self):
        children = self._children(include_dead=True)
        radius = [0.0] * len(self.nodes)
        radius = self.ratchet(radius, children)
        # ★ iter-5, residual (v): DBH is EMERGENT (§5.3, F2 ratified). The per-tier rescale
        # (root -> DBH_target/2) is DELETED — that IMPOSED the census median on every tier. ONE global
        # scalar DBH_CALIB (the deferred A4/A5 foliage layer each leafless tip stands in for) is fitted
        # ONCE so the modal m tier lands on the census median (15 in); s/l DBH are then OUTPUTS
        # (~p27/p90). ★ iter-8: it is no longer a post-hoc multiply here — it rides on R_TIP inside the
        # ratchet, which is exactly equivalent (the pipe model is homogeneous in the tip radius) but
        # leaves a radius the mechanical term can be compared against. The final girth is the larger
        # of the pipe and self-support demands, so the crown's wood is now DERIVED, not calibrated.
        radius = list(self.structural_radius(children, radius)[0])
        # strand ids from the grower's OWN axis ids (not a max-radius guess)
        strand = [self.nodes[i].axis if self.nodes[i].axis >= 0 else 0
                  for i in range(len(self.nodes))]
        alive = [nd.alive for nd in self.nodes]
        foliage = [nd.foliage for nd in self.nodes]
        out = dict(
            nodes=[dict(pos=nd.pos, parent=nd.parent, radius=radius[i], strand=strand[i],
                        alive=nd.alive, axis=nd.axis, birth=nd.birth, foliage=nd.foliage)
                   for i, nd in enumerate(self.nodes)],
            root=0, radius=radius, strand=strand, alive=alive, foliage=foliage,
            H=self.H, DBH_target_m=self.DBH_target_m,
            n_nodes=len(self.nodes), n_axes=len(self.axes), n_reiterates=self.reit_count,
            n_wood_live=sum(1 for nd in self.nodes if nd.alive and not nd.foliage),
            n_foliage_live=sum(1 for nd in self.nodes if nd.alive and nd.foliage),
        )
        # ★ iter-14: the sapwood/heartwood split at the BASE — the metric iter-12/13 were judged on
        # and never actually printed. F_S / F_H are the leaf-unit counts (Eqs 5 & 6); sap_frac is
        # measured against the wood the tree really builds (r[0], pipe OR cantilever), which is what
        # an increment corer would read. Platanus ground truth: ~50% sapwood, and it is noted for
        # WIDE sapwood, so a low number here is a FAIL however good the DBH looks.
        a_sap, a_dead_0 = math.pi * self._r_sap[0] ** 2, self._a_dead[0]
        a_built = math.pi * radius[0] ** 2
        # ★ iter-42 — RING-AGE split (Track B) is now the HEADLINE sap_frac. It RE-PARTITIONS the same
        # built basal area a_built (DBH untouched): heartwood = the aged core inside r0(t-TAU_HEARTWOOD),
        # sapwood = the outer TAU rings. Supersedes the branch-death bank as the sap/heart measure (Aye's
        # no-reuse artifact, iter-41); the old live-pipe / death-bank numbers are kept for continuity.
        a_heart_age = math.pi * self._radius_at_age(0, TAU_HEARTWOOD) ** 2
        a_sap_age   = max(a_built - a_heart_age, 0.0)
        out.update(F_S=self._f_live[0], F_H=self._f_lost[0],
                   a_sap=a_sap_age, a_heart=a_heart_age,
                   sap_frac=a_sap_age / max(a_built, 1e-12), tau_heartwood=float(TAU_HEARTWOOD),
                   # continuity: the pre-iter-42 lenses (live-pipe sapwood, branch-death heartwood).
                   a_sap_pipe=a_sap, a_heart_deathbank=a_dead_0,
                   sap_frac_pipe=a_sap / max(a_sap + a_dead_0, 1e-12),
                   # node-0 built girth per year -> lets the census overlay re-fit TAU without regrowing.
                   r0_series=[snap[0] for snap in self._radius_hist])
        # ★ iter-15: N_def and the crown it is read from. real_tips = N_def*F_S is the tree's TOTAL
        # A4/A5 tip count — the quantity Hellström's b(n) = beta*(n+1)^d predicts, and therefore the
        # independent check on this whole mechanism (it is a validator, never an input).
        # ★ iter-24: THE LIT FOLIATED LENGTH — the quantity the A5 layer makes income scale with,
        # and the one STATE demands be reported WITH the result (its m->l ratio is the loop's q).
        woody_live = [i for i, nd in enumerate(self.nodes)
                      if nd.alive and not nd.foliage and i != 0]
        n_lit = sum(1 for i in woody_live
                    if self.light_at(self.nodes[i].pos, self._shadow, self._mn) >= SHORT_SHOOT_LIGHT)
        out.update(S=self.s_def, N_def=self.n_def, crown_vol=self._crown_vol, n_tips=self._n_tips,
                   m_sub=self._m_sub, real_tips=self.n_def * self._f_live[0],
                   n_woody_live=len(woody_live), n_lit=n_lit,
                   lit_frac=(n_lit / len(woody_live) if woody_live else 0.0),
                   n_short_shoots=self._n_short_shoots)
        return out


# --- tier config. H = the crown-envelope CEILING (still an imposed soft bound, see CEIL_FRAC).
# DBH_target is now a pure VALIDATION TARGET -- nothing rescales to it (F2: DBH is emergent). ---
# ★ iter-9: both columns re-derived from the CENSUS, not guessed. tree_builder.gd picks a tier from
# `desired_h`, which is a monotone lerp of the census DBH, so the tier buckets invert to DBH cuts
# (s < 10.1 in <= m < 24.3 in <= l). Taking the MEDIAN measured DBH inside each bucket over the 1595
# Central Park planes gives 5 / 17 / 28 in -- the caliber each tier must actually hit.
# (tmp/tier_calibration.py regenerates this from lidar_data/central_park_trees.json.)
TIERS = {"s": (10.0, 5 * 0.0254), "m": (14.4, 17 * 0.0254), "l": (22.0, 28 * 0.0254)}

# ★ iter-9: THE TIER AGES, and they were the whole "crown is 2x too wide" bug.
# Feeding each tier's measured median DBH through the Urban Tree Database's age<->size curve for
# Platanus x acerifolia (McPherson/van Doorn/Peper 2016, PSW-GTR-253, zone NoEast = Queens NY, 376
# measured trees -- the right climate zone for Central Park) gives the tree's REAL age:
#
#     tier   median DBH        real age     UTD H      UTD crown dia
#     s       5 in / 12.7 cm     8 yr        6.9 m       5.2 m
#     m      17 in / 43.2 cm    40 yr       14.2 m      12.6 m
#     l      28 in / 71.1 cm    97 yr       19.1 m      16.9 m
#
# We were growing them for 12 / 20 / 35 yr -- building a 40 yr tree in 20. That forced ALPHA up, and
# a cranked ALPHA is what pumped the crown to 25 m. At the TRUE ages with the SHIPPED parameters the
# crown measures 1.07x (m) and 1.05x (l) of the real one: the width defect never existed. Five
# mechanistic "width bounds" were chasing an artifact of this table. Do not add a sixth.
# ⚠ l's 97 yr is EXTRAPOLATED past the UTD fit's 61.8 cm ceiling (its park subset has no tree over
# ~50 yr), by carrying the curve's age-60 growth rate forward. It is corroborated by the obvious:
# Central Park's big planes were planted in the early 20th century, so they ARE ~90-120 yr old.
#
# ★ iter-10: THOSE AGES ARE UTD's, AND UTD's CLOCK STARTS AT PLANTING, NOT AT THE SEED.
# McPherson & Peper measure age as YEARS SINCE PLANTING. Their age-0 tree is not a germinating
# seed -- it is a nursery whip, and the curve says so in two places at once: utd_dbh_cm(0) = 2.40 cm
# and utd_height_m(2.40) = 4.01 m, which is also exactly the stated floor of their height fit's
# applicability range. A 4 m, 1-inch-caliper B&B whip is precisely what a street/park planting is.
# We grow from a SEED, so our clock must be offset by the nursery years:
#
#     age_from_seed = UTD_age + NURSERY_YEARS
#
# NURSERY_YEARS is DERIVED, not chosen: it is the grower's own age when it reaches the whip. Mean H
# crosses 4.01 m at 6.72 yr, identically in all three tiers (max-min = 0.00 yr -- the tiers are
# bit-identical through the juvenile phase, since the CEIL_FRAC*H cap cannot engage on a 6-year-old).
# Measured over 8 seeds by tmp/nursery_offset_probe.py; full tables in tmp/iter10_nursery_offset.md.
#
# ⚠ THE ALIGNMENT IS ON HEIGHT ALONE, AND IT HAS TO BE. At 6.72 yr our trunk is 21.4 cm DBH against
# the whip's 2.40 cm (8.9x). That is not a fit error: a constant R_TIP floors DBH at 2*R_TIP =
# 10.3 cm for ANY tree at ANY age (see the R_TIP defect note above), which is already 4.3x the whip.
# There is no age at which this grower IS a nursery whip, so caliber cannot align the clock -- and
# no clock correction can fix caliber. The two defects look independent and are not.
NURSERY_YEARS = 7          # [DERIVED] 6.72, rounded. See above.
TIER_AGES = {tier: utd_age + NURSERY_YEARS
             for tier, utd_age in {"s": 8, "m": 40, "l": 97}.items()}   # -> 15 / 47 / 104


def grow_tier(tier, years=None, verbose=False, seed=SEED):
    H, DBH = TIERS[tier]
    if years is None:
        years = TIER_AGES[tier]
    g = Grower(H, DBH, seed=seed)
    return g.run(years, verbose=verbose)


if __name__ == "__main__":
    import sys
    tier = sys.argv[1] if len(sys.argv) > 1 else "m"
    g = grow_tier(tier, verbose=True)
    r = np.array(g["radius"])
    print(f"\n[{tier}] wood_live={g['n_wood_live']} foliage_live={g['n_foliage_live']} "
          f"axes={g['n_axes']} reiterates={g['n_reiterates']}")
    print(f"    trunk_r={r[0]*1000:.0f}mm  DBH={r[0]*2/0.0254:.1f}in  "
          f"r=[{r[r>0].min()*1000:.1f}..{r.max()*1000:.0f}]mm")
    print(f"    DBH vs census: {r[0]*2/TIERS[tier][1]:.2f}x   "
          f"leaf units: F_S={g['F_S']:.0f} live / F_H={g['F_H']:.0f} lost")
    print(f"    ★ RING-AGE (tau={g['tau_heartwood']:.0f} yr): SAPWOOD={100*g['sap_frac']:.1f}% of built "
          f"basal area   [target ~50% on the mature l-tier]   "
          f"(old lens: pipe/death-bank {100*g['sap_frac_pipe']:.1f}%)")
    # ★ iter-42 tau DERIVATION readout: the year the trunk reached sqrt(0.5) of its final girth is the
    # tau that lands THIS tree at exactly 50% basal-area sapwood. Fit it on the l-tier; anchor ~60 yr.
    s0 = g["r0_series"]
    if s0 and s0[-1] > 0:
        target = math.sqrt(0.5) * s0[-1]
        yr = next((k for k, rk in enumerate(s0) if rk >= target), None)
        if yr is not None:
            print(f"    tau-fit: trunk hits {100*math.sqrt(0.5):.1f}% of final girth at year {yr} of "
                  f"{len(s0)}  =>  tau_50% = {len(s0) - 1 - yr} yr  (r0: {s0[0]*1000:.1f}..{s0[-1]*1000:.0f}mm)")
