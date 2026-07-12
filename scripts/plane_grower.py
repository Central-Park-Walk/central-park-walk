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
from scipy.spatial import cKDTree

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
DBH_CALIB  = 12.85        # [FIT] 4.37 * 2.94; see docs/grower_prototype_iter1.md iter-9.
# ★ iter-8: DBH_CALIB is applied AT THE TIP, not as a post-hoc multiply in finalize(). The two are
# EXACTLY equivalent -- the pipe model r=(SUM r_c^p)^(1/p) is homogeneous of degree 1 in the tip
# radius, so seeding every tip at k*R0 scales every radius by k -- but the tip form says what the
# constant physically IS: one armature tip stands in for DBH_CALIB^PIPE_POWER real A4/A5 tips.
# This matters now, because the mechanical radius (below) has to be compared against the pipe radius
# the tree ACTUALLY BUILDS. Against the post-hoc-multiplied one that comparison cannot even be
# written down; against the raw one it is wrong by DBH_CALIB. See docs/grower_prototype_iter1.md.
# ⚠ THE ONE OPEN DEFECT (iter-9, sharpened by iter-10): R_TIP is a CONSTANT, but the deferred A4/A5
# system it stands in for is NOT. At the calibrated DBH_CALIB, one armature tip is priced as
# DBH_CALIB^PIPE_POWER = 12.85^2.3 = ~354 real twigs. That is a MATURE-CROWN number applied to every
# tip of every tree at every age: it says an 8-yr sapling's ~6 armature tips stand in for ~2200 real
# twigs. It is one scalar with two consequences, because R_TIP both seeds the pipe model AND prices
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
# ⚠ The leading candidate (N_def ACCUMULATES with a tip's own age: a limb that stopped elongating
#    decades ago has built up a short-shoot spray, a shoot laid down this year has none) rests on an
#    UNSOURCED botanical claim about Platanus short-shoot accumulation. Five mechanisms have already
#    been built and refuted on unsourced intuition on this thread. SOURCE IT BEFORE CODING IT.
R_TIP      = DBH_CALIB * R0     # effective terminal-bud radius (= the deferred tips' worth)

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
ALPHA      = 2.59e-4 # [FIT] m^3 of wood per unit of light gathered per year. v_base = ALPHA*Q_base.
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
    __slots__ = ("pos", "parent", "axis", "birth", "alive", "foliage")
    def __init__(self, pos, parent, axis, birth, foliage=False):
        self.pos = np.asarray(pos, float)
        self.parent = parent          # node index, or -1
        self.axis = axis              # owning Axis id
        self.birth = birth            # year laid down (leaf cohort year, if foliage)
        self.alive = True
        self.foliage = foliage        # True = transient A4 leaf marker (light-gatherer, not wood)


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
        self._bill = {}
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
        l_afford = ax._v / (n * math.pi * R_TIP ** 2)
        ext = min(1.0, l_afford / INTERNODE) * vigour
        if ext < EXT_MIN:
            ax._dormant += 1                    # cannot extend at all this year (a dormant bud)
            return None, []
        ax._dormant = 0
        step = INTERNODE * ext
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
        order = self._topo_leaves_first(children)
        for i in order:
            if self.nodes[i].foliage:                 # leaves are not wood — no radius
                continue
            # only WOODY live children carry pipe area (foliage excluded)
            wc = [c for c in children[i] if self.nodes[c].alive and not self.nodes[c].foliage]
            if not wc:
                r_live = R_TIP                        # ★ iter-8: the tip seed carries DBH_CALIB
            else:
                r_live = (sum(radius[c] ** PIPE_POWER for c in wc)) ** (1.0 / PIPE_POWER)
            radius[i] = max(radius[i], r_live)        # THE RATCHET — never decreases
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
        prev = np.full(N, R_TIP)
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
        cohort of FOLIAGE_PER_TIP transient A4 leaves. These are the light-gatherers/shaders;
        they are not wood. Only tips foliate, so a limb that stops extending stops re-leafing."""
        tips = [i for i, nd in enumerate(self.nodes)
                if nd.alive and not nd.foliage and i != 0
                and not any(self.nodes[c].alive and not self.nodes[c].foliage for c in children[i])]
        for t in tips:
            base = self.nodes[t].pos
            for k in range(FOLIAGE_PER_TIP):
                off = self.rng.normal(0, 1, 3); off /= (np.linalg.norm(off) + 1e-9)
                p = base + FOLIAGE_SPREAD * off
                self.nodes.append(Node(p, t, self.nodes[t].axis, year, foliage=True))

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
        shadow = {}
        for (gx, gy, gz) in gi:
            for dl in range(0, SHADOW_LEVELS):
                s = SHADOW_A * SHADOW_B ** (-dl)
                if s < 0.02:
                    break
                for dx in range(-dl, dl + 1):
                    for dz in range(-dl, dl + 1):
                        key = (gx + dx, gy - dl, gz + dz)
                        shadow[key] = shadow.get(key, 0.0) + s * math.exp(-(dx*dx+dz*dz)/(2*(dl+1)))
        return shadow, mn

    def light_at(self, pos, shadow, mn):
        g = tuple(np.floor((pos - mn) / VOX).astype(int))
        return max(FULL_LIGHT - shadow.get(g, 0.0) + SHADOW_A, 0.0)

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
                q_own[nd.axis] += self.light_at(nd.pos, shadow, mn)
        order = []                                   # children-before-parents
        stack = list(roots)
        while stack:
            a = stack.pop()
            order.append(a)
            stack.extend(kids[a])
        q_sub, n_sub = {}, {}
        for a in reversed(order):
            ax = self.axes[a]
            live_apex = 1 if (ax.alive and ax.apex is not None) else 0
            q_sub[a] = q_own[a] + sum(q_sub[c] for c in kids[a])
            n_sub[a] = live_apex + sum(n_sub[c] for c in kids[a])
        # BOOTSTRAP: before any foliage exists (year 1) the tree has caught no light. A seedling
        # grows on its stored reserves — give every apex enough to buy one full module.
        if not roots or sum(q_sub[r] for r in roots) <= 0.0:
            for ax in self.axes:
                if ax.alive and ax.apex is not None:
                    ax._v = GU_NODES[ax.cat] * math.pi * R_TIP ** 2 * INTERNODE
            return
        # --- acropetal pass: distribute v down the axis tree ---
        apical = year <= APICAL_OFF_YEAR
        self._v_base = ALPHA * sum(q_sub[r] for r in roots)   # diagnostic: the whole year's pool
        for r in roots:
            self._distribute(r, ALPHA * q_sub[r], kids, q_own, q_sub, n_sub, apical)

    def _distribute(self, a, v, kids, q_own, q_sub, n_sub, apical):
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
        for (key, q, kind, cid), w in zip(cands, wq):
            vi = v * w / tot
            if kind == "apex":
                self.axes[cid]._v = vi
            else:
                self._distribute(cid, vi, kids, q_own, q_sub, n_sub, apical)

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
    def run(self, years, verbose=False):
        for year in range(1, years + 1):
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
            self.posture(radius, children)
            shadow, mn = self.build_shadow(children)
            nshed = self.shed(self.foliage_light(shadow, mn), children, year)
            self._shadow, self._mn = shadow, mn     # ★ iter-6: bank it — next year's growth spends it
            if verbose:
                nlive = sum(1 for ax in self.axes if ax.alive)
                nfol = sum(1 for nd in self.nodes if nd.alive and nd.foliage)
                nwood = sum(1 for nd in self.nodes if nd.alive and not nd.foliage)
                vb = getattr(self, "_v_base", 0.0)
                bt = getattr(self, "_bill_total", 0.0)
                print(f"yr {year:2d}: wood={nwood:5d} foliage={nfol:5d} axes={nlive:4d} "
                      f"shed={nshed:3d} reiter={self.reit_count:3d} "
                      f"pool={vb:8.4f} m3  support_bill={bt:8.4f} m3 ({100*bt/max(vb,1e-12):5.1f}% of pool)")
        return self.finalize()

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
