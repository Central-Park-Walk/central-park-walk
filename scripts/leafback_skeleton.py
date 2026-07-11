#!/usr/bin/env python3
"""Leaf-back TRUNK-SPINE + SCAFFOLD skeleton (line C) — PROMOTED (2026-07-08).

Promoted from `tmp/leafback_trunkscaffold.py` (Chris-approved 2026-07-08, AC-8 wiring) so
the production london_plane build has a committed, reproducible source for the leaf-back
crown skeleton. Logic is verbatim from the validated prototype
(`docs/leafback_trunkscaffold_prototype.md`, iteration-2 growth partition, spec v4 AC-14);
only the module header, the import path (scripts/, not tmp/), and the bucket-config +
driver block at the bottom are new.

Pipeline role: this runs in SYSTEM PYTHON (needs scipy — which HANGS inside Blender's
bundled Python, the documented gotcha). `scripts/build_leafback_skeletons.py` calls
`build_bucket_skeleton()` per tier and saves a `.npz`; the Blender generator
(`generate_trees_mtree.py`) then LOADS that `.npz` and skins it with
`scripts/leafback_skinner.py`. So skeleton-gen (scipy, offline) and skinning (bpy) are
deliberately separate stages.

A persistent tapering central trunk runs from ground to ~0.74 H; N scaffold origins
(N = crown-bucket primary count) break off along it at distributed heights + golden-angle
azimuths (>= theta_min apart); each scaffold runs line-B space colonization over its own
nearest-anchor (growth-capacity) subset of the sprig shell cloud, with a distance-from-
trunk scaled kill/influence radius and a guaranteed clear proximal length before forking.
"""
import math
import os
import sys
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leafback_graph as lbg

PIPE_POWER = 2.3   # identical to leafback_graph.py
R0 = 0.004         # 4 mm tip seed — identical
THETA_MIN = 35.0   # sibling/scaffold angular spacing — from leafback_graph_v2.py


# ---- pipe-model taper + strand decomposition (copied VERBATIM in logic from leafback_graph) ----
def _topo_leaves_first(nodes, children):
    order = []; seen = [False]*len(nodes)
    roots = [i for i, nd in enumerate(nodes) if nd["parent"] == -1]
    stack = [(r, False) for r in roots]
    while stack:
        nid, processed = stack.pop()
        if processed:
            order.append(nid); continue
        if seen[nid]: continue
        seen[nid] = True
        stack.append((nid, True))
        for c in children[nid]: stack.append((c, False))
    return order


def _finish(nodes, root_id, fork_id, DBH_m, H, CB, n_sprigs, leftover, extra=None):
    children = {i: [] for i in range(len(nodes))}
    for i, nd in enumerate(nodes):
        if nd["parent"] >= 0:
            children[nd["parent"]].append(i)
    radius = [0.0]*len(nodes)
    order = _topo_leaves_first(nodes, children)
    for i in order:
        if not children[i]:
            radius[i] = R0
        else:
            radius[i] = (sum(radius[c]**PIPE_POWER for c in children[i]))**(1.0/PIPE_POWER)
    scale = (DBH_m*0.5) / max(radius[root_id], 1e-6)
    radius = [r*scale for r in radius]
    for i, nd in enumerate(nodes):
        nd["radius"] = radius[i]
    strand = [-1]*len(nodes); next_sid = [0]
    def assign(nid, sid):
        strand[nid] = sid
        ch = children[nid]
        if not ch:
            return
        prim = max(ch, key=lambda c: radius[c])
        for c in ch:
            if c == prim:
                assign(c, sid)
            else:
                next_sid[0] += 1; assign(c, next_sid[0])
    assign(root_id, 0)
    out = dict(nodes=nodes, children=children, root=root_id, fork=fork_id,
               strand=strand, n_strands=next_sid[0]+1, n_sprigs=n_sprigs,
               H=H, DBH_m=DBH_m, CB=CB, leftover_attractors=int(leftover))
    if extra:
        out.update(extra)
    return out


def _scaled(u, near, far, p):
    """near value at trunk (u=0) -> far value at shell (u=1), with (1-u)^p easing."""
    f = np.clip(1.0 - u, 0.0, 1.0)**p
    return far + (near - far)*f


def grow_scaffold(nodes, origin_id, seed_dir, attractors, alive_local, RX, params, pathlen):
    """Two-phase growth of one scaffold over its own attractor subset. Appends nodes in place.

    Phase A (structural leader): a directed, UNFORKED limb from the trunk surface toward the
    running centroid of live attractors, crossing the hollow crown core in D-length steps.
    Phase B (canopy ramification): validated line-B space colonization restricted to this
    subset, with a distance-from-trunk scaled kill radius so ramification densifies toward
    the shell. Returns number of attractors left unreached by this scaffold."""
    D = params["D"]; p = params["p"]
    dk_near, dk_far = params["dk_near"], params["dk_far"]
    di_near, di_far = params["di_near"], params["di_far"]
    cos_spawn = math.cos(math.radians(params["theta_spawn"]))
    STALL_LIMIT, max_iter = 8, 800

    def rho_u(pos):
        return min(math.hypot(pos[0], pos[2]) / max(RX, 1e-6), 1.0)

    # seed segment off the trunk surface so the limb emerges cleanly
    op = np.asarray(nodes[origin_id]["pos"], float)
    nodes.append({"pos": op + D*seed_dir, "parent": origin_id})
    tip = len(nodes)-1
    pathlen[tip] = D
    local_ids = [origin_id, tip]
    child_dirs = {origin_id: [seed_dir.copy()]}

    # ---- Phase A: directed structural leader across the core ----
    prev_dir = seed_dir.copy()
    for _ in range(max_iter):
        live = np.where(alive_local)[0]
        if len(live) == 0:
            break
        A = attractors[live]
        tp = np.asarray(nodes[tip]["pos"], float)
        dmin = np.linalg.norm(A - tp, axis=1).min()
        if dmin <= di_far:      # reached the shell -> hand off to ramification
            break
        target = A.mean(0)      # running centroid (curves toward the mass as it recedes)
        dirv = target - tp; n = np.linalg.norm(dirv)
        if n < 1e-9:
            break
        dirv = 0.75*(dirv/n) + 0.25*prev_dir      # light smoothing = no kinks
        dirv /= np.linalg.norm(dirv)
        prev_dir = dirv
        nodes.append({"pos": tp + D*dirv, "parent": tip})
        cid = len(nodes)-1
        pathlen[cid] = pathlen[tip] + D
        child_dirs[tip] = [dirv.copy()]
        tip = cid; local_ids.append(cid)

    # ---- Phase B: space-colonization ramification at the shell ----
    it = 0; stall = 0; prev_alive = int(alive_local.sum())
    while alive_local.any() and it < max_iter:
        it += 1
        node_pos = np.array([nodes[i]["pos"] for i in local_ids])
        tree = cKDTree(node_pos)
        live = np.where(alive_local)[0]
        A = attractors[live]
        dist, nn = tree.query(A, k=1)
        u_nn = np.array([rho_u(node_pos[k]) for k in nn])
        di_nn = _scaled(u_nn, di_near, di_far, p)
        within = dist <= di_nn
        if not within.any():
            break
        grow = {}
        for j in range(len(A)):
            if not within[j]:
                continue
            lid = local_ids[int(nn[j])]
            d = A[j] - nodes[lid]["pos"]; n = np.linalg.norm(d)
            if n < 1e-9:
                continue
            grow.setdefault(lid, np.zeros(3))
            grow[lid] += d/n
        grew = False
        for lid, gvec in grow.items():
            n = np.linalg.norm(gvec)
            if n < 1e-9:
                continue
            dirv = gvec/n
            existing = child_dirs.get(lid)
            if existing is not None and any(np.dot(dirv, e) > cos_spawn for e in existing):
                continue    # near-parallel pull continues frontier (witch's-broom guard)
            nodes.append({"pos": np.asarray(nodes[lid]["pos"], float) + D*dirv, "parent": lid})
            cid = len(nodes)-1
            pathlen[cid] = pathlen.get(lid, 0.0) + D
            local_ids.append(cid)
            child_dirs.setdefault(lid, []).append(dirv)
            grew = True
        if not grew:
            break
        node_pos2 = np.array([nodes[i]["pos"] for i in local_ids])
        tree2 = cKDTree(node_pos2)
        d2, nn2 = tree2.query(attractors[live], k=1)
        u2 = np.array([rho_u(node_pos2[k]) for k in nn2])
        dk2 = _scaled(u2, dk_near, dk_far, p)
        killed = live[d2 <= dk2]
        alive_local[killed] = False
        cur = int(alive_local.sum())
        stall = stall+1 if cur == prev_alive else 0
        prev_alive = cur
        if stall >= STALL_LIMIT:
            break
    return int(alive_local.sum())


def build_trunkscaffold(sprigs, CB, H, DBH_m, RX, N_primaries,
                        D=0.35, spine_frac=0.62, L_clear=2.0, theta_spawn=22.0,
                        dk_near=1.10, dk_far=0.45, di_near=2.00, di_far=1.90, p=1.5,
                        seed_elev=30.0, golden=137.5, partition_mode="anchor", verbose=False):
    """Build the trunk-spine + scaffold graph. Returns a finished graph dict shaped exactly
    like leafback_graph.build_graph() (nodes/children/root/fork/strand/...)."""
    params = dict(D=D, p=p, L_clear=L_clear, theta_spawn=theta_spawn,
                  dk_near=dk_near, dk_far=dk_far, di_near=di_near, di_far=di_far)
    CH = H - CB
    spine_top = CB + spine_frac*CH
    r_base = DBH_m*0.5

    def r_est(y):  # placement-only linear taper estimate (final radius = pipe model)
        t = np.clip((y - 0.0)/max(spine_top, 1e-6), 0, 1)
        return max(r_base*(1-t) + R0*t, R0)

    # --- trunk spine: ground -> spine_top in D-length segments ---
    nodes = [{"pos": np.array([0.0, 0.0, 0.0]), "parent": -1}]   # root (ground)
    root_id = 0
    n_seg = max(1, int(round(spine_top / D)))
    prev = root_id
    trunk_ids = [root_id]
    for k in range(1, n_seg+1):
        y = spine_top*k/n_seg
        nodes.append({"pos": np.array([0.0, y, 0.0]), "parent": prev})
        prev = len(nodes)-1; trunk_ids.append(prev)
    trunk_top = prev
    trunk_y = np.array([nodes[i]["pos"][1] for i in trunk_ids])

    # --- scaffold origins: distributed heights x golden-angle azimuths ---
    hf = np.linspace(0.04, spine_frac, N_primaries)
    origin_ids, seed_dirs, azimuths = [], [], []
    for k in range(N_primaries):
        y = CB + hf[k]*CH
        az = math.radians((k*golden) % 360.0)
        azimuths.append((k*golden) % 360.0)
        outward = np.array([math.cos(az), 0.0, math.sin(az)])
        # attach to nearest trunk node by height; origin offset to trunk surface
        ti = trunk_ids[int(np.argmin(np.abs(trunk_y - y)))]
        base = np.asarray(nodes[ti]["pos"], float)
        opos = base + max(r_est(y), 0.05)*outward   # >=5cm emergence offset (clean meshing)
        nodes.append({"pos": opos, "parent": ti})
        oid = len(nodes)-1
        origin_ids.append(oid)
        el = math.radians(seed_elev)
        seed_dirs.append((outward*math.cos(el) + np.array([0.0, 1.0, 0.0])*math.sin(el)))

    # angular-spacing guard (report, don't silently fix)
    flags = []
    azs = sorted(azimuths)
    gaps = [azs[(i+1) % len(azs)] - azs[i] for i in range(len(azs)-1)] + [360 - azs[-1] + azs[0]]
    min_gap = min(gaps)
    if min_gap < THETA_MIN - 1e-6:
        flags.append(f"min azimuth gap {min_gap:.1f} < theta_min {THETA_MIN}")

    # --- Voronoi assignment: each attractor -> nearest scaffold CANOPY ANCHOR ---
    anchors = []
    for k, oid in enumerate(origin_ids):
        az = math.radians(azimuths[k])
        outward = np.array([math.cos(az), 0.0, math.sin(az)])
        anchors.append(np.asarray(nodes[oid]["pos"], float) + RX*outward)
    A_anchor = np.array(anchors)
    if partition_mode == "growth":
        # --- GROWTH-ORDER capacity-constrained partition (spec v2/v4 AC-14) ---
        # lowest primary = OLDEST = largest sub-crown. target n_tips_k ~ w_k^(p/2) where
        # w_k = attractors above attachment (da Vinci area-above), so base radius ~ sqrt(area).
        sy = sprigs[:, 1]
        yk = np.array([nodes[o]["pos"][1] for o in origin_ids])
        w = np.array([max(int((sy > y).sum()), 1) for y in yk], float)   # da Vinci area-above
        tgt = w**(PIPE_POWER/2.0)                                        # counts for r ~ sqrt(area)
        cap = np.floor(len(sprigs)*tgt/tgt.sum()).astype(int)
        cap[int(np.argmax(tgt))] += len(sprigs) - int(cap.sum())         # rounding remainder -> largest
        d = np.linalg.norm(sprigs[:, None, :] - A_anchor[None, :, :], axis=2)   # (S, N)
        order = np.stack(np.unravel_index(np.argsort(d, axis=None), d.shape), 1)  # (S*N,2) nearest-first
        assign = np.full(len(sprigs), -1, int)
        filled = np.zeros(N_primaries, int)
        for s, k in order:
            if assign[s] < 0 and filled[k] < cap[k]:
                assign[s] = k; filled[k] += 1
        left = np.where(assign < 0)[0]
        if len(left):
            assign[left] = np.argmin(d[left], axis=1)
    else:
        otree = cKDTree(A_anchor)
        _, assign = otree.query(sprigs, k=1)

    # --- grow each scaffold over its own subset ---
    pathlen = {o: 0.0 for o in origin_ids}
    leftover = 0; per_scaffold = []
    for k, oid in enumerate(origin_ids):
        sel = np.where(assign == k)[0]
        subset = sprigs[sel]
        if len(subset) == 0:
            per_scaffold.append(dict(k=k, assigned=0, unreached=0, az=azimuths[k],
                                     y=float(nodes[oid]["pos"][1])))
            continue
        alive_local = np.ones(len(subset), bool)
        unr = grow_scaffold(nodes, oid, seed_dirs[k], subset, alive_local, RX, params, pathlen)
        leftover += unr
        per_scaffold.append(dict(k=k, assigned=int(len(subset)), unreached=int(unr),
                                 az=azimuths[k], y=float(nodes[oid]["pos"][1])))
        if verbose:
            print(f"  scaffold {k}: y={nodes[oid]['pos'][1]:.1f} az={azimuths[k]:.0f} "
                  f"assigned={len(subset)} unreached={unr}")

    extra = dict(trunk_ids=trunk_ids, trunk_top=trunk_top, origin_ids=origin_ids,
                 spine_top=float(spine_top), per_scaffold=per_scaffold, flags=flags,
                 N_primaries=N_primaries, RX=RX)
    return _finish(nodes, root_id, trunk_top, DBH_m, H, CB, len(sprigs), leftover, extra)


# =========================================================================================
# Crown-type buckets (docs/crown_type_buckets.md + tmp/leafback_bucket_validation.py) — the
# ONLY things that change per tier are the crown envelope (H, cb_frac, aspect, profile table)
# and DBH (trunk caliber budget). Merge/growth machinery is frozen. N=4 primaries for all.
# =========================================================================================
# Per-tier crown-envelope profile tables (normalized half-width, peak 1.0), keyed s/m/l.
# Crown-form SHAPE NAMES removed 2026-07-08: they encoded a parent-species assumption
# (the mature hybrid plane is NOT a wide flat dome) that drove the "lollipop". The grounded
# per-tier form model — architecture AND proportion — lives in
# docs/london_plane_growth_architecture.md §10, keyed to s/m/l.
_T_S = [0.00, 0.15, 0.30, 0.45, 0.55, 0.68, 0.80, 0.90, 1.00]
_P_S = [0.10, 0.42, 0.68, 0.90, 1.00, 0.95, 0.80, 0.56, 0.18]
_T_M = [0.00, 0.12, 0.25, 0.40, 0.50, 0.62, 0.75, 0.88, 1.00]
_P_M = [0.14, 0.55, 0.82, 0.98, 1.00, 0.95, 0.80, 0.55, 0.18]
_T_L = [0.00, 0.12, 0.25, 0.33, 0.48, 0.63, 0.78, 0.90, 1.00]
_P_L = [0.30, 0.72, 0.94, 1.00, 0.96, 0.84, 0.64, 0.42, 0.15]

# tier -> (age_class, H, DBH_m, cb_frac, aspect, profile). age_class is the neutral s/m/l
# meaning (young/middle/mature) — NO shape claim; see §10 for the grounded form per tier.
# NOTE: m aspect 1.00 is a LEGACY value; §10 records the grounded PROVISIONAL ~0.80
# (taller-than-wide) pending off-computer crown measurement — do NOT re-fit it here; the
# sculpt-to-architecture cut owns changing it.
BUCKETS = {
    "s": ("young",  10.0, 7*0.0254,  0.35, 0.80, (_T_S, _P_S)),
    "m": ("middle", 14.4, 15*0.0254, 0.30, 1.00, (_T_M, _P_M)),
    "l": ("mature", 22.0, 28*0.0254, 0.20, 1.20, (_T_L, _P_L)),
}
N_PRIMARIES = 4
SEED = 20260706


def build_bucket_skeleton(tier, verbose=False):
    """Deterministically build the finished trunk-scaffold skeleton graph for a london_plane
    tier (s/m/l). Returns the graph dict (nodes/parent/radius/strand/... + H/CB/RX etc.)."""
    name, H, DBH_m, cb_frac, aspect, profile = BUCKETS[tier]
    g0 = lbg.build_graph(H=H, DBH_m=DBH_m, cb_frac=cb_frac, aspect=aspect,
                         seed=SEED, profile=profile)
    NS = g0["n_sprigs"]
    pts = np.array([g0["nodes"][i]["pos"] for i in range(NS)])
    CB = g0["CB"]
    CH = H - CB
    RX = aspect*CH/2.0
    if verbose:
        print(f"[{tier}] {name}: H={H} DBH={DBH_m*1000:.0f}mm cb={cb_frac} aspect={aspect} "
              f"RX={RX:.2f} sprigs={NS}")
    return build_trunkscaffold(pts, CB, H, DBH_m, RX, N_PRIMARIES,
                               partition_mode="growth", verbose=verbose)


if __name__ == "__main__":
    for tier in ("s", "m", "l"):
        g = build_bucket_skeleton(tier, verbose=True)
        r = [nd["radius"] for nd in g["nodes"]]
        print(f"  nodes={len(g['nodes'])} sprigs={g['n_sprigs']} strands={g['n_strands']} "
              f"leftover={g['leftover_attractors']} spine_top={g['spine_top']:.1f}m "
              f"trunk_r={g['nodes'][g['root']]['radius']*1000:.0f}mm r=[{min(r)*1000:.0f}..{max(r)*1000:.0f}]mm")
        if g["flags"]:
            print("  FLAGS:", "; ".join(g["flags"]))
