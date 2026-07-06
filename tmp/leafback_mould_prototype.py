#!/usr/bin/env python3
"""One-off leaf-back mould prototype for ONE representative London plane.

NOT general tooling. Builds a single crown volume, fills it with sprig-card
placement points, then connects LEAF-BACK (sprig -> twig -> branch -> primary
-> trunk) by agglomerative merging. Hop count is emergent, not imposed.

Representative specimen (from Part A, middle/most-common height bucket):
  height H = 14.4 m, DBH = 15 in = 0.381 m, broad open-grown rounded dome.
Outputs a wireframe render + a point/edge dump under tmp/.
"""
import numpy as np, math, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(20260706)

# --- Representative specimen dimensions (Part A) ---------------------------
H          = 14.4          # total height (m), middle bucket center
DBH_M      = 15 * 0.0254   # 0.381 m
CROWN_BASE = 0.37 * H      # ~5.3 m clear bole (London plane high mottled bole)
CROWN_TOP  = H
CROWN_H    = CROWN_TOP - CROWN_BASE          # ~9.1 m
CROWN_RX   = 5.3           # widest half-width -> width ~10.6 m (aspect W/Hcrown ~1.16)
WIDEST_FRAC= 0.55          # widest at 55% up the crown (broad dome, slightly low)
SPRIG_SPACE= 0.65          # sprig-card footprint spacing (~4-leaf unit, card_rule_spacing regime)
SHELL_THICK= 1.3           # foliage rides the crown surface + inward shell depth (m)

# --- crown envelope: ovoid dome. radius(t) for t in [0,1] up the crown -----
def crown_radius(t):
    # t=0 at crown base, t=1 at apex. Smooth lobed ovoid, widest at WIDEST_FRAC.
    # base is pinched (branches gather to bole), apex rounded.
    a = (t - WIDEST_FRAC)
    prof = np.sqrt(np.clip(1.0 - (a/ max(WIDEST_FRAC,1-WIDEST_FRAC))**2, 0, 1))
    # pinch the very bottom so crown tucks into the bole
    prof *= np.clip(t*3.0, 0, 1)**0.5
    return CROWN_RX * prof

# --- 1. FILL crown volume with sprig points (shell) ------------------------
# Poisson-ish surface sampling: sample many candidate points on the ovoid
# surface at a spread of inward depths, then thin by min-distance.
def sample_shell(n_try=60000):
    ts = rng.uniform(0,1,n_try)
    y  = CROWN_BASE + ts*CROWN_H
    R  = crown_radius(ts)
    keep = R > 0.15
    ts,y,R = ts[keep], y[keep], R[keep]
    theta = rng.uniform(0, 2*math.pi, len(ts))
    depth = rng.uniform(0.0, 1.0, len(ts))**1.6 * SHELL_THICK   # bias to surface
    rr = np.clip(R - depth, 0.05, None)
    x = rr*np.cos(theta); z = rr*np.sin(theta)
    # surface normal (outward) ~ radial in xz, plus vertical from profile slope
    nx, nz = np.cos(theta), np.sin(theta)
    dt=1e-3; dR=(crown_radius(np.clip(ts+dt,0,1))-crown_radius(np.clip(ts-dt,0,1)))/(2*dt)
    ny = -dR/CROWN_H
    n = np.stack([nx, np.full_like(nx,0.0)+ny*0.0, nz],1)  # placeholder
    n = np.stack([nx, np.full_like(nx, 0.0), nz],1)
    n[:,1] = np.clip(ny,-1.5,1.5)
    n /= np.linalg.norm(n,axis=1,keepdims=True)+1e-9
    P = np.stack([x,y,z],1)
    return P, n

def thin(P, N, r):
    # greedy min-distance thinning on a grid
    cell = r
    grid = {}
    keepP, keepN = [], []
    for p,nn in zip(P,N):
        c = (int(p[0]//cell),int(p[1]//cell),int(p[2]//cell))
        ok=True
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    for q in grid.get((c[0]+dx,c[1]+dy,c[2]+dz),()):
                        if np.sum((p-q)**2) < r*r: ok=False; break
                    if not ok: break
                if not ok: break
            if not ok: break
        if ok:
            grid.setdefault(c,[]).append(p); keepP.append(p); keepN.append(nn)
    return np.array(keepP), np.array(keepN)

Pc, Nc = sample_shell()
sprigs, snorm = thin(Pc, Nc, SPRIG_SPACE)
print(f"[fill] {len(sprigs)} sprig cards on crown shell (spacing {SPRIG_SPACE} m)")

# --- 2. CONNECT leaf-back: agglomerative merge toward trunk ----------------
# Each level: bin active nodes into a grid whose cell grows with level; all
# nodes in a cell merge to ONE parent placed at their centroid, then pulled
# toward the trunk axis and downward toward the fork. Singletons carry up
# unchanged (their chain just gets longer). Repeat until few nodes remain,
# then wire those primaries to the trunk fork. Hop count is emergent.
FORK = np.array([0.0, CROWN_BASE, 0.0])
edges = []                       # (child_xyz, parent_xyz, level)
active = [ (tuple(p), 0) for p in sprigs ]   # (pos, sprig_id-ish); track hops per origin
# We track lineage hop counts by carrying a list of origin sprig indices per node.
nodes = [ {"pos": sprigs[i].copy(), "origins": {i}} for i in range(len(sprigs)) ]

cell0 = SPRIG_SPACE*2.0
growth = 1.55
level = 0
hop_of = np.zeros(len(sprigs), dtype=int)
while len(nodes) > 4 and level < 12:
    cell = cell0 * (growth**level)
    bins = {}
    for nd in nodes:
        p = nd["pos"]
        key = (int(p[0]//cell), int(p[1]//cell), int(p[2]//cell))
        bins.setdefault(key, []).append(nd)
    newnodes = []
    for key, group in bins.items():
        if len(group) == 1:
            newnodes.append(group[0])          # carries up, no new edge, no hop
            continue
        cen = np.mean([g["pos"] for g in group], axis=0)
        # pull toward trunk axis (x,z -> 0) and down toward fork, more with level
        pull_axis = min(0.20 + 0.06*level, 0.6)
        pull_down = min(0.12 + 0.05*level, 0.5)
        parent = cen.copy()
        parent[0] *= (1-pull_axis); parent[2] *= (1-pull_axis)
        parent[1] = cen[1] - pull_down*(cen[1]-CROWN_BASE)
        parent[1] = max(parent[1], CROWN_BASE+0.3)
        origins = set()
        for g in group:
            edges.append((g["pos"].copy(), parent.copy(), level))
            origins |= g["origins"]
        for oi in origins: hop_of[list([oi])] = hop_of[oi] + 1  # +1 hop this merge
        newnodes.append({"pos": parent, "origins": origins})
    nodes = newnodes
    print(f"[merge L{level}] cell={cell:.2f}m -> {len(nodes)} nodes")
    level += 1

# wire remaining primaries to the trunk fork, fork to ground
for nd in nodes:
    edges.append((nd["pos"].copy(), FORK.copy(), level))
    for oi in nd["origins"]: hop_of[oi] += 1
edges.append((FORK.copy(), np.array([0.0,0.0,0.0]), level+1))  # bole
n_primaries = len(nodes)
print(f"[trunk] {n_primaries} primaries -> fork@{CROWN_BASE:.1f}m -> ground")
print(f"[hops] sprig->trunk hop count: min {hop_of.min()} med {int(np.median(hop_of))} max {hop_of.max()} mean {hop_of.mean():.2f}")

# --- 3. Render wireframe (two views) + dumps -------------------------------
from mpl_toolkits.mplot3d import Axes3D  # noqa
fig = plt.figure(figsize=(15,8))
for si,(az,el,ttl) in enumerate([(-60,12,"oblique"), (0,4,"front-on")]):
    ax = fig.add_subplot(1,2,si+1, projection='3d')
    # skeleton edges colored by level (trunk dark -> twig light green)
    lv_max = max(e[2] for e in edges)
    cmap = plt.cm.YlGn
    for a,b,lv in edges:
        col = cmap(0.25+0.7*(lv/lv_max))
        lw = 0.4 + 2.6*(1-lv/lv_max)
        ax.plot([a[0],b[0]],[a[1],b[1]],[a[2],b[2]], color=col, lw=lw)
    # sprig cards as small green dots with outward normals
    ax.scatter(sprigs[:,0],sprigs[:,1],sprigs[:,2], s=3, c='#2e7d32', alpha=0.5)
    ax.set_title(f"London plane leaf-back mould ({ttl})\nH={H}m DBH=15in  {len(sprigs)} sprigs  hops med {int(np.median(hop_of))}")
    ax.set_box_aspect((1,1,1)); ax.view_init(elev=el, azim=az)
    ax.set_xlim(-7,7); ax.set_zlim(-7,7); ax.set_ylim(0,15)
    ax.set_xlabel('x'); ax.set_ylabel('y (up)'); ax.set_zlabel('z')
plt.tight_layout()
out="/home/chris/central-park-walk/tmp/leafback_mould_wire.png"
plt.savefig(out, dpi=110); print("[render]", out)

# crown-shell point cloud only (top-down + side)
fig2,axs=plt.subplots(1,2,figsize=(12,5))
axs[0].scatter(sprigs[:,0],sprigs[:,2],s=4,c=sprigs[:,1],cmap='viridis'); axs[0].set_title('sprig cards — plan (top-down)'); axs[0].set_aspect('equal')
axs[1].scatter(sprigs[:,0],sprigs[:,1],s=4,c='#2e7d32',alpha=.5); axs[1].set_title('sprig cards — elevation'); axs[1].set_aspect('equal')
plt.tight_layout(); out2="/home/chris/central-park-walk/tmp/leafback_sprig_cloud.png"; plt.savefig(out2,dpi=110); print("[render]",out2)

# numeric dump
np.savetxt("/home/chris/central-park-walk/tmp/leafback_sprigs.xyz", np.hstack([sprigs,snorm]), fmt="%.3f",
           header="x y z nx ny nz  (sprig card position + outward twig normal)")
stats=dict(n_sprigs=int(len(sprigs)), n_edges=len(edges), n_primaries=int(n_primaries),
           hops=dict(min=int(hop_of.min()),med=int(np.median(hop_of)),max=int(hop_of.max()),mean=round(float(hop_of.mean()),2)),
           height_m=H, dbh_in=15, crown_base_m=round(CROWN_BASE,1), crown_rx_m=CROWN_RX)
json.dump(stats, open("/home/chris/central-park-walk/tmp/leafback_stats.json","w"), indent=2)
print("[stats]", json.dumps(stats))
