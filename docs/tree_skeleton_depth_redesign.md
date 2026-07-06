# Tree Skeleton-Depth Redesign — reference-driven, starts 2026-07-06

**Status: SPEC DRAFTED 2026-07-06 — awaiting Chris's approval before ANY generation code.**
Steps 0–3 below are complete (source-verified depths, reference research, budget
cross-reference, numeric design spec). The recommendation is a **uniform
`skeleton_max_depth = 3`** across every tier of both species, with card compensation
specified per tier. Nothing is built yet. Supersedes the "just tune
`sub_start_radius`/density knobs" approach — that treated a symptom of a deeper structural
issue.

**One open decision for Chris (§Step 3d):** depth **3** (recommended, reference- + card-system-
grounded, = Chris's own evolved oak_s position) vs depth **2** (the literal Hard Law 4 in
`tree_skeleton_plan.md` §1b). The spec recommends formally superseding Hard Law 4's "= 2" with
"= 3"; that supersession needs Chris's ratification.

## Why this exists — the finding that triggered it (2026-07-06)

While porting the london_plane weld-cull fix (`137f286`, `sub_start_radius`) to oak `_s`, we
checked `skeleton_max_depth` across species and inspected the **actual generated mesh** (not
just config), deterministic regen at the existing seed:

- **`skeleton_max_depth` consuming code** (`scripts/generate_trees_mtree.py:4410`):
  `sp_tier.get("skeleton_max_depth")` with **no default** → returns `None` when the key is
  absent; guarded by `if _max_depth is not None:` so an absent key means **the ramification
  cap is never applied** (no numeric fallback; "no-op when unset").
- **london_plane `_s` and `_m`: NO `skeleton_max_depth` key set → UNCAPPED.** Mesh histogram
  (`hierarchy_depth × radius`) confirms both ramify all the way to **depth 8**:
  - LP `_s`: depths 0–8 present (d3=1285, d4=555, d5=156, d6=67, d7=17, d8=3 verts); no
    ramification-cap line emitted.
  - LP `_m`: depths 0–8 present (d3=5478, d4=4652, d5=2776, d6=810, d7=185, d8=22 verts); no
    cap line.
- **oak `_s`: `skeleton_max_depth: 3` → CAPPED.** Histogram tops out at depth 3 (0:384, 1:503,
  2:529, 3:404); cap line emitted: *"depth ≤ 3, 1132 verts removed beyond tertiary."*
- **oak `_m`/`_l`: UNCONFIRMED — needs the same mesh-histogram check** (config vs actual).

### Why this matters
- The original design intent was **"no ramification beyond secondary"** (Chris). LP `_s`/`_m`
  were approved/gated while silently ramifying to **depth 8** — an **unintended** configuration.
- The woodland perf investigation measured bark at **~90–97%** of the tree GPU cost, and the
  `137f286` isolation attributed the s/m density regression to *"~90% denser BARK geometry."*
  Deep ramification (depth 4–8) is expensive bark geometry. The depth-8 config and the bark
  cost are plausibly the same phenomenon — **to be characterised in this redesign, not assumed.**

## The approach Chris wants (NOT trial-and-error)

**No regen-and-eyeball parameter tuning.** This is reference-driven and designed as one spec
before any code changes:

1. **Study real tree branching structure** (per species where it matters — plane/oak differ).
   How many branch orders does a real crown carry as *woody structure* vs *foliage*?
2. **Derive what depth is silhouette-load-bearing** (the woody skeleton the eye reads at
   gameplay distance) **vs. what should be card-carried foliage** (the fine outer crown that a
   leaf card should paint, not real ramified geometry).
3. **Cross against the RTX 3060 Ti budget** (`docs/rendering.md` §4: camera raster 4.0 ms,
   shadow 1.0 ms; deep woodland ≥45 fps floor). What depth can we afford, park-wide, at the
   real 6808-tree count?
4. **Design skeleton depth + card-fill compensation TOGETHER as one spec** — if we cap depth,
   the card layer must compensate for the lost outer-crown fill so the silhouette holds. Depth
   cap and card rule are a coupled pair, decided jointly, then implemented once.

## Current state / what's on hold (as of 2026-07-06)

- **oak `_s` `sub_start_radius: 0.7` fix**: complete + measured (Gate sheet `tmp/oak_s_gate_AB.png`;
  raw born verts 3480→4168 +20%, final 2920→3049 +4.4%, depth-3 twig verts +19.5%, bare
  branches 17→14). **Source edited but NOT committed** — held pending this redesign, because oak
  `_s` may itself be affected by whatever depth/card spec comes out of it.
- **LP `_s`/`_m` are now SUSPECT** — approved/gated under the unintended depth-8 config; **do not
  treat as a finalized baseline** until this redesign resolves.
- No code changed for the redesign yet. `generate_trees_mtree.py` still has the uncommitted oak
  `_s` edit only.

---

# Step 0 — actual `skeleton_max_depth`, verified from `scripts/generate_trees_mtree.py`

Re-checked directly from source (the working assumptions were wrong more than once, so this
is the ground truth, not a recollection):

| Species | `_s` | `_m` | `_l` |
|---|---|---|---|
| **london_plane** | **UNCAPPED** → mesh depth 8 (no key; L1803–1894) | **UNCAPPED** → depth 8 (no key; L1910–1939) | **`= 4`** (L1954) |
| **oak (red)** | **`= 3`** (L872) | **UNCAPPED** (no key; L873–874) | **UNCAPPED** (no `skeleton_overrides` at all; L875) |

Mechanics: `hierarchy_depth` 0=trunk · 1=primary · 2=secondary · 3=tertiary · … `cap_skeleton_depth()`
deletes verts with `depth > max_depth`; absent key → `.get()` returns `None` (L4410) → cap skipped
= uncapped. The template block (L744, `= 3`) is the copy-me default, not a live species.

**The current config violates Hard Law 4** (`tree_skeleton_plan.md` §1b: "orders = trunk + primary
+ secondary ONLY … `max_depth = 2` … supersedes the `_l = max_depth 4` rule") on **every tier** —
LP `_l` sits at 4, LP `_s`/`_m` and oak `_m`/`_l` are uncapped, oak `_s` at 3.

**Precision finding from the mesh histograms** (`_s`/`_m` measured; `_l`/oak from the length-scaling
law): the depth-8 tail is **negligible on `_s`** (LP `_s` carries only ~800 verts total beyond depth 3,
tapering to 3 verts at d8) but **substantial on `_m`** (LP `_m` carries ~8,400 verts at depth 4–8,
≈ half the crown mass). Ramification depth grows ~exponentially with limb length (Mtree forks
per-segment), so uncapped `_l` runs to depth 11. **⇒ The over-ramification is genuinely an `_m`/`_l`
problem; `_s`'s prior approval is NOT meaningfully compromised by depth** — `_s`'s real defect was the
separate weld-cull sparsity (the `sub_start_radius` fix), not deep ramification.

---

# Step 1 — Reference research (real-world branching structure)

Full report + citations in the session log; load-bearing findings:

**The decisive result is exact and species-independent — foveal acuity (1 arcmin):**

| Viewing distance | resolution floor (1′) | reads as a distinct line (~3′) |
|---|---|---|
| 15 m | **4.4 mm** | 13 mm |
| 30 m | **8.7 mm** | 26 mm |
| 50 m | **14.5 mm** | 44 mm |

A real 5 mm twig at 30 m subtends 0.57′ — **below the resolution limit; it cannot be seen as an
individual branch, it merges into mass.** It only reaches the 1′ floor at ~17 m.

**Real diameter-by-order (mature broadleaf):** trunk 300–1200 mm · order-1 primary 100–300 mm ·
order-2 secondary 30–100 mm · **order-3 tertiary 10–30 mm** · order-5–8 fine twig 2–6 mm.
Cross with the acuity table: **at ≥30 m only orders 0–2 (≥~9 mm) resolve as structure; order-3 is
borderline (near-field only); order-4+ (≤~10 mm) is always foliage mass.** Total realistic ceiling
≈ **8 woody orders** (TLS/QSM ground truth); **"ramifying LOD0 geometry past order ~4–5 has no visual
payoff."**

**Structural (silhouette-bearing) orders per species — all four resolve to orders 0–2:**

| Species | Architecture (Hallé–Oldeman) | Structural orders | Structure→foliage transition | Card-pattern implication |
|---|---|---|---|---|
| **London plane** | **Massart** — few **bold high forks**, plagiotropic horizontal tiers | 0–2 (~3–6 bold limbs) | order 2→3, ~10 mm | **tip-biased** (Massart galleries) — matches LP's `{1:.05, 2:.60, 3:1.0}` |
| **Pin oak** | Rauh (Pfisterer: Massart) — excurrent leader + 3 tiers | 0–2 | order ~3, 10–20 mm | along-branch tiers |
| **Red oak** | **Rauh §I candelabrum** — stouter, **denser even ramification**, "dense crown surface, hollow interior" | 0–2 (+part 3) | order 3–4, 15–25 mm | **along-branch** — matches oak's `{1:.30, 2:.85, 3:1.0}`; **keep `_l` DENSE, not parsimonious** |
| **Turkey oak** | Rauh §II (Malus) — straight upswept limbs, polyarchic when old | 0–2 | order 3, 10–20 mm | along-branch |

**Two conclusions that drive the spec:**
1. **Orders 0–2 are the silhouette for every species.** Order 3 is the *transition* order — a real
   woody order, marginally resolvable only in the near field. Order 4+ has no visual payoff and is
   exactly the geometry the leaf card already paints. This is the reference basis for capping at the
   tertiary twig and card-carrying everything beyond.
2. **Plane genuinely differs from the oaks architecturally** (Massart few-bold-forks vs Rauh
   even-ramification) — but that difference lives in the **card placement pattern** (tip-biased vs
   along-branch, already correct in config) and **crown shape** (already per-tier), **NOT in the depth
   cap.** The depth budget (structural orders 0–2 + one transition order) is the same for all four.

*Honesty flag (state it downstream):* no source publishes a per-species "branch-order count" or a
twig-mm→distance threshold. Those are interpolated from architecture theory + QSM order ceilings +
the acuity math. Solid & cited: architectural-model assignments, crown form, the ~8-order ceiling, and
the acuity calculation (exact).

---

# Step 2 — Budget cross-reference (and the premise correction)

**The premise that launched this effort — "bark = 90–97 % of tree GPU cost → deep ramification is the
woodland-perf problem → capping depth is a big fps win" — does NOT survive the measured data.** Naming
the conflict, per the ground rule:

- **"Bark = 79–97 %" is bark's share of TRIANGLE / VERT COUNT, not of frame time** (`trees.md` §4b:
  LP_l 151 k verts, 79 % bark). The "~90 % denser bark" figure was the *geometry* delta of the `_m`
  density regression, not a frame-time share.
- **The woodland frame is fragment-bound, not geometry-bound.** `--render-scale=0.5` = −25 ms, but
  `--tree-mesh-range` (dropping distant mesh geometry) = only −5/−3/−4 ms — *"tier pull-in is DEAD as a
  perf lever … vertex load was never binding at 1080p on this GPU"* (`trees.md` §4a/§4f).
- **Skeleton density is a measured ~2–5 ms lever that does NOT move the woodland floor.** The LP `_m`
  trade50 (backing off ~50 % of skeleton density) *"saves a genuine but modest ~2–5 ms bark-geometry
  amount — it does NOT move this number. The bottleneck is structural, not skeleton density"*
  (woodland-perf memory, CLOSED). That floor is a separate, already-resolved structural problem
  (splits2 + fade025 adopted, `640b2c2`).

**⇒ Depth-capping cannot be sold as the deep-woodland fps fix.** It is justified — and the justification
is real — on three *other* grounds:

1. **Correctness.** Match the intended skeleton architecture (Step 1: structure = orders 0–2 + one
   transition order) instead of an unintended depth-8/11 runaway. This alone justifies the work.
2. **Cluster-count / overdraw — the one place it touches the binding bottleneck.** The per-branch card
   rule places ≥1 card per eligible branch, so deep ramification **silently inflates leaf-card count**,
   and **leaf overdraw IS the dominant fragment cost.** Capping depth removes the depth-4+ branches
   *and the redundant cards they carry* (those cards are redundant-by-construction with the depth-3 tip
   cards). Fewer cards → less canopy overdraw. Effect is real but single-digit-ms, concentrated on
   `_m`/`_l`.
3. **Build / disk / memory.** Uncapped LP `_l` = depth-11, ~9.5 k clusters, **53 MB GLB.** Capping is a
   large asset-size and build-time win.

**Affordable depth, per tier:** the cap of 3 is affordable everywhere — it is scale-appropriate *by
construction*. The same `max_depth = 3` removes ~nothing from `_s` (negligible d4-8 tail), ~half the
crown mass from `_m` (the d4–8 haze), and the deepest runaway from `_l` (d4–11) — i.e. it bites exactly
where over-ramification exists and is a near-no-op where it doesn't. **No botanical-vs-budget conflict at
depth 3:** Step 1 says orders 0–2 + a thin transition order is all that reads; the budget says
everything past that is redundant card-painted geometry. Botany and budget agree.

---

# Step 3 — Design spec (numeric; no code yet)

## 3a. Skeleton depth — the target

**`skeleton_max_depth = 3`, uniform across `_s`/`_m`/`_l` for BOTH species.**

- Orders 0–2 (trunk + primary + secondary) = the silhouette-load-bearing scaffold (Step 1: resolvable
  as structure at all gameplay distances).
- Order 3 (tertiary) = one **thin transition-twig order** that (a) is marginally visible only in the
  near field (<40 m) and (b) gives the leaf cards real terminal tips to sit on and fill *between*
  secondaries — the "card-masked twig order" Chris already endorsed for oak `_s` ("the ban is on heavy
  tertiary FORKS, not card-twigs").
- Orders 4–8/11 = pruned. Zero visual payoff (Step 1), redundant with the card (Step 2), and the bulk of
  the GLB/cluster cost.

This unifies the current mess (LP `_s`/`_m` = 8, LP `_l` = 4, oak `_s` = 3, oak `_m`/`_l` = uncapped) to
one principled value. **Tiers do NOT need different depths** — the length-scaling of natural ramification
means one cap removes proportionally more from bigger tiers automatically, which is the correct behavior.
Age/size differentiation stays where it already lives: crown shape (`variant_spans`), card density
(`tier_fraction`), and spacing.

## 3b. Skeleton role vs. card role (the coupled pair)

**Skeleton carries:** the silhouette envelope — trunk, primary scaffold count/angle, secondary spread,
and one thin tertiary twig order for cards to anchor to. Crown *width* and *shape* are skeleton jobs.

**Cards carry:** the entire foliage-mass shell — everything the acuity math says is texture, not
structure (order 3+ visually). Because the card system's `card_rule_depth_keep` is already built around a
`{3: …}` terminal key and cards only ride branches ≤ `card_rule_max_radius` (5 cm radius), **the card
layer was already designed for a depth-3-terminated crown.** Capping the currently-uncapped tiers at 3
therefore removes only the *card-redundant* depth-4+ order; the silhouette-bearing depth-3 tip cards
remain. This is why depth 3 (not 2) is the low-risk target: no card-system redesign is required, only the
per-tier compensation below.

## 3c. Per-tier spec — explicit numbers

`sub_start_radius` = the held/deferred weld-cull fixes (`tree-pipeline-lessons.md`), folded in here
because depth-3 keeps the thin twig order those fixes rescue, so they ship together. Card params default
to the species-level values unless a change is listed.

| Tier | `skeleton_max_depth` | `sub_start_radius` | `card_rule_depth_keep` | other card change | expected effect |
|---|---|---|---|---|---|
| **LP `_s`** | **8 → 3** | 0.7 (already set) | `{1:.05, 2:.60, 3:1.0}` unchanged | none | removes ~800 verts (negligible); crown preserved. Confirms `_s` was never a depth problem. |
| **LP `_m`** | **8 → 3** | 0.45 (already set) | `{1:.05, 2:.60, 3:1.0}` unchanged | none (contingency: 2:.60 → **.70** only if the post-cap shell reads thin — see gate) | removes ~8,400 redundant-card verts + their cards; shell held by d3 tip cards. Real cluster/size win. |
| **LP `_l`** | **4 → 3** | — | `{1:.04, 2:.40, 3:.62}` → `{1:.04, 2:.40, 3:**.75**}` | keep `card_half_factor 1.00`, `spacing 0.72` | one order removed; the removed d4 shell-share folded into a denser d3 keep so the parsimonious `_l` crown holds. |
| **oak `_s`** | **3 (no change)** | 0.7 (uncommitted → **commit**) | `{1:.30, 2:.85, 3:1.0}` unchanged | none | already correct; this spec *ratifies* it and ships the held weld fix. |
| **oak `_m`** | **uncapped → 3** | none → **0.45** (deferred port, add) | `{1:.30, 2:.85, 3:1.0}` (inherited) unchanged | none | caps the unconfirmed d4+ tail (likely ~LP_m scale); weld port fills the milder ~34 % cull band. |
| **oak `_l`** | **uncapped → 3** | — | `{1:.30, 2:.85, 3:1.0}` (inherited) unchanged — **stays DENSE, not parsimonious** | none | biggest single geometry win (uncapped dense-card big crown); dense surface kept per red oak's Rauh-§I "dense crown surface, hollow interior". |

**Card-fill compensation rule (how the numbers were derived, not eyeballed):** the removed depth-4+
branches were, by the card rule, clad at the max-key keep (1.0 for LP `_s`/`_m` and all oak; 0.62 for LP
`_l`). Those cards are geometrically redundant with the depth-3 tip cards on the same strands, so for the
`{3:1.0}` tiers **no compensation is needed** (the shell is already fully clad at d3). Only LP `_l`, whose
d3 keep is a deliberately-thin 0.62, needs the removed-order's shell-share folded in → **0.62 → 0.75**
(conserves the pre-cap outer-shell clad-branch count at the parsimony the `_l` crown was approved at).

## 3d. The one decision for Chris — depth 3 vs Hard Law 4's depth 2

Hard Law 4 (`tree_skeleton_plan.md` §1b, Chris 2026-06-22) is literal: `max_depth = 2`, "no tertiary."
This spec recommends **formally superseding it with `= 3`**, because:

- **Chris's own later position is already depth-3-with-thin-tertiary.** Depth-2 was empirically found to
  give "beads on a string / long bare secondaries / see-through crown" on both oak `_s` and LP `_s`;
  Chris revised oak `_s` to 3, defining order-3 as "a SUB-VISIBLE thin twig order masked by cards … the
  ban is on heavy tertiary FORKS, not card-twigs." That *is* the depth-3-with-banned-heavy-forks rule.
- **The card system needs order-3 tips** (its `depth_keep {3:…}` key and 5 cm-radius card gate); depth-2
  forces cards onto bare secondaries, which bunch inboard / float.
- **Step 1 supports it:** order 3 is a real woody order and the near-field transition structure, not an
  invention; orders 4+ are what "no ramification beyond structure" should actually forbid.

**Alternative (depth 2)** honors the letter of Hard Law 4 and Step 1's "orders 0–2 = structure" boundary,
at the cost of a card-system retune (raise d2 keep, tighten spacing, widen apex band to hold the shell on
bare secondaries) and re-litigating the "beads on a string" failure. Recommend **depth 3**; the
supersession of Hard Law 4's "= 2" is Chris's call.

## 3e. Build order & verification (when approved — still no code until then)

One deterministic regen per tier (existing seeds), **no regen-and-eyeball loop.** Per tier, at build:
1. Print the `hierarchy_depth × radius` histogram (the `[diag]` block already emits it) to confirm the
   cap landed at 3 and to read the exact d3 clad-branch count.
2. Gate the silhouette on the **SILHOUETTE / card-fill classifier** (never on green — `project_impostor_card_erosion`
   lesson): post-cap crown-fill must be ≥ the pre-cap approved fill for LP `_s` (preservation) and within
   the approved parsimony band for LP `_l`; oak `_m`/`_l` gate against the oak `_s` approved density.
3. Rebake impostor atlases for any tier whose lod0 silhouette moved (`--bake-impostors`, ≥2400 s timeout;
   `tree-pipeline-lessons.md`) — LP `_m`/`_l` and oak `_m`/`_l` will move; LP `_s` likely byte-stable.
4. `perf_gate.sh ×5` at the dense woodland poses — expect a modest cluster/size reduction, **not** a
   woodland-floor move (Step 2); do not chase fps here.

Relates to: `docs/trees.md` (tier spec / budgets, top banner), `docs/tree-pipeline-lessons.md` (weld-cull
+ ramification-depth lessons), `docs/tree_skeleton_plan.md` §1b (Hard Law 4 — to be amended on approval),
`docs/tree_model_redesign.md`. Memory: `project_oak_pipeline` (held oak `_s`/`_m` fixes),
`project_london_plane_sm_skeleton_fix`, `project_woodland_perf_investigation`.
