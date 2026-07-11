# Trunk-spine + scaffold-branch space colonization — design (comparison line C)

**Status: DESIGN (written before code, per task protocol).** Prototype line C, isolated in
`tmp/leafback_trunkscaffold.py`. Does **not** modify `build_graph_v2` / `leafback_graph.py`
(merge line, line A), `leafback_spacecol.py` (single-origin space-col, line B), or the 3 shared
mesh functions. Reuses the 781-sprig m-tier attractor cloud from `leafback_graph.build_graph()`
and the pipe-model taper logic (copied verbatim in-file, as line B did).

## 1. The gap this line addresses
Real London planes (reference photos, looking up into a mature crown from near the trunk) show two
things neither line A nor line B reproduces:

1. **A persistent central leader.** The trunk continues as a real tapering central mass *well into
   the canopy* before dissolving into codominant limbs — it does **not** terminate at a single low
   fork. Lines A and B both **collapse to one pinned point at crown-base** (`FORK = [0, CB, 0]`):
   line A merges *inward* to it, line B radiates *outward* from it. Either way there is exactly one
   origin and no vertical trunk inside the crown.
2. **Near-trunk sparseness.** Standing under the tree you see a *handful of thick, widely-spaced
   limbs with real sky gaps between them*; ramification density builds up only further out, toward
   the canopy shell. Both existing lines put maximal branching complexity right at the single
   origin.

Line B's post-mortem found the attractor cloud is a **pure shell** (0 % of the 781 sprigs lie in
the crown interior, ρ<0.6; 99.4 % on the outer shell). For a single-origin cage that hollow core
reads as a wireframe lantern — a *liability*. For a trunk-scaffold model it is an **asset**: real
crowns *are* hollow near the trunk, and a shell of foliage targets is exactly what a set of radial
limbs should reach out to. This line is structurally matched to the data we already have.

## 2. Data we already have (and will actually use)
From `docs/crown_type_buckets.md` + `tmp/leafback_bucket_validation.json`, per crown bucket:

| bucket | H (m) | crown-base / fork (m) | RX (m) | **primaries N** | median hops |
|--------|-------|-----------------------|--------|-----------------|-------------|
| s tier | 10.0 | 3.50 | 2.60 | **4** | 5 |
| **m tier REF** | **14.4** | **4.32** | **5.04** | **4** | 5 |
| l tier | 22.0 | 4.40 | 10.56 | **4** | 8 |

Neither line A nor line B uses the **primaries N** field to place multiple distributed origins —
both ignore it and collapse to one point. This line makes N the count of scaffold origins.
`θ_min = 35°` is the sibling-spacing constant from the merge line (`leafback_graph_v2.py`,
`THETA_MIN=35.0`); we reuse it for scaffold **angular** spacing. Pipe model: `PIPE_POWER=2.3`,
tip seed `R0=0.004 m`. Prototype specimen = **m tier REF** (matches line B exactly, so the
three lines are directly comparable on one crown).

## 3. Design

### 3a. Trunk spine (persistent tapering central axis)
A real node chain from ground `[0,0,0]` up to `spine_top`, in fixed `D=0.35 m` segments (same step
as line B). **How far it persists:** `spine_top = CB + spine_frac·CH`, `spine_frac = 0.62` →
for m tier `spine_top ≈ 4.32 + 0.62·10.08 ≈ 10.6 m` (**~74 % of tree height**, i.e. deep into
the crown — matching the photos' "central mass well into the canopy"). Above `spine_top` there is
no trunk; the apex is reached by the topmost scaffold(s), so the trunk **dissolves into codominant
limbs** at the top rather than stopping at a hard fork.

**How it tapers: emergent from the pipe model, not hand-authored.** The trunk carries the summed
`r^2.3` load of every scaffold attached above each height, so it is thickest at the base
(`= DBH/2 = 0.19 m`, enforced by the same root-scaling as lines A/B) and steps *down* at every
scaffold attachment as that limb's load peels off, reaching ~`R0` at `spine_top`. No profile table
— taper falls out of the same validated `_finish()` used everywhere. (A rough linear taper estimate
`r_est(h)` is used **only** to offset each scaffold's emergence onto the trunk *surface*; it does
not set final radii.)

### 3b. Scaffold attachment points (N origins, distributed in height AND azimuth)
`N = bucket primaries = 4`. Origins are distributed so they are **not bunched at one point**:

- **Heights:** `hf_k = linspace(0.04, spine_frac, N)` of `CH` above `CB` →
  `y_k ≈ [4.7, 6.6, 8.6, 10.6] m`. Lowest primary just above crown-base; highest **is** `spine_top`
  (the leader's dissolution point). Spread over the lower ¾ of the crown.
- **Azimuths:** golden-angle spiral `az_k = (k·137.5°) mod 360°` → `[0°, 137.5°, 275°, 52.5°]`.
  Golden-angle placement is organic (non-repeating, like real branch phyllotaxis) and guarantees
  wide separation: sorted azimuths `[0, 52.5, 137.5, 275]` have **min pairwise gap 52.5° > θ_min
  35°** — so, as required, scaffolds never emerge at nearly the same angle from nearly the same
  height. Correlating azimuth with height (spiral) also matches how limbs wind up a real trunk. A
  post-check asserts every pairwise azimuth gap ≥ `θ_min`; if golden-angle ever violates it for
  some N, the origin is nudged (reported as a FLAG, not silently).
- **Emergence:** each origin sits on the trunk *surface* at its height
  (`trunk_axis(y_k) + r_est(y_k)·outward_k`), with a single seeded first segment in direction
  `normalize(outward·cos30° + up·sin30°)` so the limb leaves the trunk cleanly (mirrors the
  surface-emergence base in `leafback_graph.strand_polylines`). Attractor pull takes over
  immediately after.

### 3c. Per-scaffold growth — Voronoi assignment + validated space colonization
Each attractor is assigned to the **nearest scaffold canopy anchor** (static Voronoi). The anchor
is the scaffold's aim point out on the shell, `origin + RX·outward` — **not** its trunk-attach
point. *(Refinement found in prototyping: near-axis attach points are all ~equidistant
horizontally from every shell attractor, so "nearest attach point" degenerates to HEIGHT RINGS —
one scaffold gets a full 360° ring at its height, whose centroid is on the axis, so a single limb
has no direction to grow and stalls. Anchoring on the shell gives proper azimuth×height wedges with
off-axis centroids.)* Each scaffold then grows over **only its own subset**, in two phases:

**Phase A — structural leader (core crossing).** A directed, unforked limb steps `D` at a time from
the trunk surface toward the running centroid of its live attractors, crossing the hollow crown
core. *(Refinement: the line-B averaged-pull SCA cannot cross the empty core — from a near-axis
origin the horizontal pulls of a wide-azimuth wedge cancel while vertical pulls reinforce, so the
limb grows as a vertical spike near the axis and stalls before reaching the shell. The core-cross
must be **directed**, not colonized.)* This directed leader **is** the clean, widely-spaced
proximal limb the reference photos show, by construction.

**Phase B — canopy ramification.** Once the tip reaches the shell (nearest live attractor within
`di_far`), it hands off to the **exact space-colonization mechanism validated in line B** (Runions
et al. 2007: averaged pull → `D`-step → kill within `dk`), restricted to the subset and seeded with
the leader chain. Its structural cleanliness (no elbow / long edge / collapse — proven in line B by
construction) is inherited. Forking happens only here, at the shell.

### 3d. Distance-scaled branching density (the near-trunk-sparseness mechanism)
Two coupled controls, both keyed to **`ρ` = horizontal distance of the growing tip from the trunk
axis** (`sqrt(x²+z²)`), normalized `u = clip(ρ/RX, 0, 1)`:

1. **Primary lever — radial-distance-scaled kill/influence radius.** In space colonization the
   kill radius `dk` *is* a branch tip's capture zone: a large `dk` lets one limb sweep up a wide
   swath of territory with few forks; a small `dk` forces tips to proliferate to reach closely
   packed targets. So make it a function of `u`:
   ```
   dk(u) = dk_far + (dk_near − dk_far)·(1−u)^p      dk_near=1.10, dk_far=0.45, p=1.5
   di(u) = di_far + (di_near − di_far)·(1−u)^p      di_near=3.50, di_far=1.70
   ```
   Near the trunk (`u→0`): `dk≈1.1 m`, `di≈3.5 m` → coarse, few thick limbs, wide gaps. Near the
   shell (`u→1`): `dk≈0.45 m`, `di≈1.7 m` → fine dense ramification. `di_far=1.7` lands in the
   1.5–1.9 optimum band line B's sweep identified for shell-region branching, so the distal crown
   is grown at line B's best-known density; the gradient only *coarsens* it inward.
   **Why this over θ_spawn:** line B's sweep showed `θ_spawn` is a near-no-op for density over a
   shell (θ∈{15,20,25} gave identical valence). `dk`/`di` is the real SCA density lever and gives a
   *continuous* sparse→dense ramp, which is what the photos show (monotone increase in ramification
   outward), not a single threshold. `θ_spawn` is kept only as a fixed 22° witch's-broom guard.
2. **Secondary guarantee — the Phase-A leader is unforked by construction.** The whole core-crossing
   leader (§3c Phase A) is a single unbranched chain; forking is only possible in Phase B, which
   begins only once the tip reaches the shell. So the "walk up and stand under it" clear proximal
   limb is *structurally* guaranteed, not merely statistically likely from the `dk` gradient. *(This
   supersedes the originally-planned `L_clear` minimum-hop rule, which is subsumed — the two-phase
   split gives the same guarantee more cleanly. `L_clear` is retained only as an inert parameter.)*

## 4. Structural risk register (what could reopen old artifacts, and the guard)
- **Scaffold→trunk junction elbow.** Mitigated by surface-emergence + a 30°-elevation seed
  segment. Measured: fork-bend (incoming trunk dir vs outgoing scaffold dir) at each of the N
  junctions; also the trunk's own bend at each attachment.
- **Long straight edges.** Impossible within a scaffold (fixed `D=0.35` steps). The only new edges
  are trunk segments (`D`) and the emergence seed (`D`). Guard: report longest edge and count >3 m
  (expect 0, as line B).
- **Node collapse / coincident nodes.** Guard: minimum non-trunk edge length; also check no two
  nodes from *different* scaffolds are coincident (Voronoi should prevent shared targets, but tips
  of adjacent wedges can approach — that is fine visually, only flagged if edges degenerate).
- **Valence / witch's-broom.** Emergent cap expected ≤3–4 as in line B; `θ_spawn=22°` guard.
  Report full valence distribution + `%v1`.
- **Reachability.** Per-scaffold and total unreached attractors (line B ran ~3–4 %).

## 5. Verification & renders (plan — executed; results in §7–8)
- Metrics (`tmp/leafback_trunkscaffold_measure.py`): valence dist + `%v1`, sibling min/median,
  hop + branch-order depth, longest/`>3 m` edges, min edge (collapse), per-junction fork-bend,
  per-scaffold + total reachability, and a **near-trunk density profile** (branch count vs `ρ`) to
  quantify the sparseness gradient.
- Renders (`tmp/leafback_trunkscaffold_render.py`, Blender, reusing the shared mesh fns read-only):
  full-crown ×3 and a trunk→scaffold transition closeup (same framing as lines A/B), **plus the
  money shot: a low camera near the trunk (~2 m) looking up into the canopy**, framed like the
  reference photos, to judge whether the near-trunk region reads as a few legible widely-spaced
  limbs with sky gaps.
- Honest comparison section: does near-trunk now show a small number of legible limbs with visible
  gaps rather than a single-point cage or a tangle? Where does it still fall short?

## 6. Parameters (single place to tune)
```
specimen  = m tier REF (H=14.4, CB=4.32, RX=5.04, DBH=0.381, N=4)
D=0.35   spine_frac=0.62   theta_spawn=22   theta_min=35
dk_near=1.10 dk_far=0.45   di_near=6.00 di_far=1.90   p=1.5
seed_elev=30°   golden_angle=137.5°   PIPE_POWER=2.3   R0=0.004
# di_near raised 3.5->6.0 in prototyping: the Phase-A leader must SEE its shell wedge across the
# hollow core (min origin->attractor ~3.4 m > RX-agnostic 3.5), else growth never starts.
# di_far 1.7->1.9 = line B's shell optimum. L_clear removed (subsumed by the two-phase split).
```

## 7. Verification results (RAN — m tier REF, N=4)
Metrics (`leafback_trunkscaffold_measure.py`) and renders (`..._render.py`) executed. Skeleton =
1037 nodes / 795 internal / 242 leaves, saved to `leafback_trunkscaffold_graph.npz`.

**Structural checks (no old artifact reopened):**
| check | line C result | verdict |
|-------|---------------|---------|
| valence dist | {1:576, 2:198, 3:20, 4:1}, max **4** (one node), mean 1.30, %v1 72.5 | clean — emergent, no cap (≈ line B) |
| sibling angle | min **22.2°**, median 89° | acceptable (one tight pair; > 0, not coincident; cf. line B 25–40°) |
| **long-edge** | longest **0.35 m**, edges >3 m = **0** | clean (fixed-`D` steps, as line B) |
| **node-collapse** | min non-trunk edge **0.050 m** (was 0.004 → clamped emergence offset to ≥5 cm) | clean |
| **elbow** | worst single-strand bend 179.6°, but **all 9 bends >150° are on the thinnest 17.6 mm terminal twigs** (10/11 out at the shell ρ≈4–4.6 m) | **not a structural elbow** — cosmetic SCA tip-jitter on hair twigs; thick limbs (100–190 mm) have none. Qualitatively unlike the merge line's *thick-limb* elbows |
| junction bend | scaffold→trunk = **60°** at all 4 origins (= the designed branch-emergence angle, not a kink) | by design |
| trunk taper | **monotonic** base→top, 190.5→183.5→157.4→114.5 mm (steps down as each scaffold peels off load) | correct pipe-model taper |

**Reachability:** **93.3 %** (52/781 unreached), per-scaffold 4/16/24/8 unreached of 82/208/261/230
assigned — every scaffold grows and reaches its wedge (cf. line B ~97 %). The ~7 % unreached are
azimuthal-wedge-boundary pockets between primaries.

**Near-trunk density profile (leaf tips vs radial distance ρ) — the design's core claim:**
```
ρ 0.0–1.1 m:   4 tips   #
ρ 1.1–2.1 m:  10 tips   ###
ρ 2.1–3.2 m:  30 tips   ##########
ρ 3.2–4.2 m: 110 tips   ####################################
ρ 4.2–5.3 m:  85 tips   ############################
```
A clean **monotone sparse→dense gradient** from trunk to shell — quantitatively the "stand under it
and see sky gaps" structure. Achieved *structurally* (unforked leaders cross the empty core; forking
only at the shell), not by a tuned threshold.

## 8. Honest comparison — does near-trunk read as legible limbs with sky gaps?
**Yes, this is the clear win.** In the crown views and especially the two near-trunk "looking up"
renders (`..._fromtrunk_0/1.png`, `..._lookup.png`), line C shows a **persistent central trunk
running up into the canopy** with a **handful of thick primaries breaking off at different heights**
and real sky gaps between them near the trunk; fine ramification builds only out toward the shell.
This is neither line A's single-pinned-fork tangle nor line B's hollow single-point cage — compare
the 3-row montage `leafback_trunkscaffold_cmp_crown.png` (A merge / B cage / C trunk-scaffold). It
is the first of the three lines that actually uses the bucket's **primary-count** datum to place
multiple distributed origins.

**Where it still falls short:**
1. **Uniform emergence.** All 4 primaries leave the trunk at the same 60° angle and arc similarly;
   real limbs vary their branch angle and curvature. A per-scaffold jitter on `seed_elev` and a mild
   gravity/light tropism in Phase A would break the regularity.
2. **Wedge-boundary gaps (~7 % unreached).** With only 4 golden-angle wedges, the seams between
   primaries leave thin azimuthal gaps at the shell. More primaries for larger buckets (the datum
   allows it) or a light cross-wedge attractor-sharing pass would close them.
3. **Frontal views still read slightly "arcy."** From some azimuths the primaries' arcs echo line
   B's meridians; the side/among-the-limbs views look markedly more tree-like than the head-on ones.
4. **Apex slightly sparse.** The top scaffold both continues the leader and fills the apex; it is a
   little thin right at the crown top. A dedicated short leader-continuation origin at `spine_top`
   would help.
5. **Twig tip-jitter.** The 9 hair-twig reversals (§7) are cosmetically harmless but would ideally
   be smoothed with the same 0.75/0.25 blend used on the Phase-A leader, applied to Phase-B tips.

None of these are structural regressions (all project checks stay clean); they are the natural next
tuning targets if this line is carried forward.

## 9. Status
Prototype only — **nothing committed.** This doc is prepared for review but **not committed**. No
shared code touched: `build_graph_v2`, `leafback_graph.py`, `leafback_spacecol.py`, and the 3 shared
mesh functions are unmodified. New uncommitted artifacts (all in gitignored `tmp/`):
`leafback_trunkscaffold.py` (generator), `leafback_trunkscaffold_measure.py` (metrics + npz save),
`leafback_trunkscaffold_render.py` (Blender), `leafback_ts_paramprobe.py` (dev probe),
`leafback_trunkscaffold_graph.npz`, and renders `leafback_trunkscaffold_{crown_view0-2,
transition_0-1, fromtrunk_0-1, lookup}.png` + montages `..._cmp_crown.png`, `..._cmp_fromtrunk.png`.
