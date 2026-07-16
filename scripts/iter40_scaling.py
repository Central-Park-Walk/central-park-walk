#!/usr/bin/env python3
"""iter-40 — VERIFY the load-bearing assumption behind Chris's REDIRECT (LEDGER iter-39 verdict).

Claim to test, against the ACTUAL wiring (not iter-24's comment):
  (1) the shed gate's cost is a *surviving* woody-internode COUNT that scales ~R^3 (crown volume),
  (2) income (light gathered) scales ~R^2 (crown silhouette / shell),
  (3) the shed gate UNDER-prunes the interior: many surviving woody internodes stand in deep shade.

Instrument: monkeypatch Grower.shed to log, once per year, the gate's OWN two terms at the whole
tree — income = Sum(foliage_light)  and  nwood = #(alive, non-foliage nodes) = sz[trunk] — plus a
crown size R. One l-tree ontogeny (104 yr) is a clean, same-seed R-sweep with dozens of points.

The killer number is d log(nwood)/d log(income): 1.0 => cost tracks income (sustainable);
~1.5 => cost ∝ income^1.5 = volume-vs-surface = the gate condemning bigness (diagnosis CONFIRMED).
"""
import sys, os, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plane_grower as pg

TIER = sys.argv[1] if len(sys.argv) > 1 else "l"
H, DBH = pg.TIERS[TIER]
YEARS = pg.TIER_AGES[TIER]

log = []            # (year, income, nwood, ntip, R, Htop)
orig_shed = pg.Grower.shed

def shed_hook(self, light, children, year=None):
    r = orig_shed(self, light, children, year)
    income = float(sum(light.values()))                      # gate numerator lg[trunk]
    nwood  = sum(1 for nd in self.nodes if nd.alive and not nd.foliage)   # gate denom sz[trunk]
    # a woody TIP = alive, non-foliage, non-root, no alive woody child (matches grower's tipset test)
    kids = children
    ntip = sum(1 for i, nd in enumerate(self.nodes)
               if nd.alive and not nd.foliage and i != 0
               and not any(self.nodes[c].alive and not self.nodes[c].foliage for c in kids[i]))
    pos = np.array([nd.pos for i, nd in enumerate(self.nodes) if nd.alive and nd.foliage])
    if len(pos):
        Rc = float(np.percentile(np.hypot(pos[:, 0], pos[:, 2]), 90))
        Htop = float(pos[:, 1].max())
    else:
        Rc = Htop = 0.0
    log.append((year, income, nwood, ntip, Rc, Htop))
    return r

pg.Grower.shed = shed_hook

print(f"[iter40] growing {TIER} tier: H={H} DBH_census={DBH} years={YEARS} (single job)", flush=True)
g = pg.Grower(H, DBH, seed=pg.SEED)
result = g.run(YEARS, verbose=False)

arr = np.array(log, dtype=float)          # (year, income, nwood, ntip, R, H)
yr, inc, nwood, ntip, R, Htop = arr.T

# ---- interior-light histogram at the FINAL year (does the interior survive shaded?) ----
shadow, mn = g._shadow, g._mn
wl = np.array([g.light_at(nd.pos, shadow, mn)
               for nd in g.nodes if nd.alive and not nd.foliage])
FULL = pg.FULL_LIGHT
frac_zero = float((wl < 0.02 * FULL).mean())
frac_deep = float((wl < 0.10 * FULL).mean())
frac_lit  = float((wl > 0.50 * FULL).mean())

def slope(x, y, mask):
    lx, ly = np.log(x[mask]), np.log(y[mask])
    return float(np.polyfit(lx, ly, 1)[0])

# fit over the MATURE portion (skip juvenile transient): nwood >= 200 AND after year 15
m = (nwood >= 200) & (yr >= 15) & (inc > 0) & (R > 0)
full = (nwood >= 5) & (inc > 0) & (R > 0)

print("\n================= iter-40 SCALING RESULT =================", flush=True)
print(f"final: year={int(yr[-1])} income={inc[-1]:.1f} nwood={int(nwood[-1])} "
      f"ntip={int(ntip[-1])} R={R[-1]:.2f}m H={Htop[-1]:.2f}m", flush=True)
print(f"mature-fit window: {int(m.sum())} years (nwood>=200, yr>=15)\n", flush=True)
print(f"  d log(nwood)  / d log(income) = {slope(inc,  nwood, m):.2f}   [1.0=sustainable, ~1.5=R^3-vs-R^2]", flush=True)
print(f"  d log(ntip)   / d log(income) = {slope(inc,  ntip,  m):.2f}", flush=True)
print(f"  d log(income) / d log(R)      = {slope(R,    inc,   m):.2f}   [~2 = silhouette/shell]", flush=True)
print(f"  d log(nwood)  / d log(R)      = {slope(R,    nwood, m):.2f}   [~3 = crown volume/solid]", flush=True)
print(f"  d log(ntip)   / d log(R)      = {slope(R,    ntip,  m):.2f}", flush=True)
print(f"\ninterior light over {len(wl)} surviving woody internodes (FULL_LIGHT={FULL}):", flush=True)
print(f"  frac at ~0 light (<0.02C) = {frac_zero:.2f}", flush=True)
print(f"  frac in deep shade (<0.10C) = {frac_deep:.2f}", flush=True)
print(f"  frac well lit   (>0.50C) = {frac_lit:.2f}", flush=True)
print(f"  woody light: min={wl.min():.3f} med={np.median(wl):.3f} mean={wl.mean():.3f} max={wl.max():.3f}", flush=True)

np.savez("tmp/iter40_scaling.npz",
         per_year=arr, woody_light=wl,
         cols=np.array("year,income,nwood,ntip,R,H".split(",")))
print("\nsaved -> tmp/iter40_scaling.npz", flush=True)
print("=========================================================", flush=True)
