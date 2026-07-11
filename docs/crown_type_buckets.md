# London Plane — Crown-Type Buckets (adopted)

> **Status:** ADOPTED (Claude's delegated call, 2026-07-06). Defines the crown-form
> bucket scheme for London plane, replacing the size-only s/m/l framing for
> **crown-shape** purposes. **No pipeline code migrated yet** — §4 is a scope note
> only. **By:** Opus 4.8 (1M). Follows `docs/first_mould_leafback_prototype.md`
> (Parts A–D) and its Chris sign-off.

---

## 0. What this decides, and what it doesn't

Chris delegated the bucket call. Using only what was already in hand — the Part A
height/DBH distribution (with its spatial-join caveat), the Part A §5 natural-break
candidates, and the Part C iNat crown-form trend — this doc **adopts a 3-bucket
crown-type scheme** and names the buckets by crown form, not size. It does **not**
migrate any s/m/l-keyed code (§4 sizes that future task); it does **not** touch oak,
generalize the mould method, or reopen any capture work (§5).

---

## 1. Decision: three buckets

**Adopted: 3 buckets, broken at 12 m and 18 m.**

Reasoning, in order of weight:

1. **Crown form changes *shape*, not just scale, across the range — and it does so
   in three legible stages.** The Part C iNat measurement is unambiguous that CP
   open-grown planes progress: young trees are higher-forked, taller-than-wide
   *ovoids*; mature trees are balanced *rounded domes*; veterans are low-forked,
   *wide-spreading* crowns wider than they are tall. That is a genuine morphological
   gradient. A 2-bucket split (Part A §5 break at 15.6 m) would fuse the mature dome
   and the veteran spread — collapsing the single most recognisable "great tree"
   London-plane silhouette (the low-forked wide spread) into the generic dome. Three
   buckets keep it.

2. **Each bucket is anchored by a real measured specimen.** The three clean iNat
   crowns map one-to-one onto the three buckets — `obs75867287` (young ovoid) →
   bucket 1, the built mould's target = `obs75867287`-derived broad dome → bucket 2,
   `obs11670158` (veteran wide spread) → bucket 3. Three form data points is thin for
   *fitting a curve*, but it is exactly right for *pinning three archetypes*: we are
   not interpolating a fourth.

3. **The breaks track the Part A 3-cluster k-means (centres 8.4 / 14.4 / 21.9 m;
   raw breaks 11.4 / 18.1 m).** The join caveat blurs the exact decimals (see the
   prototype doc §6), so the raw 11.4 / 18.1 are rounded to **12 m and 18 m** — clean,
   defensible, and aligned to the height histogram's bin edges (the 12–16 m mode band
   sits wholly inside bucket 2; 18 m is the shoulder where the distribution thins into
   the veteran tail).

4. **All three buckets are well-populated.** Approx shares of the tight-match height
   sample (n≈1054): **bucket 1 ≈ 30 %, bucket 2 ≈ 45 % (mode), bucket 3 ≈ 25 %.** No
   bucket is a rounding-error tail — even the veteran bucket carries ~250 trees, and
   its distinctive form is visually high-value out of proportion to its count.

**Why not 2:** loses the veteran spread (see 1). **Why not 4+:** only three measured
form archetypes exist, and the distribution is unimodal — a fourth break would be
inventing a class the data doesn't show.

### A correction folded in

The task brief characterised the iNat trend as "**clear-bole ratio and aspect ratio
both increasing** with size/age." The measured Part C data shows that for **aspect
ratio** (W/H rises 0.85 → >1.2 with age) but the **opposite for clear-bole fraction**:
it **falls** 0.33 → 0.20 with age, because mature/veteran planes fork *lower* and
spread, not higher. (Absolute bole *height* stays roughly flat — ~4.6 m young vs ~5 m
veteran — as the tree grows taller; it is the *fraction* of total height that drops.)
The buckets below use the **measured** direction, not the brief's parenthetical.

---

## 2. The buckets

Height ranges are the model-selection bounds (a placed tree's height picks its bucket).
Clear-bole fraction and aspect W/H are read off the Part C trend, interpolated/
extrapolated across the three anchor specimens.

| # | Name | Height range | Centre | Clear-bole frac | Aspect W/H | Crown form |
|---|---|---|---|---|---|---|
| 1 | **s tier** | 7 – 12 m | ~10 m | **~0.35** | **~0.80** | Young. High-forked, single straight mottled bole; crown taller than wide, a rounded ovoid pinched at the base. Often the pruned-up young street/lawn plane. |
| 2 | **m tier** | 12 – 18 m | ~14–15 m | **~0.30** | **~1.00** | Mature, and the **modal CP plane**. Balanced rounded dome, roughly as wide as tall, widest near mid-crown. **This is the built leaf-back mould v2** (H 14.4 m, clear-bole 0.30, aspect 1.0). |
| 3 | **l tier** | 18 – 28 m | ~22 m | **~0.20** | **~1.2+** | Old / veteran "great tree". Low fork, heavy near-horizontal low primaries, crown wider than tall and wide-spreading. The hero London-plane silhouette. |

Notes:
- **28 m is the real upper edge.** The Part A height tail past ~28 m (52 m max) is
  nearest-neighbour join artifact, not real trees (prototype doc §2, §6). Bucket 3's
  centre is ~22 m (the k-means centre 21.9), **not** 30 m — see §4 for why that
  matters to the old `_l` tier.
- Clear-bole *fraction* × height gives a near-constant absolute bole (~3.5 m for a
  10 m ovoid, ~4.5 m for a 15 m dome, ~4.5–5 m for a 22 m spread) — consistent with
  the trend being a *shape* progression, not a bole that keeps climbing.
- These envelope numbers are the **leaf-back mould inputs** (target crown volume:
  clear-bole start + aspect + widest-fraction), i.e. the shape the sprig fill packs
  and the skeleton is derived back from. Skeleton depth stays an **output**, per the
  retired depth-cap debate — a lower/broader bucket-3 crown will simply derive fewer
  hops than a bucket-1 ovoid, as v1→v2 already demonstrated (med 6 → 5).

---

## 3. Retiring the "multi-angle / aerial gap"

The open item carried at the end of Parts C–D — *"no specimen from ≥2 crown angles,
zero aerials; distribution characterised but no single volume triangulated"* — is
**retired as a concern. No work is scoped to close it.**

Reason: **leaf-back construction makes per-angle typicality a property of the method,
not of the source photography.** Because the skeleton is *derived from* a filled crown
envelope rather than a jittered skeleton being *imposed* and then hoping it reads right,
a tree built this way is typical-for-species-and-age **from every viewing angle by
construction** — there is no guesswork step for an odd angle to expose. Triangulating
one real specimen from multiple angles would matter if we were *reconstructing that
tree*; we are building a **distribution** of typical crowns, and the envelope
(clear-bole + aspect + widest-fraction) is all the method consumes. Multi-angle/aerial
capture would add cost without changing any input this pipeline reads.

This is in fact one of the core wins of the whole direction: the old trees were
idiosyncratic enough to read as the *wrong* shape for what they were, regardless of
angle; leaf-back has no such failure mode. **Do not reopen aerial/street-view/multi-
angle capture as a task.** (Pointer-retired in the prototype doc and in
`docs/crown_data_audit.md`; see the memory note.)

---

## 4. Migration scope note — s/m/l → buckets (DO NOT execute yet)

> **★ Validated 2026-07-06** — the leaf-back method was run unchanged at both size
> extremes (s tier H10 + l tier H22, plus a 7→28 m edge sweep) and
> generalizes with no parameter fragility or degenerate cases →
> [`docs/leafback_bucket_validation.md`](leafback_bucket_validation.md), **GO for
> migration**. Two tuning inputs carried forward (young bucket wants a *tighter* depth
> range not a shallower one; scale card-thinning for the big bucket's large sprig cloud).

Requested scope-sizing only. **Verdict: the slot *count* maps 1:1, but the
*boundaries, target heights, and per-tier params do not* — and a new crown-envelope
parameter pair has no home in the current schema.** So this is a **re-parameterisation
+ rename of three existing slots plus a small schema addition**, not an add/remove of
tiers. Moderate, not trivial.

**Maps cleanly (1:1, no plumbing change):**
- **Three model slots stay three.** `models/trees/london_plane_{s,m,l}.glb`, the three
  `SPECIES["london_plane"]["tiers"]` entries, the three impostor atlas bakes
  (`bake_impostors.gd` is per species-tier), and the two-boundary `TIER_BOUNDS` /
  `HEIGHT_RANGES` shape all survive as three buckets. No 4th tier to wire, none to
  remove. Rename `s/m/l` → the bucket names (or keep the keys and repoint them).

**Does NOT map cleanly (values must change):**
1. **Boundaries move.** `TIER_BOUNDS["london_plane"] = [13.0, 25.0]` → **[12.0, 18.0]**
   (tree_builder.gd:301). The lower break barely moves (13→12); the **upper break
   drops hard, 25 → 18.**
2. **Old `_m` straddles the new bucket-2/3 break and must split.** The current `_m`
   tier is `height_range [15,25], target_h 22` — that single tier spans **both** new
   m tier (12–18) **and** l tier (18–28), and its target (22 m) actually
   lands in the *new bucket 3*. The old middle tier fractures across two new buckets;
   its `sub_start_radius` (0.45 weld), `card_rule_depth_keep`, and `tier_fraction`
   (0.40) were tuned for one 22 m tree and now have to serve two distinct forms.
3. **Old `_l` shrinks/merges downward.** `_l` is `height_range [25,35], target_h 30`
   with its own v1 `card_rule_depth_keep {1:0.04,2:0.40,3:0.62}` and
   `_LP_V2_L_SUBDENSITY`. But the **real distribution barely reaches 28 m** and bucket 3
   centres at ~22 m — so `_l`'s 30 m tuning is above the real trees. Bucket 3 is closer
   to today's *upper `_m`* than to today's `_l`; the `_l` params need re-tuning **down**
   to ~22 m, not a straight rename.
4. **Old `_s` ≈ new bucket 1, nearly (still not exact).** `_s` is `height_range [7,13],
   target_h 9` with `sub_start_radius 0.7` (the weld-survival fix) and `min_twig_diameter
   {s:0.04}`. New s tier is 7–12, centre ~10 — the closest of the three to a
   straight rename, but the top edge shifts 13→12 and target 9→~10.
5. **NEW crown-envelope params have nowhere to live yet.** Clear-bole *fraction* and
   *aspect W/H* (the table in §2) are the leaf-back mould's inputs and **encode form,
   which the current tiers do not carry at all** — today's `tiers` differ by
   `skeleton_overrides` (size/twig knobs), not by crown-envelope shape. So even where
   height ranges overlap, these two values are net-new fields that must be *authored*
   for all three buckets, not remapped from anything.
6. **v2 card overrides are s/m/l-keyed.** `_lp_set_cards("s"|"m"|"l", …)` and
   `SPECIES["london_plane"]["tiers"]["l"]["skeleton_overrides"]["sub_density"]`
   (generate_trees_mtree.py ~line 667–674) key off the old names — mechanical rename,
   but must move in lockstep with the split in (2)/(3).

**Files the future migration touches:** `tree_builder.gd` (`TIER_BOUNDS`, maybe
`HEIGHT_RANGES` top), `scripts/generate_trees_mtree.py` (the three `tiers` entries +
`_lp_set_cards` block + a new envelope field per bucket), `docs/trees.md` (the tier
spec), and a re-bake of the three impostor atlases after the models regenerate. LOD
*distance* handoff (lod0→impostor, height-scaled ~80 m) is **not** s/m/l-keyed and is
untouched.

**Bottom line for planning:** count-preserving 3→3 rename, **plus** a moved upper
boundary that splits the old middle tier and demotes the old large tier, **plus** two
new form fields authored per bucket. Call it a **medium** migration — bigger than a
rename, smaller than a new subsystem.

---

## 5. Explicitly out of scope (unchanged)

- No aerial / street-view / multi-angle capture (§3 retires the need).
- No s/m/l pipeline migration — §4 is a reasoning note only.
- No oak work; the held oak `_s` weld fix stays parked.
- No generalizing the mould method beyond London plane yet.
