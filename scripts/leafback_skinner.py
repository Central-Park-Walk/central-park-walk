#!/usr/bin/env python3
"""Leaf-back per-strand tube skinner — PRODUCTION skinner for the trunk-scaffold (line C) leaf-back
skeleton. Promoted out of tmp/ 2026-07-07 (Chris-approved) after the re-spike showed the per-strand
skinner reaches essentially-connected geometry with clean low-valence junctions on line-C.

WHY this module exists. The space-colonization trunk-scaffold skeleton is a (pos, parent, radius,
strand) node graph. It has NO Mtree path — the production mesher `m_tree.ManifoldMesher().mesh_tree()`
only accepts an opaque Mtree `Tree` C++ object, not a raw node graph. This module skins the node graph
into a bark tube mesh carrying the SAME per-vertex attribute contract Mtree's mesher provides, so the
existing shared steps (`clean_degenerate_geometry` / `enforce_min_twig_diameter` / `stitch_bark_islands`)
AND the downstream foliage-placement + wind-bake paths in generate_trees_mtree.py work unchanged.

Lifted from the Phase-A spike (`tmp/leafback_skin_spike.py` + `tmp/leafback_graph.py::strand_polylines`)
with two PRODUCTION changes:

  1. AXIAL-EMERGENCE base fix. The Phase-A surface-emergence base offsets a child strand's base by
     `0.9*r_parent` along the child's emergence DIRECTION. That works for a branch emerging RADIALLY,
     but for a scaffold emerging NEAR-PARALLEL to the trunk axis (e.g. line-C's upper scaffold that
     leaves the spine going straight up before arcing out) it pushes the base UP the axis, so the child
     base ring sits concentric INSIDE the trunk tube, leaving a (r_parent - r_child) radial gap that
     exceeds stitch's weld tolerance -> the whole sub-crown orphans (measured: one 1274-vert orphan,
     45.3 mm gap vs 32 mm tol). The fix decomposes the emergence and places the base RADIALLY on the
     parent tube surface (using the strand's downstream arc to find a radial direction when the first
     segment is near-axial), so the child base always overlaps the parent surface and welds.
     The protected `tmp/leafback_graph.py` copy is intentionally NOT edited — the two diverge; if the
     merge-line spike ever needs the same fix that is a separate, deliberate decision.

  2. FULL attribute contract. Writes `radius`, `stem_id`, `hierarchy_depth`, `branch_extent`,
     `direction` (Mtree's mesher provides these; the wind bake reads hierarchy_depth/branch_extent/
     stem_id, the card path reads stem_id/radius/direction/branch_extent/hierarchy_depth):
       - radius          FLOAT        per-node pipe-model radius
       - stem_id         INT          logical branch id (== skeleton `strand`); stitch reads int-or-float
       - hierarchy_depth FLOAT        branch order: trunk strand = 0, each cross-strand fork +1
       - branch_extent   FLOAT        Euclidean path length from the root node (monotone to tips)
       - direction       FLOAT_VECTOR unit branch tangent at the vertex (RMF), orients the sprig card

KNOWN RESIDUAL (accepted 2026-07-07, non-blocking). Raw tube-through-tube interpenetration at the
thickest low-scaffold forks (no smooth branch collar): ~5% self-intersecting faces at RING=10 preview,
worst at the lowest scaffold, milder up the tree. Cosmetically minor at s/m tier viewing distance.
INTENDED REMEDY at production time: RING ~= 24 + smoothing iterations (the default RING here is 24).
Logged so it is not silently rediscovered later as a "new" bug.
"""
import bpy, sys, math
import numpy as np
from mathutils import Vector, Quaternion

DEFAULT_RING = 24          # production radial resolution (preview spike used 10)
PIPE_TIP_MIN = 0.004


# --------------------------------------------------------------------------- graph helpers (pure numpy)
def _children(nodes):
    ch = {i: [] for i in range(len(nodes))}
    for i, nd in enumerate(nodes):
        p = nd["parent"]
        if p >= 0:
            ch[p].append(i)
    return ch


def _node_pathlen(nodes):
    """Euclidean path length from the root along the parent chain (for branch_extent)."""
    N = len(nodes)
    pl = [None] * N
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, N + 1000))
    def rec(i):
        if pl[i] is not None:
            return pl[i]
        p = nodes[i]["parent"]
        if p < 0:
            pl[i] = 0.0
        else:
            pl[i] = rec(p) + float(np.linalg.norm(np.asarray(nodes[i]["pos"], float) - np.asarray(nodes[p]["pos"], float)))
        return pl[i]
    for i in range(N):
        rec(i)
    sys.setrecursionlimit(old)
    return pl


def _strand_starts(nodes, strand):
    """The entry node of each strand (its parent is in a different strand, or it is the root)."""
    starts = {}
    for i, nd in enumerate(nodes):
        p = nd["parent"]
        if p == -1 or strand[p] != strand[i]:
            starts[strand[i]] = i
    return starts


def _strand_order(nodes, strand, starts):
    """Branch order per strand: trunk strand (root's) = 0; each strand = parent-strand order + 1."""
    order = {}
    def ordof(sid):
        if sid in order:
            return order[sid]
        s = starts[sid]
        p = nodes[s]["parent"]
        order[sid] = 0 if p == -1 else ordof(strand[p]) + 1
        return order[sid]
    for sid in starts:
        ordof(sid)
    return order


def strand_polylines(nodes, children, strand):
    """Each strand -> ordered list of (pos, radius, node_id), base(=parent side) first, with a
    SURFACE-EMERGENCE base prepended (node_id = -1) so child tubes overlap the parent at forks.

    AXIAL-EMERGENCE FIX vs the Phase-A copy: the prepended base is offset RADIALLY onto the parent
    tube surface (perpendicular to the parent axis), not along the child's raw emergence direction —
    so a near-vertically-emerging scaffold still overlaps and welds instead of sitting concentric
    inside the trunk.
    """
    starts = _strand_starts(nodes, strand)
    polys = {}
    for sid, s in starts.items():
        chain = []
        n = s
        while n != -1:
            chain.append(n)
            nxt = [c for c in children[n] if strand[c] == sid]
            n = nxt[0] if nxt else -1
        pts = [(np.asarray(nodes[i]["pos"], float), float(nodes[i]["radius"]), i) for i in chain]
        p = nodes[s]["parent"]
        if p != -1:
            ppos = np.asarray(nodes[p]["pos"], float)
            pr = float(nodes[p]["radius"])
            cfirst = np.asarray(nodes[s]["pos"], float)
            # parent axis at p (incoming trunk/limb direction)
            gp = nodes[p]["parent"]
            pa = (ppos - np.asarray(nodes[gp]["pos"], float)) if gp != -1 else (cfirst - ppos)
            pan = np.linalg.norm(pa)
            pa_hat = pa / pan if pan > 1e-9 else np.array([0.0, 1.0, 0.0])
            # radial component of the child's emergence (perpendicular to the parent axis)
            d = cfirst - ppos
            radial = d - np.dot(d, pa_hat) * pa_hat
            rn = np.linalg.norm(radial)
            if rn < 0.2 * max(np.linalg.norm(d), 1e-9):
                # near-AXIAL emergence: use the strand's downstream arc to recover a radial direction
                nid = s
                acc = np.zeros(3)
                cnt = 0
                for _ in range(4):
                    dch = [c for c in children[nid] if strand[c] == sid]
                    if not dch:
                        break
                    nid = dch[0]
                    acc += np.asarray(nodes[nid]["pos"], float) - ppos
                    cnt += 1
                if cnt:
                    rd = acc / cnt
                    radial = rd - np.dot(rd, pa_hat) * pa_hat
                    rn = np.linalg.norm(radial)
            if rn > 1e-9:
                radial_hat = radial / rn
            else:
                tmp = np.array([1.0, 0.0, 0.0]) if abs(pa_hat[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
                radial_hat = np.cross(pa_hat, tmp)
                radial_hat /= np.linalg.norm(radial_hat)
            base_pos = ppos + 0.9 * pr * radial_hat
            # Emergence ring must match the parent radius so the fork reads as a
            # filled shoulder, not a thinner child tube tip-welded onto the parent.
            pts.insert(0, (base_pos, pr, -1))
        polys[sid] = pts
    return polys


# --------------------------------------------------------------------------- frames + mesher (bpy)
def _frames(pts):
    """Rotation-minimizing frames (parallel transport) along a polyline. Verbatim from the spike."""
    P = [Vector(p) for p in pts]
    n = len(P)
    tans = []
    for i in range(n):
        if i == 0: t = P[1] - P[0]
        elif i == n - 1: t = P[n - 1] - P[n - 2]
        else: t = P[i + 1] - P[i - 1]
        if t.length < 1e-9: t = Vector((0, 1, 0))
        tans.append(t.normalized())
    a = tans[0]
    ref = Vector((1, 0, 0)) if abs(a.x) < 0.9 else Vector((0, 0, 1))
    u = (ref - a * ref.dot(a)).normalized()
    frames = [(u, a.cross(u).normalized())]
    for i in range(1, n):
        u_prev, _ = frames[-1]
        t_prev, t_cur = tans[i - 1], tans[i]
        axis = t_prev.cross(t_cur)
        if axis.length < 1e-8:
            u = u_prev
        else:
            axis.normalize()
            ang = math.acos(max(-1, min(1, t_prev.dot(t_cur))))
            u = u_prev.copy(); u.rotate(Quaternion(axis, ang))
            u = (u - t_cur * u.dot(t_cur)).normalized()
        frames.append((u, t_cur.cross(u).normalized()))
    return P, frames, tans


def _ring_for_radius(r, ring_max):
    """Radius-scaled ring count (lever 1, AC-8 density pass 2026-07-08). Thick trunk/primary limbs
    keep the full ring; secondaries half; twigs a third (min 8). Bark verts scale with ring, and the
    node count is dominated by thin twig strands, so this recovers ~2-3x on the heavy l
    tier while keeping the low thick limbs smooth.

    Chosen PER-STRAND (from the strand's thickest node) so a strand is a single uniform-ring tube —
    there are NO intra-strand ring transitions to fan/weld. Ring-count mismatches occur ONLY at fork
    welds, where the child's base ring welds onto the parent surface exactly as before (the
    radius-derived stitch tol is keyed to the thickest node at ring_max, so it still covers every
    thinner junction). Those fork welds are the ring-transition junctions the density-pass verify
    must inspect for cracks/non-manifoldness (components==1 alone would miss a surface crack)."""
    if r >= 0.09:
        return ring_max
    if r >= 0.035:
        return max(8, ring_max // 2)
    return max(8, ring_max // 3)


def build_tube_mesh(g, ring=DEFAULT_RING, name="leafback_bark", radius_scaled=True):
    """Skin a leaf-back node-graph `g` (keys: nodes[{pos,parent,radius}], strand[list]) into a bark
    tube mesh with the full Mtree attribute contract. Returns the Blender object.

    radius_scaled=True (default): ring count is scaled per strand by radius (_ring_for_radius); `ring`
    is then the MAX (thick-limb) ring. False: uniform `ring` everywhere (the pre-density-pass behavior,
    kept for A/B measurement)."""
    ring_max = ring
    nodes, strand = g["nodes"], g["strand"]
    children = g.get("children") or _children(nodes)
    starts = _strand_starts(nodes, strand)
    order = _strand_order(nodes, strand, starts)
    pathlen = _node_pathlen(nodes)
    root_extent = None
    polys = strand_polylines(nodes, children, strand)

    verts, faces = [], []
    v_radius, v_stem, v_depth, v_extent, v_dir = [], [], [], [], []
    for sid, poly in polys.items():
        if len(poly) < 2:
            continue
        pts = [p for p, r, nid in poly]
        radii = [r for p, r, nid in poly]
        nids = [nid for p, r, nid in poly]
        ring = _ring_for_radius(max(radii), ring_max) if radius_scaled else ring_max
        P, frames, tans = _frames(pts)
        depth = float(order.get(sid, 0))
        # per-point branch_extent: use node pathlen; the synthetic base (nid=-1) inherits its strand
        # start's parent extent so it sits just below the strand base monotonically.
        extents = []
        for i, nid in enumerate(nids):
            if nid >= 0:
                extents.append(pathlen[nid])
            else:
                s = starts[sid]
                p = nodes[s]["parent"]
                extents.append(pathlen[p] if p != -1 else 0.0)
        ring_start = []
        for i in range(len(P)):
            u, v = frames[i]
            r = radii[i]
            t = tans[i]
            base = len(verts)
            ring_start.append(base)
            for k in range(ring):
                a = 2 * math.pi * k / ring
                nrm = (math.cos(a) * u + math.sin(a) * v)
                verts.append(P[i] + r * nrm)
                v_radius.append(r); v_stem.append(int(sid))
                v_depth.append(depth); v_extent.append(extents[i])
                v_dir.append((t.x, t.y, t.z))
        for i in range(len(P) - 1):
            b0, b1 = ring_start[i], ring_start[i + 1]
            for k in range(ring):
                k2 = (k + 1) % ring
                faces.append((b0 + k, b0 + k2, b1 + k2, b1 + k))
        # tip cap
        tipc = len(verts)
        verts.append(P[-1]); v_radius.append(radii[-1]); v_stem.append(int(sid))
        v_depth.append(depth); v_extent.append(extents[-1])
        tt = tans[-1]; v_dir.append((tt.x, tt.y, tt.z))
        b = ring_start[-1]
        for k in range(ring):
            faces.append((b + k, b + (k + 1) % ring, tipc))

    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in verts], [], faces)
    me.update()
    me.attributes.new("radius", 'FLOAT', 'POINT').data.foreach_set("value", v_radius)
    me.attributes.new("stem_id", 'INT', 'POINT').data.foreach_set("value", v_stem)
    me.attributes.new("hierarchy_depth", 'FLOAT', 'POINT').data.foreach_set("value", v_depth)
    me.attributes.new("branch_extent", 'FLOAT', 'POINT').data.foreach_set("value", v_extent)
    dir_flat = [c for xyz in v_dir for c in xyz]
    me.attributes.new("direction", 'FLOAT_VECTOR', 'POINT').data.foreach_set("vector", dir_flat)

    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    me.calc_loop_triangles()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def load_graph_npz(path):
    """Build a skinner `g` dict from a saved trunk-scaffold skeleton .npz."""
    d = np.load(path)
    pos, parent, radius, strand = d["pos"], d["parent"].astype(int), d["radius"], d["strand"].astype(int)
    N = len(pos)
    nodes = [{"pos": np.asarray(pos[i], float), "parent": int(parent[i]), "radius": float(radius[i])}
             for i in range(N)]
    g = dict(nodes=nodes, children=_children(nodes), strand=list(strand),
             root=int(d["root"]) if "root" in d else -1)
    for k in ("H", "CB", "RX"):
        if k in d:
            g[k] = float(d[k])
    return g
