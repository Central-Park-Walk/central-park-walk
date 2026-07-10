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

# --- module / growth-unit lengths, in NODES (metamers). C&E measured for A2..A5. ---
GU_NODES = {1: 14,        # A1 trunk. [GAP-A1GU] — C&E's cell is BLANK; do NOT interpolate
            2: 15,        # A2  measured C&E
            3: 10,        # A3  measured C&E
            4: 7,         # A4  measured C&E
            5: 5}         # A5  measured C&E (short shoot)
INTERNODE = 0.11          # metamer length, m. [PROV] — no plane number; set so the m-tier
                          # trunk reaches ~14 m over the establishment window.

# ★ F6 SCOPE: grow the WOODY ARMATURE only (A1 trunk, A2 primaries, A3 secondaries). The
# A4/A5 short-shoot + twig layer is the space-filling FOLIAGE layer (design §7.1, §9.2) and
# is deferred — this prototype is LEAFLESS, so its terminal A3 tips ARE the foliage proxy.
MAX_CAT = 3               # deepest apparent order grown as skeleton (A3). A4/A5 = foliage layer.
# BRANCH_GRADE: how many axillary buds of a module's spiral zone RELEASE as growing branches
# this year (the rest stay dormant — proleptic; available to LATENT_BUD later). [PROV/GAP-grade]
BRANCH_GRADE = {1: 2, 2: 1, 3: 0}

SPIRAL_FRAC = 0.60        # distal fraction of a module that bears laterals (acrotony). [PROV]
DIVERG_SPIRAL = 137.5     # 2/5 spiral phyllotaxis divergence for orthotropic A1 (~144); use
                          # golden as the continuous stand-in [PROV-ish; C&E says spiral 2/5]

# --- angles ---
THETA_RELAY_DEG = 4.0     # kink of the relay ("prolongement", near-straight). [PROV/GAP-θrelay]
THETA_LATERAL_DEG = 55.0  # insertion angle of subjacent laterals ("ouvert"). [PROV]
THETA_GSA_DEG = 60.0      # plagiotropic gravitropic set-point from vertical, A2-A5. [PROV/GAP-θGSA]

# --- relay dominance D / firing (§2). ---
AU_MIN_AGE   = 6          # SEED trunk establishment: no crown-fork before the AU is attained.
                          # C&E: "AU attained in first 6 years." (structural, from source)
REITER_MIN_AGE = 2        # a REITERATE leader is born mature (low D); it builds acrotony over
                          # a couple modules, then forks — it is NOT a seedling. [PROV]
H_SOFT_FRAC  = 0.42       # crown-envelope soft cap (§6): a leader's D collapses as its apex
                          # nears H, so vertical extension stops near the target height. [PROV]
D0_SEED      = 1.0        # seed trunk starts fully dominant
D_DECAY_AGE  = 0.13       # per-module dominance decay (acrotony wanes). [PROV/GAP-γ]
PHI_FORK     = 0.34       # D threshold below which the axis forks. [PROV/GAP-Φfork]
D_RESET      = 0.55       # newborn wave inherits D_RESET * D_at_fork -> lower each wave. [PROV/GAP-D0]
D_STOP       = 0.12       # below this a fork's elements are terminal (peripheral pauperized
                          # secondaries, NOT new orthotropic leaders) -> recursion ends on its
                          # own, D->0 at the periphery (C&E). [PROV]
MAX_ORDER_GUARD = 7       # loop guard only; NOT a botanical cap (max_order is an output)

# --- posture (§7.2): dtheta = righting_toward_GSA - sag_from_self_weight ---
SAG_K        = 0.055      # sag gain per (subtree mass * lever). [PROV/GAP-strain]
RIGHT_K      = 0.16       # reaction-wood righting gain (∝ 1/r). [PROV/GAP-strain]

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
    __slots__ = ("id", "cat", "order", "reit", "D", "alive", "apex", "nodes",
                 "birth", "dirv", "gsa", "age", "forked", "D_at_fork", "_relay_host")
    def __init__(self, aid, cat, order, reit, D, apex, dirv, birth):
        self.id = aid
        self.cat = cat                # apparent order rung 1..5 (A1..A5)
        self.order = order            # topological/apparent branching order for shading only
        self.reit = reit              # owning Reiterate id
        self.D = D                    # relay dominance
        self.alive = True
        self.apex = apex              # node index of the active apex (or None once ended)
        self.nodes = [apex]           # node indices in growth order
        self.birth = birth
        self.dirv = np.asarray(dirv, float)
        self.gsa = None               # set-point direction target (plagiotropic axes)
        self.age = 0                  # modules grown
        self.forked = False


class Grower:
    def __init__(self, H, DBH_target_m, seed=SEED):
        self.H = H
        self.DBH_target_m = DBH_target_m
        self.rng = np.random.default_rng(seed)
        self.nodes = []
        self.axes = []
        self.reit_count = 0
        # seed: ground node + trunk apex one internode up
        self.nodes.append(Node([0, 0, 0], -1, -1, 0))     # ground/root, node 0
        up = np.array([0.0, 1.0, 0.0])
        self.nodes.append(Node([0, INTERNODE, 0], 0, 0, 0))  # first trunk metamer, node 1
        trunk = Axis(0, cat=1, order=0, reit=0, D=D0_SEED, apex=1, dirv=up, birth=0)
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
        n = GU_NODES[ax.cat]
        # lay down n metamers along the current (posture-updated) direction
        d = ax.dirv.copy()
        laterals_hosts = []       # (node_id, position_in_module) for the distal spiral zone
        spiral_start = int(math.floor(n * (1.0 - SPIRAL_FRAC)))
        base_az = self.rng.uniform(0, 360)
        for i in range(n):
            p_prev = self.nodes[ax.apex].pos
            newp = p_prev + INTERNODE * d
            nid = self._new_node(newp, ax.apex, ax.id, year)
            ax.apex = nid
            ax.nodes.append(nid)
            if i >= spiral_start:
                laterals_hosts.append((nid, i))
        # --- acrotony: emit laterals at the distal spiral zone (§4) ---
        # most-distal host is reserved for the relay; a small branching-grade of the
        # sub-jacent buds RELEASE this year (most distal first = acrotony), the rest stay
        # dormant. A5/A4 twig layer is not grown here (F6 skeleton scope, MAX_CAT).
        relay_host = laterals_hosts[-1][0] if laterals_hosts else ax.apex
        child_axes = []
        child_cat = ax.cat + 1
        grade = BRANCH_GRADE.get(ax.cat, 0)
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
        # dominance decays with age (acrotony wanes); light modulation applied in step()
        ax.D *= (1.0 - D_DECAY_AGE)
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
    # FIRING (§2) — a fork IS a reiteration
    # ======================================================================
    def terminal_fork(self, ax, relay_host, year):
        """D fell below Phi_fork at this axis's tip: replace the single relay with 2-3
        co-equal reiterates (start_order = the forking axis's OWN rung). The axis ENDS."""
        # how many co-equal masters (2 or 3) — light-equity among near-apex buds; here [PROV] 2/3
        M = 3 if self.rng.random() < 0.45 else 2      # [PROV] until light-equity wired
        d = ax.dirv
        Dfork = getattr(ax, "D_at_fork", ax.D)
        Dchild = D_RESET * Dfork
        # ★ recursion terminates at the periphery: once inherited dominance is spent, the fork
        # elements are pauperized terminal SECONDARIES (plagiotropic, sheddable), not new
        # orthotropic leaders. This is C&E's "D -> nul" — max_order is an OUTPUT, not a cap.
        terminal = Dchild < D_STOP
        child_cat = MAX_CAT if terminal else ax.cat
        new_axes = []
        for j in range(M):
            az = (j * 360.0 / M) + self.rng.uniform(-15, 15)
            fd = self._azimuth_dir(d, 22.0, az)       # [PROV] fork half-angle
            p = self.nodes[relay_host].pos + INTERNODE * fd
            nid = self._new_node(p, relay_host, len(self.axes), year)
            self.reit_count += 1
            child = Axis(len(self.axes), cat=child_cat, order=ax.order + (1 if terminal else 0),
                         reit=self.reit_count, D=Dchild, apex=nid, dirv=fd, birth=year)
            child.gsa = None if child_cat == 1 else self._gsa_target(fd)
            self.nodes[nid].axis = child.id
            self.axes.append(child)
            new_axes.append(child)
        ax.alive = False
        ax.apex = None
        ax.forked = True
        return new_axes

    def latent_bud(self, year):
        """Mode 2: dormant buds on OLD wood re-erect. start_order = s(u_ins) positional law
        (§3.3): complete reiteration low on the trunk, pauperized toward the periphery. This
        is what makes the lower limbs heavier (they start at a lower rung => bigger subtree)
        and older (fire earlier => more ratchet). Fires sparsely, light-gated (F1)."""
        # path length (root->node) for every node, for u_ins
        pl = self._pathlen()
        maxpl = max(pl.values()) if pl else 1.0
        births = []
        MAX_PER_YEAR = 8                              # [PROV] bounded release
        # candidate hosts: old-wood nodes (age>=4 yr) on orthotropic axes (trunk + masters)
        for ax in list(self.axes):
            if not ax.alive or ax.cat > 1:            # trunk + orthotropic master leaders only
                continue
            for nid in ax.nodes:
                if len(births) >= MAX_PER_YEAR:
                    break
                nd = self.nodes[nid]
                if year - nd.birth < 4:               # must be old wood
                    continue
                if self.rng.random() > 0.0018:        # [PROV] sparse release rate
                    continue
                u = pl.get(nid, 0.0) / max(maxpl, 1e-6)
                s = self._start_order(u)              # positional pauperization
                # re-erect: orthotropic new leader
                az = self.rng.uniform(0, 360)
                fd = self._azimuth_dir(np.array([0.0, 1.0, 0.0]), 12.0, az)
                p = nd.pos + INTERNODE * fd
                cid = self._new_node(p, nid, len(self.axes), year)
                self.reit_count += 1
                child = Axis(len(self.axes), cat=s, order=ax.order + 1, reit=self.reit_count,
                             D=D_RESET, apex=cid, dirv=fd, birth=year)
                child.gsa = None if s == 1 else self._gsa_target(self._perp(np.array([0, 1.0, 0])))
                self.nodes[cid].axis = child.id
                self.axes.append(child)
                births.append(child)
        return births

    def _start_order(self, u):
        """s(u_ins): 1 (total, c.r.t.) at the base -> 5 (M.A.U.) at the periphery. §3.3."""
        # linear map, rounded, clamped [1,5]; complete low, pauperized high.
        return int(np.clip(round(1 + u * 4.0), 1, 5))

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
                r_live = R0
            else:
                r_live = (sum(radius[c] ** PIPE_POWER for c in wc)) ** (1.0 / PIPE_POWER)
            radius[i] = max(radius[i], r_live)        # THE RATCHET — never decreases
        return radius

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
    # SHED (§7.3) — light_gathered/size < tau  => remove subtree, keep radius
    # ======================================================================
    def shed(self, light, children):
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
            root = ax.nodes[0]
            if not self.nodes[root].alive:
                continue
            ratio = lg.get(root, 0.0) / max(sz.get(root, 1), 1)
            if ratio < TAU_SHED:
                shed_roots.append((root, ax))
        for root, ax in shed_roots:
            self._kill_subtree(root, children)
            ax.alive = False
        return len(shed_roots)

    # ======================================================================
    # POSTURE (§7.2) — plagiotropic axes sag then right; A1 stays orthotropic
    # ======================================================================
    def posture(self, radius, children):
        subtree_mass = self._subtree_mass(radius, children)
        for ax in self.axes:
            if not ax.alive or ax.cat == 1 or ax.gsa is None:
                continue
            # current growth direction bends: righting toward GSA (∝1/r) minus sag (∝ mass*lever)
            tip = ax.apex
            if tip is None:
                continue
            r = max(radius[tip], R0)
            mass = subtree_mass.get(ax.nodes[0], 1.0)
            lever = np.linalg.norm(self.nodes[ax.apex].pos - self.nodes[ax.nodes[0]].pos)
            sag = SAG_K * mass * lever
            right = RIGHT_K / r
            frac_to_gsa = np.clip(right / (right + sag + 1e-6), 0.0, 0.9)
            d = self._rot_toward(ax.dirv, ax.gsa, frac_to_gsa)
            # then apply downward sag directly
            d = d + np.array([0.0, -sag, 0.0]) * 0.1
            d = d / (np.linalg.norm(d) + 1e-12)
            ax.dirv = d

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
            # 1. GROWTH — every alive axis with an active apex grows one module
            live = [ax for ax in self.axes if ax.alive and ax.apex is not None]
            fork_queue = []
            for ax in live:
                relay_host, _ = self.grow_module(ax, year)
                ax._relay_host = relay_host
            # 2. FOLIAGE — living tips put out this year's transient leaf cohort; old cohorts
            #    abscisse. Foliage is the light-gatherer/shader and the shed rule's source.
            children = self._children(include_dead=True)
            self.grow_foliage(year, children)
            self.age_foliage(year)
            children = self._children(include_dead=True)
            shadow, mn = self.build_shadow(children)
            # 3. LIGHT modulates D (F1 env_release): shaded apices lose dominance faster; AND the
            #    crown-envelope soft cap (§6) collapses D as the apex nears H so leaders stop.
            for ax in live:
                lt = self.light_at(self.nodes[ax.apex].pos, shadow, mn)
                ax.D *= np.clip(lt / FULL_LIGHT, 0.15, 1.0)
                if ax.cat == 1:                        # orthotropic leaders feel the height cap
                    y = self.nodes[ax.apex].pos[1]
                    hcap = np.clip((self.H * 1.05 - y) / (self.H * H_SOFT_FRAC), 0.05, 1.0)
                    ax.D *= hcap
            # 4. FIRING — crown-building TERMINAL_FORK: orthotropic (A1) leaders only, where D
            #    collapsed past establishment. A reiterate leader establishes far faster than
            #    the seed trunk (it is born mature, not a seedling).
            for ax in live:
                if ax.cat != 1 or ax.forked:
                    continue
                est = AU_MIN_AGE if ax.id == 0 else REITER_MIN_AGE
                if ax.age >= est and ax.D < PHI_FORK:
                    ax.D_at_fork = ax.D
                    self.terminal_fork(ax, ax._relay_host, year)
            # 5. LATENT_BUD — sparse re-erection on old wood (ages the tree)
            self.latent_bud(year)
            # 6. RATCHET radius (monotone), then POSTURE (needs radius), then SHED (foliage light).
            children = self._children(include_dead=True)
            radius = [0.0] * len(self.nodes)
            radius = self.ratchet(radius, children)
            self.posture(radius, children)
            shadow, mn = self.build_shadow(children)
            nshed = self.shed(self.foliage_light(shadow, mn), children)
            if verbose:
                nlive = sum(1 for ax in self.axes if ax.alive)
                nfol = sum(1 for nd in self.nodes if nd.alive and nd.foliage)
                nwood = sum(1 for nd in self.nodes if nd.alive and not nd.foliage)
                print(f"yr {year:2d}: wood={nwood:5d} foliage={nfol:5d} axes={nlive:4d} "
                      f"shed={nshed:3d} reiter={self.reit_count:3d}")
        return self.finalize()

    # ======================================================================
    # FINALIZE -> skinner-shaped graph dict (pos/parent/radius/strand/root)
    # ======================================================================
    def finalize(self):
        children = self._children(include_dead=True)
        radius = [0.0] * len(self.nodes)
        radius = self.ratchet(radius, children)
        # fit DBH: scale so root radius == DBH_target/2 (F2: fit ONE scalar, then check shape)
        scale = (self.DBH_target_m * 0.5) / max(radius[0], 1e-6)
        radius = [r * scale for r in radius]
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


# --- m-tier config (envelope tables live in leafback_skeleton; here only H + DBH target). ---
# DBH_target is a FIT SCALAR for iter 1 (F2 recommends emergent+validate; iter 1 imposes the
# median to check the DBH-vs-H SHAPE across tiers, which is the falsifiable part). m = middle.
TIERS = {"s": (10.0, 7 * 0.0254), "m": (14.4, 15 * 0.0254), "l": (22.0, 28 * 0.0254)}


def grow_tier(tier, years=None, verbose=False, seed=SEED):
    H, DBH = TIERS[tier]
    if years is None:
        # developmental age scales with tier: young/middle/mature. [PROV]
        years = {"s": 12, "m": 20, "l": 35}[tier]
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
