# First Mould — Leaf-Back Construction Prototype (London Plane)

> **Status:** PROTOTYPE + DATA PULL. One specimen built. No code in the s/m/l
> pipeline touched, no crown-type boundaries locked. Awaiting Chris's sign-off
> before generalizing. **Date:** 2026-07-06 · **By:** Opus 4.8 (1M).
> **Scope:** Part A = real CP London plane height/DBH distribution; Part B = one
> concrete leaf-back mould to validate the "crown-in, skeleton-derived" approach.

---

## Part A — Real CP specimen distribution

### 1. Species matching (reported exactly, per file)

The two data files name trees **completely differently**, and only one carries
species at all:

| File | Species field? | London-plane key matched | Count |
|---|---|---|---|
| `central_park_trees.json` | yes — `"Genus species - common name"` | **`"Platanus x acerifolia - London planetree"`** | **1564** |
| `6m_trees_central_park.json` | **NO** — only `{x,z,h,a}` | (cannot filter by species) | — |

Related keys found in `central_park_trees.json` (kept **separate**, not merged
into the 1564):

- `Platanus x acerifolia 'Bloodgood' - 'Bloodgood' London planetree` — 39
- `Platanus x acerifolia 'Columbia' - 'Columbia' London planetree` — 22
- `Platanus x acerfolia 'Exclamation' - 'Exclamation' London planetree` — 30  ⚠ note the misspelling *acer**f**olia* in the source; the columnar 'Exclamation' cultivar is an atypically narrow form (matches the nursery ref in the crown audit)
- `Platanus occidentalis - American sycamore` — 14 *(distinct species, excluded)*

**The `a` field in `6m_trees` is not a species code.** Its values run 1…30+ with
a smooth decaying frequency, and mean height rises monotonically with it
(a=1→10.3 m, a=12→17.7 m) — it behaves like an age / canopy-cluster index, not a
taxon. So `6m_trees` **cannot be filtered to London plane on its own.**

### Consequence: DBH is native, height requires a spatial join

- **DBH** — present per-tree in `central_park_trees.json` (in inches). Native.
- **Height** — only in `6m_trees` (`h`, metres), which has no species. To get a
  *London-plane* height distribution I projected the 1564 census points into the
  project's world frame (`convert_to_godot.py` `project()`: `REF_LAT 40.7829`,
  `REF_LON −73.9654`, `MLAT 110540`, `MLON ≈84264`) and did a **nearest-neighbour
  join** to `6m_trees`. Join QA: NN distance **median 2.37 m, p90 5.1 m**; **1060
  of 1564 (68%) within 3 m**. Heights below are reported both ways; the
  distribution is stable across them (median 14.1–14.5 m), so the join is sound.
  ⚠ Caveat: a matched height is the nearest *canopy* point, which may be a
  neighbouring tree — treat as distributional truth, not per-tree truth.

### 2. Height and DBH distributions (n = 1564 London plane)

**DBH (inches)** — native, n=1535 non-zero (29 zeros):
`min 1 · median 15 · max 50`

```
 0– 6 in | 219  ██████████████
 6–12 in | 217  ██████████████
12–18 in | 509  █████████████████████████████████   ← mode
18–24 in | 366  ████████████████████████
24–30 in | 157  ██████████
30–40 in |  57  ███
40–50 in |  10
```

**Height (m)** — spatial-join, tight matches ≤3 m, n=1060:
`min 2.3 · median 14.1 · max 52.4` (the 52 m tail is a bad/long NN match, not real)

```
 0– 8 m |  99  ████████████
 8–12 m | 217  ███████████████████████████
12–16 m | 363  █████████████████████████████████████████████   ← mode
16–20 m | 216  ███████████████████████████
20–24 m | 126  ███████████████
24–28 m |  27  ███
28–35 m |   7
35–60 m |   5   (join artifacts)
```

**Condition** (from census): Good 801 · Fair 402 · Dead **211** · Poor 61 ·
Unknown 58 · Excellent 28 · Critical 3. The 13.5% dead share is high — expected
for an aging census, and dead trees were excluded from the shape analyses below.

### 3. `nyc_trees.csv` — does it cover CP interior trees? **No.**

Full-file point-in-polygon test against `central_park_boundary_osm.json`
(1,106,281 rows scanned): **only 179 points fall inside the park polygon** (33
London plane), and those are almost all along the four transverse cross-roads and
the park edge (`TPStructure`: 169 Full, 5 Stump, 5 Retired). Compare
`central_park_trees.json`: **20,107 interior trees, 1564 London plane.**

**Verdict, plainly:** `nyc_trees.csv` is the **citywide street-tree census —
street plantings only**. It captures <1% of CP interior trees. Its
`TPStructure` / `TPCondition` fields are **not usable** for CP interior
specimens. (This closes the one check requested; no further pollarding pursuit.)

### 4. Short + thick outliers (flag only, no investigation)

Flagging trees short-for-their-girth (low height ÷ DBH — the storm-topped /
pollarded signature). Threshold: DBH ≥ 20 in **and** height/DBH(m) < 15. **3
specimens**, alive, tight-matched. **Height is join-derived, so each outlier's
own NN match distance is shown** (see §6 caveat — a large match distance means
the "signature" could be a mismatched adjacent tree, not verified either way):

| height | DBH | h/DBH | match dist | vs. median (2.37 m) | condition | lat, lon |
|---|---|---|---|---|---|---|
| 5.7 m | 30 in | 7.5 | **1.60 m** | within median (28th pctile) | Fair | 40.79608, −73.96744 |
| 8.0 m | 34 in | 9.3 | **2.84 m** | ⚠ in tail (63rd pctile) | Good | 40.79685, −73.97388 |
| 8.1 m | 24 in | 13.3 | **1.26 m** | within median (18th pctile) | Good | 40.79917, −73.96611 |

The strongest signature (30-in bole, 5.7 m tall — textbook topped/storm/pollard)
matched at **1.60 m, comfortably within the median offset**, so for that one the
join is *not* the likely culprit — still unconfirmed, but not a mismatch artifact.
The **8.0 m / 34-in** tree matched at **2.84 m, in the tail** of the offset
distribution: its short-for-girth reading **could be a mismatched join rather than
a real short tree, and has NOT been verified either way.** All 3 **flagged for
later — not chased.**

### 5. Proposed natural breaks (proposal only — NOT locked in)

Height is unimodal, centred ~14 m. 1-D k-means on the tight-match heights
(n=1054, h≥3 m) suggests:

- **2 buckets** — break at **15.6 m** (centres 11.4 / 19.8 m)
- **3 buckets** — breaks at **11.4 m and 18.1 m** (centres 8.4 / 14.4 / 21.9 m)

The dominant cluster either way is the **middle band (~12–18 m, centre 14.4 m)** —
that's where most CP London planes live, and what the prototype below is built to.
These are data-derived clusters, **not** a young/mature/old scheme, and are
offered for discussion only. As you noted, tiering may want to wait until more
moulds are built.

### 6. Caveat — spatial-join reliability (folded in per sign-off 2026-07-06)

The height figures throughout Part A are **not native**. `6m_trees_central_park.json`
has no species field, so every London-plane height was obtained by a
**nearest-neighbour join** from the census points to the 6m-trees canopy points.
Match quality: **NN offset median 2.37 m, p75 3.25 m, p90 5.10 m; only 1060/1564
(68%) within 3 m.** That means **roughly a third of the height values are matched
at a distance where the nearest canopy point could plausibly be an *adjacent,
different* tree** rather than the same specimen — most acutely in dense grove
areas (Ramble, North Woods) where crowns are packed tighter than the offset.

This is a **flag, not a defect to fix** (join deliberately not re-run). It bears on
exactly two downstream claims:

1. **Bucket breaks are approximate** — the distribution *shape* is trustworthy, the
   exact break decimals (15.6 m; 11.4 / 18.1 m) are blurred by join noise (see §5).
2. **The 3 short+thick outliers are plausible but unconfirmed** — each outlier's own
   match distance is now in §4. The strongest (5.7 m / 30 in) sits at 1.60 m (within
   median → join not the likely culprit); the 8.0 m / 34 in sits at 2.84 m (in the
   tail → could be a mismatched join, **not verified either way**).

Per-tree match distances are dumped to **`tmp/lp_height_join.csv`** (`lat, lon,
dbh_in, condition, height_m, match_distance_m`) so this is inspectable per-specimen,
not only in aggregate, next time distribution work touches this data. (The
single-specimen `tmp/leafback_stats.json` carries a `_join_caveat` summary pointing
to that CSV.) **No action taken beyond flagging.**

---

## Part B — One mould, leaf-back construction

**Reference status checked first** (per `docs/crown_data_audit.md`): usable
whole-crown reference is **thin** — effectively 2 trusted single-angle photos
(`A149-03_hero_l.jpg` broad rounded dome; the CP `…nyc11.jpg` tall vase→spreading
on a high mottled bole), no multi-angle/aerial coverage, iNat pull not yet run.
Sufficient to **sanity-check** a crown shape, not to reconstruct one. So the
target volume here is a **broad open-grown rounded dome** consistent with those
two references and the Part-A dimensions — explicitly a stand-in until the iNat
multi-angle pull closes the gap.

### Representative specimen (from the mode bucket)

- Height **14.4 m** (centre of the dominant 12–18 m band)
- DBH **15 in = 0.381 m** (the DBH mode/median)
- Clear bole to **5.3 m** (~37% — London plane's characteristic high mottled bole)
- Crown 5.3→14.4 m, half-width 5.3 m (width ~10.6 m, W/H_crown ≈ 1.16), widest at
  ~55% up — a broad, base-pinched ovoid dome.

### a. Fill — sprig-card placement points

The **sprig card = the existing 4-leaf twig unit** (not a bare leaf; matches
`_sprig_cards()` in `generate_trees_mtree.py`, `london_plane_cluster.png`).
Cards were packed on the **crown shell** (surface + 1.3 m inward depth — foliage
rides the outside, interior stays open) by dense surface sampling + greedy
min-distance thinning at **0.65 m** spacing (the `card_rule_spacing` regime).

→ **809 sprig cards**, each with position **and an outward twig normal** (the
crown-surface normal = the direction the 4-leaf sprig opens away from the trunk).
Dump: `tmp/leafback_sprigs.xyz` (x y z nx ny nz). Plan + elevation:
`tmp/leafback_sprig_cloud.png` (even shell, base-pinched dome).

### b. Connect — leaf-back, NOT trunk-outward

Starting from the 809 sprigs, nodes were **merged agglomeratively** toward the
trunk: each level bins active nodes into a grid whose cell grows ×1.55 per level;
all nodes in a cell fuse to **one parent** at their centroid, pulled toward the
trunk axis and down toward the fork (pull strengthens with level). Singletons
carry up unchanged (their chain simply lengthens). No fixed depth is imposed —
the funnel runs until few nodes remain, which are then wired to the trunk fork.

```
809 sprigs
  └► L0 (cell 1.30 m) → 263 twigs
       └► L1 (2.02 m) → 82 branches
            └► L2 (3.12 m) → 30
                 └► L3 (4.84 m) → 10
                      └► L4 (7.50 m) → 6
                           └► L5 (11.6 m) → 4 primaries
                                └► fork @ 5.3 m ──► ground (bole)
```

**Emergent hop count (sprig → trunk): median 6, range 2–6, mean 5.84.** This was
**derived, not set** — it fell out of the merge geometry. **4 primaries** leave
the trunk fork, which is botanically plausible for a broad-domed plane.

> ✅ **This retires the skeleton-depth debate** (`docs/tree_skeleton_depth_redesign.md`;
> Hard-Law `skeleton_max_depth = 2`; the depth-3 spec drafted earlier). Sign-off
> 2026-07-06: **depth is not a parameter to set — it is an output that varies per
> specimen and per sprig.** Leaf-back merging of this real-scale 14 m crown *derived*
> a median of 6 hops (range 2–6) from where the foliage actually sits; a taller/broader
> crown or a denser fill will derive a different number, and individual sprigs within
> one tree already range 2→6. Any future proposal to "cap depth at N" is answering the
> wrong question — the cap is an emergent property of crown size × fill density × merge
> geometry, not a knob. Note this wherever the depth-cap question resurfaces.

### c. Scope

This is **one concrete specimen**, not a system. No parameters were generalized,
no arbitrary-tree tooling built; the script (`tmp/leafback_mould_prototype.py`)
is a single-run prototype, deliberately in `tmp/`.

### Visual output

- **`tmp/leafback_mould_wire.png`** — wireframe, oblique + front-on. Skeleton
  coloured trunk-dark → twig-light; sprig cards as green dots. Reads as a tree:
  primaries fan from the fork, funnel out through branches/twigs to a coherent
  ovoid foliage shell.
- **`tmp/leafback_sprig_cloud.png`** — sprig cloud, plan + elevation.
- **`tmp/leafback_sprigs.xyz`**, **`tmp/leafback_stats.json`** — numeric dumps.

---

## What this validates / what it doesn't

**Validates:** the leaf-back direction is workable end-to-end — a target crown
volume can be filled with real 4-leaf sprig cards and a plausible trunk-connected
skeleton *derived by merging inward*, with hop count emerging from the geometry
rather than being imposed.

**Does not yet establish:** (a) the crown shape is a reference stand-in, not a
reconstructed CP volume — the iNat multi-angle pull (crown audit §"Optional next
step") should precede any real mould; (b) tuning of merge radius / trunk-pull vs.
real branch topology (the `…branch_structure.jpg` from-below scaffold ref is the
check); (c) nothing here is wired into Godot or the s/m/l pipeline.

**Recommended next step (for sign-off):** run the iNat *Platanus* CP-bbox pull
for 2–3 mature open-grown specimens at ≥2 angles, rebuild this one mould against a
real crown outline, and only then discuss crown-type buckets. **Stopping here per
the task's step-6 boundary.**
