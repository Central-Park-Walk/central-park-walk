# s/m/l → Crown-Type Bucket Migration

> **Status:** CONFIG LANDED (commit `75979d2`) + **REGEN PHASE STOPPED FOR REVIEW.**
> The §6 config was approved and landed. Regenerating the retargeted meshes then
> surfaced **two findings that block the "verify distinct forms" step** — reported in
> §8. Impostor re-bake and live-sim verify were **not run** (stopped on the "if
> anything looks off, don't push through" rule). **Date:** 2026-07-06 · **By:** Opus
> 4.8 (1M). Follows [`crown_type_buckets.md`](crown_type_buckets.md) §4 and
> [`leafback_bucket_validation.md`](leafback_bucket_validation.md).
>
> **★ READ §8 FIRST** — the LOD-budget lever (`tier_fraction`) is **inert for London
> plane**, and the regenerated crowns are **old parametric shapes scaled**, not the
> new bucket forms, because the leaf-back mould is not yet wired into generation.
> §0–§6 below are the (still-valid) config plan; §8 is what actually happened on run.

---

## 0. The one decision that must be made first: rename vs. repoint

The task says "rename the s/m/l tier keys to the three bucket names throughout the
codebase." Investigation shows a **literal global rename is the wrong move**, and
`crown_type_buckets.md` §4 already licensed the alternative ("*or keep the keys and
repoint them*"). The evidence:

1. **`s/m/l` is a shared, species-wide structural schema, not a London-plane thing.**
   `TIER_BOUNDS` and `HEIGHT_RANGES` key all **17** species on `s/m/l`; `TIERS :=
   ["s","m","l"]` is global; every species' models are `{species}_{s,m,l}.glb`. The
   bucket names (Upright Ovoid / Broad Dome / Low-Forked Spread) are **London-plane
   crown forms** — they are meaningless for oak, elm, willow, etc. Renaming the shared
   keys would mis-label 16 other species.
2. **The runtime recovers the species name by string-splitting the tier suffix.**
   `species_tier` strings like `london_plane_m` are split back with
   `mesh_key.substr(0, mesh_key.rfind("_"))` (tree_builder.gd:1071, 1233, 1605). This
   only works because the tier is a **single trailing token with no underscore**. A
   name like `Upright Ovoid` (space) or `upright_ovoid` (underscore) **breaks the
   parse** — `rfind("_")` would split `london_plane_upright_ovoid` at the wrong place.
3. **Every baked asset is filename-coupled to `_s/_m/_l`:** 3 `.glb` + their embedded
   texture PNGs, ~40 impostor atlas PNGs (`london_plane_{s,m,l}_*`), all `.import`
   sidecars, and the manifest keys (`"london_plane_s|m|l"`). A rename means renaming
   and re-importing all of them for zero functional gain.

**Recommendation (for review): KEEP `s/m/l` as the structural tier keys; attach the
bucket identity as London-plane-only metadata.** Concretely: `s → Upright Ovoid`,
`m → Broad Dome`, `l → Low-Forked Spread`, recorded as a `crown_buckets` block on the
`london_plane` species entry that carries each slot's **name + clear-bole + aspect**,
and repoint each slot's `target_h` / `height_range` / `TIER_BOUNDS`. This satisfies the
migration's intent (buckets drive LP's boundaries, targets, and form) with a **1:1 slot
remap and no cross-species breakage**. The literal-rename alternative is documented
here only as the rejected option and its cost.

Everything below assumes the **repoint** approach. If review prefers a literal rename,
the touch-point list in §1 is still the complete set — it just grows the asset-rename
and `rfind` refactor work.

---

## 1. Complete enumeration of touch-points

Every place `s/m/l` keys London-plane tier config or the shared tier machinery. **✎ =
edited under repoint; ⟳ = regenerated asset (post-review); ✓ = unchanged under repoint,
would change only under a literal rename.**

### A. Generation config — `scripts/generate_trees_mtree.py`
| # | Location | What it holds now (LP) | Migration action |
|---|---|---|---|
| A1 | `SPECIES["london_plane"]["tiers"]["s"]` | `target_h 9, height_range [7,13]`, skeleton_overrides (`sub_start_radius 0.7` weld, `sub_density 1.7`, `skeleton_max_depth 3`) | ✎ retarget to Upright Ovoid: `target_h 10, height_range [7,12]`; params carry (see §3) |
| A2 | `…["tiers"]["m"]` | `target_h 22, height_range [15,25]`, `sub_start_radius 0.45`, `sub_density 1.14` | ✎ retarget to Broad Dome: `target_h 15, height_range [12,18]` — **big drop, see §2** |
| A3 | `…["tiers"]["l"]` | `target_h 30, height_range [25,35]`, `card_rule_depth_keep {1:.04,2:.40,3:.62}` | ✎ retarget to Low-Forked Spread: `target_h 22, height_range [18,28]` — **big drop, see §2** |
| A4 | `…["tier_fraction"]` | `{"l":1.0, "m":0.40, "s":0.18}` | ✎ LFS (`l`) pull — **see §5 LOD budget** |
| A5 | `…["min_twig_diameter"]` | `{"s":0.04}` | ✓ keyed by slot; carries (Upright Ovoid keeps the 4 cm sapling floor) |
| A6 | `_LP_V2_S/M/L_DEPTH_KEEP`, `_LP_V2_S/M/L_SPACING`, `_LP_V2_L_SUBDENSITY` (lines 2201–2207) | per-slot v2 card overrides | ✎ values re-tuned to new targets; **keys stay s/m/l** |
| A7 | `_lp_set_cards("s"/"m"/"l", …)` + `…["tiers"]["l"]["skeleton_overrides"]["sub_density"]` (2218–2221) | applies A6 to slots | ✓ mechanical; keys stay s/m/l |
| A8 | **NEW** `SPECIES["london_plane"]["crown_buckets"]` | — (does not exist) | ✎ add: name + clear-bole + aspect per slot (§3) |
| A9 | `DEFAULT["tiers"]`, `DEFAULT["tier_fraction"]`, `DEFAULT["card_rule_depth_keep"]` | shared schema defaults | ✓ untouched — other species rely on them |

### B. Runtime tier selection / LOD — `tree_builder.gd`
| # | Location | Now | Action |
|---|---|---|---|
| B1 | `TIER_BOUNDS["london_plane"]` (:301) | `[13.0, 25.0]` | ✎ **`[12.0, 18.0]`** (§2) |
| B2 | `HEIGHT_RANGES["london_plane"]` (:216) | `[9.0, 32.0]` | ✎ tighten top to `[9.0, 28.0]` (real ceiling; §2) |
| B3 | `TIERS := ["s","m","l"]` (:309); `_get_tier` (:336) returns `"s"/"m"/"l"`; suffix build `"_"+_get_tier(...)` (:857); `tier_list/tier_suffixes = ["_s","_m","_l"]` (:569, :650) | slot keys | ✓ unchanged under repoint (would be the rename blast radius) |
| B4 | `rfind("_")` species recovery (:1071, :1233, :1605) | parses `species_tier` | ✓ safe under repoint; **breaks under literal rename** (§0.2) |
| B5 | `_species_real_h`, `_species_meshes`, `_species_heights`, impostor mesh dict — all keyed `species+"_"+tier` | `london_plane_{s,m,l}` | ✓ unchanged under repoint |

### C. Baked assets (regenerate post-review, after A/B land)
| # | Asset | Action |
|---|---|---|
| C1 | `models/trees/london_plane_{s,m,l}.glb` (+ embedded cluster/leaf PNGs, `.import`) | ⟳ **regenerate** at new targets (10/15/22 m) — the current `.glb`s are baked at 9/22/30 m and are now stale |
| C2 | `textures/impostors/london_plane_{s,m,l}_*` (~40 files) + `london_plane_manifest.json` | ⟳ **re-bake** impostor atlases from the regenerated `.glb`s (per `lessons_impostor_bake`: one Godot per species, ~6 min/tier, timeout ≥2400 s) |

### D. Eval / diagnostics — `eval_plot_builder.gd`
| # | Location | Now | Action |
|---|---|---|---|
| D1 | `STAND_ROWS` (:97–99) | `["_s",10],["_m",22],["_l",30]` | ✎ heights → `10 / 15 / 22` to match new targets |
| D2 | `force_tier` tagging (:284, :313), `DEFAULT_EVAL_SPECIES`, TIER_MATCH garden | tier strings `s/m/l` | ✓ slot keys unchanged under repoint |

### E. Not touched (verified)
`hud_manager.gd` (perf HUD reads MMI counts, not tier keys), `main.gd` (LOD overlay is
lod0/impostor distance-based, not slot-keyed), `park_loader.gd`, `bake_impostors.gd`
(iterates whatever tier list tree_builder hands it — no hardcoded LP names). `docs/trees.md`
tier spec ✎ (doc update to reflect buckets, same commit as A/B).

**Total code/config files edited under repoint: 3** (`generate_trees_mtree.py`,
`tree_builder.gd`, `eval_plot_builder.gd`) + `docs/trees.md`. **Assets regenerated: 2
sets** (3 `.glb`, ~40 impostor files). No shared-schema or cross-species changes.

---

## 2. TIER_BOUNDS move + old-tier reassignment

**`TIER_BOUNDS["london_plane"]`: `[13.0, 25.0]` → `[12.0, 18.0]`.** Lower break barely
moves (13→12); the **upper break drops hard, 25→18**. Effect on model selection:

| Slot | Selected height range (new bounds) | Old `target_h` | New `target_h` |
|---|---|---|---|
| `s` = Upright Ovoid | h ≤ 12 m | 9 | **10** |
| `m` = Broad Dome | 12 < h ≤ 18 m | 22 | **15** |
| `l` = Low-Forked Spread | h > 18 m | 30 | **22** |

**How the existing authored 22 m and 30 m content is reassigned — stated explicitly:**

- **Old `_m` (target 22 m) does NOT survive as Broad Dome content.** 22 m now falls in
  the **Low-Forked Spread** band (>18 m), not Broad Dome (12–18). So slot `m` is
  **retargeted down to ~15 m** (the Broad Dome centre, which is exactly what the
  validated v2 mould was built at — H 14.4). Old `_m`'s skeleton parameters
  (`sub_start_radius 0.45`, `sub_density 1.14`, v2 card overrides) carry forward as
  **starting values**, but the 22 m `.glb` is **superseded** and slot `m` regenerates
  at 15 m. The "bigger-tree" character old `_m` encoded at 22 m informs the new
  **Low-Forked Spread**, not the new Broad Dome.
- **Old `_l` (target 30 m) is reassigned DOWN to Low-Forked Spread (~22 m).** The real
  distribution ceiling is ~28 m (the 30 m target sat above real trees; `crown_type_buckets.md`
  §1). Old `_l`'s params (`sub_density 0.35`, `card_rule_depth_keep {1:.047,2:.47,3:.78}`,
  `card_rule_spacing 0.85`, `tier_fraction 1.0`) carry as starting values but are
  **re-tuned to 22 m**; the 30 m `.glb` is **superseded**.

**Net:** no authored tier is deleted, but **neither slot `m` nor slot `l` maps cleanly
onto one new bucket** — both retarget downward and both `.glb`s regenerate. Parameter
*values* carry as seeds; `target_h` / `height_range` / form fields change. This is the
"medium migration" from `crown_type_buckets.md` §4, confirmed.

---

## 3. New form fields per bucket (from `crown_type_buckets.md` §2)

Add `crown_buckets` to the `london_plane` species entry (A8). Values are the adopted,
validated ones — **no new numbers invented here:**

| Slot | Bucket name | `clear_bole_frac` | `aspect_wh` | `target_h` | `height_range` |
|---|---|---|---|---|---|
| `s` | Upright Ovoid | **0.35** | **0.80** | 10 | [7, 12] |
| `m` | Broad Dome | **0.30** | **1.00** | 15 | [12, 18] |
| `l` | Low-Forked Spread | **0.20** | **1.20** | 22 | [18, 28] |

These are the leaf-back mould's envelope inputs (fork height = `clear_bole_frac·H`;
crown half-width = `aspect·CH/2`). They have **no current home** in the tiers schema —
today's tiers differ by `skeleton_overrides` (size/twig knobs), not crown-envelope
shape — so they are net-new authored fields, not remapped from anything.

**Upright Ovoid depth note (required scope §3):** the mould validation showed the young
bucket's hop **median is 5 — same as Broad Dome — with a *tighter range* (3–5 vs 2–6)**,
not a lower median. So **no shallower depth is authored for slot `s`.** Its existing
`skeleton_max_depth 3` (A1) is retained; if any depth-adjacent knob is expressed
per-bucket it should encode a *tighter* spread, never an artificially shallow cap.
(This is a "do-not-do" for the migrator, recorded so the tighter-range finding isn't
mis-read as "make the young tree shallow.")

---

## 4. Upright Ovoid — no other extreme-scale surprises

The 7 m floor of the smallest bucket produced 92 sprigs / 4 balanced primaries / hops
4 (2–5) with no degeneracy (validation §edge sweep). Slot `s`'s card saturation
(`_LP_V2_S_DEPTH_KEEP {1:.12,2:.85,3:1.0}`, `tier_fraction 0.18`, `card_size_floor 0.42`)
is already tuned for a small crown that must not go see-through, and carries forward
unchanged. **No adjustment required for the small extreme.**

---

## 5. LOD budget check — Low-Forked Spread (required scope)

### 5a. Reconcile the two figures
The 2865 and 4556 numbers are **not contradictory — they are different heights, and
the profile barely matters:**

| build | H | profile | aspect | sprigs |
|---|---|---|---|---|
| test specimen (bucket **centre**) | 22 | spread (low-widest) | 1.20 | **2865** |
| edge-sweep **ceiling** | 28 | *dome* (mid-widest) | 1.25 | 4556 |
| ceiling, **apples-to-apples** | 28 | spread (low-widest) | 1.25 | **4590** |
| ceiling, spread, W/H 1.20 | 28 | spread | 1.20 | 4410 |

Re-running the ceiling with the **correct spread profile** gives ~4590 (vs the sweep's
dome-profile 4556) — a ~1 % difference. **The driver is height (22→28 m), not profile.**
So: **centre ≈ 2865, ceiling ≈ 4590.** A per-bucket LOD budget must bound the **ceiling**
(the biggest trees placed in the 18–28 m band carry the most cards), while the centre is
the representative build.

### 5b. Implied LOD0 card count vs. current budget
Current LP LOD0 card counts (from the `_LP_V2` config comments — these are
**config-comment estimates**, to be re-measured when generation is wired): `_m ≈ 1450`,
`_l ≈ 2686`. Under the mould, foliage-card demand ≈ raw sprig count (a sprig *is* a
4-leaf card), scaled by `tier_fraction`:

| LFS build | raw | ×1.0 (inherit `l`) | ×0.60 | vs current `_l` (~2686) |
|---|---|---|---|---|
| centre H22 | 2865 | 2865 | 1719 | ×1.0 ≈ parity |
| **ceiling H28** | 4590 | **4590** | **2754** | **×1.0 = 1.7× over budget** |

### 5c. Conclusion — adjustment IS needed (direction certain, magnitude gated on a real count)
At the inherited `tier_fraction l:1.0`, Low-Forked Spread is **≈ parity with the old `_l`
budget at its centre but ~1.7× over at its 28 m ceiling** — exactly the heavy tail the
validation flagged. **So yes: this bucket must pull harder than `l:1.0`.**

- **Recommended target: `tier_fraction["l"] ≈ 0.60` for London plane** (holds the 28 m
  ceiling at ~2754 ≈ the established `_l` budget; centre lands ~1719, sensibly between
  today's `_m` and `_l` for a 22 m tree). `card_rule_depth_keep` order-3 could take the
  finer trim if needed (LFS's wide crown has more order-3 twig surface).
- **Honest caveat — do not apply blind:** the mould is **not yet wired into
  generation**, so "raw sprig × fraction" is a *predictive* budget, not a measured
  pipeline count. The `_m ≈ 1450 / _l ≈ 2686` baselines are config-comment estimates.
  The **direction (pull below 1.0) and rough magnitude (~0.55–0.65) are certain**; the
  exact value must be **confirmed by counting actual LOD0 cards** on a regenerated
  Low-Forked Spread `.glb` before it ships. That measurement is part of the
  post-review generation step, not this config plan.
- This is **tuning on an existing parameter for one bucket**, consistent with the
  validation's framing — not a method gap and not a silent change (the number and its
  basis are stated here for review, not applied).

---

## 6. Proposed final config (for review — NOT applied)

```
# tree_builder.gd
TIER_BOUNDS["london_plane"]  = [12.0, 18.0]      # was [13.0, 25.0]
HEIGHT_RANGES["london_plane"] = [9.0, 28.0]      # was [9.0, 32.0]  (real ceiling)

# generate_trees_mtree.py — SPECIES["london_plane"]
tiers["s"]: target_h 10, height_range [7,12]     # Upright Ovoid  (was 9 / [7,13])
tiers["m"]: target_h 15, height_range [12,18]     # Broad Dome     (was 22 / [15,25])
tiers["l"]: target_h 22, height_range [18,28]     # Low-Forked Spread (was 30 / [25,35])
tier_fraction: {"l": 0.60, "m": 0.40, "s": 0.18} # LFS pull 1.0→0.60 (§5, confirm by card count)
crown_buckets: {                                  # NEW form fields (§3)
  "s": {name:"Upright Ovoid",     clear_bole_frac:0.35, aspect_wh:0.80},
  "m": {name:"Broad Dome",        clear_bole_frac:0.30, aspect_wh:1.00},
  "l": {name:"Low-Forked Spread", clear_bole_frac:0.20, aspect_wh:1.20},
}

# eval_plot_builder.gd
STAND_ROWS heights: 10 / 15 / 22                  # was 10 / 22 / 30
```

Post-review order: (1) land config A/B/D + doc; (2) regenerate 3 `.glb` at new targets;
(3) **count actual LOD0 cards on the LFS build, confirm/adjust the 0.60**; (4) re-bake
impostor atlases; (5) verify in the eval garden, then the park. **Steps 2–5 are the
"run against live trees" phase this report stops before.**

---

## 7. Config land (DONE — commit `75979d2`)
Approved §6 config landed across 3 files + this doc: `tree_builder.gd` (TIER_BOUNDS
`[12,18]`, HEIGHT_RANGES top `28`), `generate_trees_mtree.py` (LP tiers retargeted
s 10 / m 15 / l 22, `crown_bucket` metadata added per tier), `eval_plot_builder.gd`
(STAND_ROWS 10/15/22). `crown_bucket` verified inert to the current generation path
(tier cfg is read by explicit keys only). Then the gated regen phase was run — see §8.

---

## 8. Regeneration findings (STOP-and-report — the verify phase cannot pass yet)

Ran `blender4 … generate_trees_mtree.py -- --species london_plane --tier {m,l}
--no-fork-test` on the landed config. Two findings, both material, both exactly what
the "count the actual cards / verify the forms" gate exists to catch.

### Finding 1 — `tier_fraction` is INERT for London plane; the LOD-budget lever was wrong
**Measured `_l` (Low-Forked Spread, target 22 m): 774 leaf clusters** (`h=26.3 m,
w=3.2 m`, seed 300). `_m` (Broad Dome, target 15 m): **190 clusters** (`h=16.2 m,
w=3.0 m`). Neither is near the report's ~2686 baseline / ~2754 prediction — because
**that whole budget arithmetic used the wrong lever and the wrong card population:**

- **LP is on the card-per-branch RULE path, not the distribute path.** LP sets
  `distribute_tiers: []` (the comment at L718 literally calls the alternative "the dead
  3D-leaf path") and `card_leaf_rule: True`. Its card count comes from the RULE
  function (prints `card per-branch (RULE): N clusters across M branches`), governed by
  **`card_rule_depth_keep` + `card_rule_spacing` + skeleton branch count**. That
  function **never reads `tier_fraction`.**
- **`tier_fraction` is only read at L2521**, inside the foliage-DISTRIBUTE path
  (`target_count = target_l × tier_fraction[tier]`) — which LP disables. So
  **`tier_fraction["l"] 1.0→0.60 has zero effect on LP's LOD0 card count.** Verified:
  the `_l` regen produced 774 clusters; it would be 774 at either value.
- The report's §5 arithmetic (raw mould-sprig × tier_fraction ≈ cards) was doubly
  mis-premised: the mould sprig cloud is **not** the wired card population (the RULE
  path is), and `tier_fraction` is **not** LP's card scaler.

**Action taken:** reverted `tier_fraction["l"]` to `1.0` with a comment recording the
finding (it is a proven no-op, and the 0.60 comment's justification was false — leaving
it would be misleading, not honest). This is **not** a silent re-tune to hit a number:
no number was forced, an ineffective change was removed and documented. **LP's real
card lever is `_LP_V2_L_DEPTH_KEEP {1:0.047, 2:0.47, 3:0.78}` + `card_rule_spacing`** —
if Low-Forked Spread's card budget ever needs pulling, that is the knob, and it should
be set against a **measured** count, not the mould prediction. With the retarget alone
(30→22 m, a shorter tree = fewer branches), `_l` already dropped to 774 clusters.

### Finding 2 — regenerated crowns are OLD parametric shapes scaled, NOT the bucket forms
The `crown_bucket` fields (`clear_bole_frac`, `aspect_wh`) are **inert** — the Mtree
skeleton generation reads none of them. So the shape is still the old parametric
candelabra, only scaled to the new target height:

- **Measured skeleton width is clamped ~3.0–3.2 m** for both tiers (`_m` w=3.0, `_l`
  w=3.2), i.e. skeleton aspect ~0.12. This is a **known pre-existing Mtree limitation**
  (L863 comment, 2026-06-24: *"crown width is clamped ~3.3m by Mtree crown/gravity
  internals — crown_base_size, up_attraction, branch_angle & length all proved ~no-op
  on measured width"*). The foliated crown reads a bit wider than the skeleton bbox
  (cards over-hang), but **nowhere near the Low-Forked Spread's aspect 1.2 wide spread.**
- The `_l` thumbnail (`models/trees/thumbnails/london_plane_l.png`) confirms it visually:
  a **narrow, high-forked upright oval on a clean bole** — the old form, shorter. Not a
  low-forked, wide-spreading veteran.

**Consequence:** step 6 ("verify Broad Dome and Low-Forked Spread read as intended
distinct forms, not reversions to old idiosyncratic shapes") **cannot pass on the
current generation path.** The bucket *identity* is now attached (metadata, boundaries,
targets), but the bucket *forms* require the **leaf-back mould to be wired into
generation** — which the migration report §0/§5 explicitly scoped as future work, not
part of this config migration. Regenerating now yields old-form trees at new heights.

### What was and wasn't done, and the recommended next move
- **Kept:** the landed config (§7) and the regenerated `_m`/`_l` `.glb`s — they are
  **height-correct for the new bounds** (a 15 m `_m` model now fits the 12–18 m slot;
  previously a 22 m model served it), an interim improvement even with old crown form.
- **Reverted:** `tier_fraction["l"]` → 1.0 (Finding 1).
- **NOT done (deliberately stopped):** impostor re-bake (step 5) and live-sim verify
  (step 6). Re-baking would bake the old form; the lod0 meshes (new height) and the
  **stale impostor atlases (old height/form) now mismatch** — so **do not run LP in the
  live sim until either the impostors are re-baked or the mould-wiring lands.**
- **Recommended next task (the real form delivery):** wire the leaf-back mould
  (`tmp/leafback_bucket_validation.py` machinery) into `generate_trees_mtree.py` so
  `crown_bucket` actually drives the crown envelope, then regenerate → measure cards
  (real lever = `card_rule_depth_keep`) → re-bake → verify. That is the step that makes
  the buckets visible; this config migration is its prerequisite, now in place.

**This is a genuine stop point, not a failure of the migration** — the config half is
sound and landed; the run surfaced that the form half depends on the (separately
scoped) mould wiring, and that the report's LOD lever was the wrong one. Reporting both
before touching anything further, per the gate.

### Out of scope (unchanged)
- No oak work (held oak weld fix parked). No new buckets / boundary changes. No
  re-running the leaf-back validation. No silent tuning — every number here is measured
  and stated with its basis.
