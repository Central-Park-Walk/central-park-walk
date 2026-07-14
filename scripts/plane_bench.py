"""plane_bench — the n-seed measurement instrument for the London plane grower.

WHY THIS EXISTS (iter-30's finding, and the rail it left):
    An n=1 instrument cannot measure a ratio. Iters 27-30 fitted the magnitude family against
    numbers read off ONE tree, and when three seeds were finally run, the m->l crown lever came
    out 1.86 / 3.40 / 1.78 -- a +-50% spread around every conclusion that had been drawn from it.
    The fit was inside its own noise.

WHAT IT REPORTS, AND WHY THAT AND NOT A MEAN:
    A mean without a resolution is the same lie in nicer clothes. For every observable this reports
    the residual against census IN UNITS OF THE INSTRUMENT: half-width = 2*SEM = 2*sd/sqrt(n).

        RESOLVED  |mean - census| > 2*SEM  -- the model really is off, and by how much
        --noise-- otherwise                -- the deviation is indistinguishable from seed luck,
                                              and MAY NOT BE THE TELL AN ITERATION TURNS ON.

    For an unresolved residual it prints n_req = (2*sd/residual)^2: the seeds it would take to see
    it. If n_req is absurd, that observable is not an instrument at this effect size, and no
    amount of staring at it will make it one.

    LEVERS (m->l ratios) are computed PAIRED, per seed, then averaged -- a ratio of two means
    throws away the pairing and understates the spread.

USAGE
    python3 scripts/plane_bench.py                       # 5 seeds x {s,m,l}, all cores
    python3 scripts/plane_bench.py -n 8 --tiers m,l
    python3 scripts/plane_bench.py --set ALPHA=1.2e-5    # sweep a global (fits go through HERE)
    python3 scripts/plane_bench.py --load tmp/bench.npz  # re-report a cached run, no compute

COST: jobs are independent processes, so wall clock is ~ the single slowest run (an `l` is
600-1200 s), not the sum. 5 seeds x 3 tiers ~= 20-25 min on this box. It is still not free --
announce it before you run it.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

# One BLAS thread per worker: the parallelism is across seeds, and oversubscribing the box
# makes every run slower without making any run finish sooner.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import plane_grower as G  # noqa: E402

# ── Ground truth ────────────────────────────────────────────────────────────────────────────
# DBH + H are the tier definitions (median measured DBH of the 1595 Central Park planes, and the
# tier's height). Crown radius is UTD's crown DIAMETER for the same tier ages (PSW-GTR-253,
# zone NoEast): 5.2 / 12.6 / 16.9 m, halved.
CENSUS_R = {"s": 2.6, "m": 6.3, "l": 8.45}
OBS = [
    #  key       label            unit  scale(to unit)   census lookup
    ("dbh",   "DBH",              "cm", 100.0, lambda t: G.TIERS[t][1]),
    ("h",     "height",           "m",    1.0, lambda t: G.TIERS[t][0]),
    ("rp50",  "crown r_p50",      "m",    1.0, lambda t: CENSUS_R[t]),
    ("rp90",  "crown r_p90",      "m",    1.0, lambda t: None),
    ("nfol",  "foliage units",    "",     1.0, lambda t: None),
    ("sap",   "sapwood frac",     "%",  100.0, lambda t: 0.50),
    ("FH",    "F_H (heartwood)",  "",     1.0, lambda t: None),
    ("FS",    "F_S (sapwood)",    "",     1.0, lambda t: None),
]


def _one(job):
    """Grow one (tier, seed) and reduce it to scalars. Runs in its own process."""
    tier, seed, overrides = job
    for k, v in overrides.items():
        setattr(G, k, v)
    t0 = time.time()
    H, DBH = G.TIERS[tier]
    g = G.Grower(H, DBH, seed=seed)
    st = g.run(G.TIER_AGES[tier])
    fol = [i for i, nd in enumerate(g.nodes) if nd.alive and nd.foliage]
    P = np.array([g.nodes[i].pos for i in fol], dtype=float)
    r = np.hypot(P[:, 0], P[:, 2])
    return dict(tier=tier, seed=seed, secs=time.time() - t0,
                dbh=2 * float(np.array(st["radius"])[0]),
                h=float(P[:, 1].max()),
                rp50=float(np.percentile(r, 50)),
                rp90=float(np.percentile(r, 90)),
                nfol=float(len(fol)),
                sap=float(st["sap_frac"]),
                FH=float(st["F_H"]), FS=float(st["F_S"]))


def run(tiers, seeds, overrides, jobs):
    work = [(t, s, overrides) for t in tiers for s in seeds]
    # Slowest tier first: the long `l` runs must start at t=0 or they set the wall clock alone.
    work.sort(key=lambda w: -G.TIER_AGES[w[0]])
    recs = []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for rec in ex.map(_one, work):
            recs.append(rec)
            print(f"  [{rec['tier']} seed={rec['seed']}] DBH={100*rec['dbh']:5.1f}cm  "
                  f"r_p50={rec['rp50']:5.2f}m  H={rec['h']:5.2f}m  fol={rec['nfol']:6.0f}  "
                  f"[{rec['secs']:.0f}s]", flush=True)
    return recs


# ── The report ──────────────────────────────────────────────────────────────────────────────
def _stats(v):
    v = np.asarray(v, dtype=float)
    n = len(v)
    sd = float(v.std(ddof=1)) if n > 1 else 0.0
    return v.mean(), sd, 2.0 * sd / np.sqrt(n), n     # mean, sd, half-width (2*SEM), n


def _verdict(mean, half, census, n):
    """Is the residual against census bigger than the instrument's half-width?"""
    if census is None:
        return f"(no census)   +/-{100*half/abs(mean) if mean else 0:.0f}% instr"
    resid = mean - census
    if abs(resid) > half:
        return f"{mean/census:5.2f}x census   ** RESOLVED **  (residual {resid:+.3g} > +/-{half:.3g})"
    # We need 2*sd/sqrt(n_req) = |resid|, and half = 2*sd/sqrt(n)  =>  n_req = n*(half/resid)^2.
    n_req = n * (half / abs(resid)) ** 2 if resid else float("inf")
    req = "never" if n_req > 999 else f"needs n~{n_req:.0f}"
    return f"{mean/census:5.2f}x census   -- noise --   (residual {resid:+.3g} < +/-{half:.3g}, {req})"


def report(recs, tiers, seeds, overrides):
    by = {t: [r for r in recs if r["tier"] == t] for t in tiers}
    n = len(seeds)
    print("\n" + "=" * 100)
    print(f"plane_bench — {n} seeds x {list(tiers)}   ALPHA={G.ALPHA:.4g}"
          + (f"   overrides={overrides}" if overrides else ""))
    print("  RESOLVED = |mean - census| exceeds the instrument's half-width (2*SEM). "
          "Anything else is seed luck.")
    print("=" * 100)

    for t in tiers:
        rs = sorted(by[t], key=lambda r: r["seed"])
        print(f"\n── tier {t}   (age {G.TIER_AGES[t]} yr, {len(rs)} seeds)")
        for key, label, unit, sc, cens in OBS:
            v = np.array([r[key] for r in rs])
            mean, sd, half, nn = _stats(v)
            c = cens(t)
            spread = (v.max() - v.min()) / mean if mean else 0.0
            print(f"   {label:16s} {sc*mean:8.2f} +/-{sc*sd:6.2f} {unit:2s}  "
                  f"[spread {100*spread:4.1f}%]  {_verdict(mean, half, c, nn)}")

    # ── Levers: PAIRED per seed. A ratio of means is not a mean of ratios.
    if len(tiers) > 1:
        print(f"\n── LEVERS (paired per seed)")
        CENSUS_LEVER = {("m", "l"): {"dbh": 71.1 / 43.2, "rp50": 8.45 / 6.3, "h": 22.0 / 14.4},
                        ("s", "m"): {"dbh": 43.2 / 12.7, "rp50": 6.3 / 2.6, "h": 14.4 / 10.0}}
        for lo, hi in [("s", "m"), ("m", "l")]:
            if lo not in tiers or hi not in tiers:
                continue
            print(f"  {lo} -> {hi}")
            for key in ("dbh", "rp50", "h", "nfol"):
                a = {r["seed"]: r[key] for r in by[lo]}
                b = {r["seed"]: r[key] for r in by[hi]}
                lev = np.array([b[s] / a[s] for s in seeds if s in a and s in b and a[s]])
                mean, sd, half, nn = _stats(lev)
                c = CENSUS_LEVER.get((lo, hi), {}).get(key)
                lab = dict(dbh="DBH", rp50="crown r_p50", h="height", nfol="foliage")[key]
                per = "  ".join(f"{x:.2f}" for x in lev)
                print(f"   {lab:16s} {mean:6.3f} +/-{sd:5.3f}   per-seed [{per}]")
                if c:
                    print(f"   {'':16s} vs census {c:5.3f}     {_verdict(mean, half, c, nn)}")

    print("\n  ⚠ A quantity printed `-- noise --` MAY NOT BE THE TELL AN ITERATION TURNS ON.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--seeds", type=int, default=5)
    ap.add_argument("--tiers", default="s,m,l")
    ap.add_argument("--jobs", type=int, default=min(os.cpu_count() or 4, 16))
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VAL",
                    help="override a plane_grower global (e.g. ALPHA=1.2e-5)")
    ap.add_argument("--out", default="tmp/bench.npz")
    ap.add_argument("--load", help="re-report a cached .npz; runs nothing")
    a = ap.parse_args()

    tiers = tuple(a.tiers.split(","))
    overrides = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        assert hasattr(G, k), f"plane_grower has no global {k!r}"
        overrides[k] = float(v)

    if a.load:
        d = np.load(a.load, allow_pickle=True)
        recs = list(d["recs"])
        tiers = tuple(dict.fromkeys(r["tier"] for r in recs))
        seeds = sorted({r["seed"] for r in recs})
        for k, v in d["overrides"].item().items():
            setattr(G, k, v)
        report(recs, tiers, seeds, d["overrides"].item())
        return

    for k, v in overrides.items():
        setattr(G, k, v)
    seeds = [G.SEED + i for i in range(a.seeds)]
    t0 = time.time()
    print(f"plane_bench: {len(tiers) * len(seeds)} runs on {a.jobs} workers "
          f"(tiers={tiers} seeds={seeds[0]}..{seeds[-1]})", flush=True)
    recs = run(tiers, seeds, overrides, a.jobs)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    np.savez(a.out, recs=np.array(recs, dtype=object), overrides=np.array(overrides, dtype=object))
    report(recs, tiers, seeds, overrides)
    print(f"\n  wall {time.time()-t0:.0f}s   cached -> {a.out}   (re-report: --load {a.out})")


if __name__ == "__main__":
    main()
