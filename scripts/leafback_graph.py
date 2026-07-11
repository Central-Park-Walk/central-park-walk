#!/usr/bin/env python3
"""Leaf-back attractor cloud + m-tier merge graph — PROMOTED copy (2026-07-08).

Promoted out of gitignored tmp/ so the production leaf-back london_plane build has a
committed, reproducible source for the sprig (attractor) cloud. This is a COPY of the
protected `tmp/leafback_graph.py` (the two are allowed to diverge; the tmp original is
NOT edited, mirroring how `scripts/leafback_skinner.py` carries a corrected copy of
`strand_polylines`).

ONE deliberate divergence from the tmp original:
  * `build_graph(...)` takes a `profile=(T, P)` argument (default = the m-tier envelope
    table, unchanged) so the s and l tiers can be built
    with their own crown-envelope tables (from `tmp/leafback_bucket_validation.py`) —
    the ONLY thing that changes per bucket, exactly per crown_type_buckets.md
    ("no parameter changes beyond what the envelope shape dictates"). The merge machinery
    (SPRIG_SPACE, SHELL_THICK, CELL0_MULT, GROW, pull laws, stop-at-4) is byte-identical
    and frozen.

The trunk-scaffold skeleton (line C, `scripts/leafback_skeleton.py`) consumes ONLY the
sprig positions + (CB, H, DBH_m) constants from this graph; the returned merge tree
(nodes/children/strand of the OLD merge line A) is not used by production and is kept
only so the m-bucket cloud path is byte-identical to the validated one.
"""
import numpy as np, math

SPRIG_SPACE, SHELL_THICK = 0.65, 1.3
CELL0_MULT, GROW = 2.0, 1.55
PIPE_POWER = 2.3  # pipe model exponent: r_parent^p = sum(r_child^p). ~2.0-2.5 for trees.

# m-tier v2 envelope (widest ~mid) — the default profile (identical to validation).
_T = np.array([0.00, 0.12, 0.25, 0.40, 0.50, 0.62, 0.75, 0.88, 1.00])
_P = np.array([0.14, 0.55, 0.82, 0.98, 1.00, 0.95, 0.80, 0.55, 0.18])


def build_graph(H=14.4, DBH_m=15*0.0254, cb_frac=0.30, aspect=1.00, seed=20260706,
                profile=None):
    """Build the sprig (attractor) cloud + merge graph for one crown tier.

    profile: optional (T, P) normalized half-width envelope tables (peak 1.0). Default =
    the m-tier envelope table. The s and l tiers pass their own tables.
    """
    T, P = (_T, _P) if profile is None else (np.asarray(profile[0]), np.asarray(profile[1]))
    rng = np.random.default_rng(seed)
    CB = cb_frac*H; CH = H-CB; RX = aspect*CH/2.0
    def cr(t): return RX*np.interp(np.clip(t, 0, 1), T, P)
    # --- sprig fill (frozen) ---
    ts = rng.uniform(0, 1, 60000); y = CB+ts*CH; R = cr(ts)
    keep = R > 0.15; ts, y, R = ts[keep], y[keep], R[keep]
    th = rng.uniform(0, 2*math.pi, len(ts))
    # VOLUME-UNIFORM radial fill (Runions, Lane & Prusinkiewicz 2007 canonical default, beta=0.5):
    # attraction points fill the whole crown VOLUME, not a 1.3m surface shell. For a
    # surface-of-revolution slice of local radius R, volume-uniform == area-uniform per slice ==
    # rr = R*sqrt(U(0,1)). This replaces the Fig.7 degenerate hollow-lantern shell placement
    # (old: depth = U**1.6 * SHELL_THICK, biased ONTO the skin), the published degenerate case.
    rr = R * np.sqrt(rng.uniform(0, 1, len(ts)))
    Pp = np.stack([rr*np.cos(th), y, rr*np.sin(th)], 1)
    cell = SPRIG_SPACE; grid = {}; keep_pts = []
    for p in Pp:
        c = (int(p[0]//cell), int(p[1]//cell), int(p[2]//cell)); ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid.get((c[0]+dx, c[1]+dy, c[2]+dz), ()):
                        if np.sum((p-q)**2) < cell*cell: ok = False; break
                    if not ok: break
                if not ok: break
            if not ok: break
        if ok: grid.setdefault(c, []).append(p); keep_pts.append(p)
    sprigs = np.array(keep_pts)

    # --- node graph: each node {pos, parent}. sprigs are leaves (tips). ---
    nodes = [{"pos": sprigs[i].copy(), "parent": -1} for i in range(len(sprigs))]
    active = [{"id": i, "pos": sprigs[i].copy()} for i in range(len(sprigs))]
    FORK = np.array([0.0, CB, 0.0]); cell0 = SPRIG_SPACE*CELL0_MULT; L = 0
    while len(active) > 4 and L < 12:
        cs = cell0*(GROW**L); bins = {}
        for nd in active:
            k = (int(nd["pos"][0]//cs), int(nd["pos"][1]//cs), int(nd["pos"][2]//cs))
            bins.setdefault(k, []).append(nd)
        nxt = []
        for grp in bins.values():
            if len(grp) == 1:
                nxt.append(grp[0]); continue  # singleton carries up unchanged
            cen = np.mean([q["pos"] for q in grp], 0)
            pa = min(.20+.06*L, .6); pd = min(.12+.05*L, .5)
            par = cen.copy(); par[0] *= (1-pa); par[2] *= (1-pa)
            par[1] = max(cen[1]-pd*(cen[1]-CB), CB+0.3)
            pid = len(nodes); nodes.append({"pos": par, "parent": -1})
            for q in grp: nodes[q["id"]]["parent"] = pid
            nxt.append({"id": pid, "pos": par})
        active = nxt; L += 1
    # remaining actives -> FORK node -> ROOT (ground)
    fork_id = len(nodes); nodes.append({"pos": FORK.copy(), "parent": -1})
    for nd in active: nodes[nd["id"]]["parent"] = fork_id
    root_id = len(nodes); nodes.append({"pos": np.array([0.0, 0.0, 0.0]), "parent": -1})
    nodes[fork_id]["parent"] = root_id

    # --- children map + pipe-model radius (leaves seed r0, accumulate to root) ---
    children = {i: [] for i in range(len(nodes))}
    for i, nd in enumerate(nodes):
        if nd["parent"] >= 0: children[nd["parent"]].append(i)
    r0 = 0.004  # 4 mm tip seed
    radius = [0.0]*len(nodes)
    order = _topo_leaves_first(nodes, children)
    for i in order:
        if not children[i]:
            radius[i] = r0
        else:
            radius[i] = (sum(radius[c]**PIPE_POWER for c in children[i]))**(1.0/PIPE_POWER)
    # scale so trunk (root) radius == DBH/2
    scale = (DBH_m*0.5) / max(radius[root_id], 1e-6)
    radius = [r*scale for r in radius]
    for i, nd in enumerate(nodes): nd["radius"] = radius[i]

    # --- strand decomposition (primary-child continuation = Mtree stem_id) ---
    strand = [-1]*len(nodes); next_sid = [0]
    def assign(nid, sid):
        strand[nid] = sid
        ch = children[nid]
        if not ch: return
        prim = max(ch, key=lambda c: radius[c])   # thickest child continues the strand
        for c in ch:
            if c == prim: assign(c, sid)
            else:
                next_sid[0] += 1; assign(c, next_sid[0])
    assign(root_id, 0)

    return dict(nodes=nodes, children=children, root=root_id, fork=fork_id,
                strand=strand, n_strands=next_sid[0]+1, n_sprigs=len(sprigs),
                H=H, DBH_m=DBH_m, CB=CB)

def _topo_leaves_first(nodes, children):
    """Order node ids so every node comes after all its children (post-order)."""
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


if __name__ == "__main__":
    g = build_graph()
    r = [nd["radius"] for nd in g["nodes"]]
    print(f"nodes={len(g['nodes'])}  sprigs(leaves)={g['n_sprigs']}  strands={g['n_strands']}")
    print(f"trunk radius={g['nodes'][g['root']]['radius']*1000:.1f}mm  (DBH {g['DBH_m']*1000:.0f}mm -> {g['DBH_m']*500:.0f}mm target)")
    print(f"radius range: {min(r)*1000:.1f}..{max(r)*1000:.1f} mm")
