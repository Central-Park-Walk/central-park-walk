# Tree & Leaf Production Pipeline — Standing Brief for Claude Code

**Status:** canonical working agreement. Suggested home: `docs/tree-leaf-pipeline-brief.md`.
**Owner of all design calls:** Chris. This brief defines *how* to work; Chris decides *whether* a result is acceptable.

> **⮕ GEOMETRY-SOURCE DECISION SETTLED (2026-06-22).** This brief's *process* — dossier
> first, two hard human gates, evidence-over-assertion, the gameplay-distance bar, the
> lessons loop — stands unchanged and is canonical. But the leaf **representation** is
> settled and is NOT the parametric leaf *mesh* this brief originally assumed:
> **leaves = real-photo CLUSTER CARDS** (see `tree-pipeline-lessons.md` top banner and
> [[project-leaf-pipeline-mtree]]). Read "archetype leaf" in Phase 2 below as *a
> real-photo cluster card per leaf-type + the attach/placement contract*, not a
> parametric base mesh. Render budget killed the mesh path (~460 M tris/frame for
> structural leaves on a 3060 Ti); leaf shape only resolves <30 m, so a card's alpha
> silhouette carries identity and the shader carries seasonal color.

---

## Purpose

We are overhauling every tree in the park. Leaves are the hard, reference-driven part; tree models are comparatively simple assembly. This brief decouples the two and runs leaf production as a documented line, so quality is repeatable and the work gets faster over time.

Three phases, run in order:

1. **Gather** all data that could be useful, across every species in the roster.
2. **Build the archetype leaf library** — a small set of parametric base leaves plus a fixed attach contract.
3. **Build the trees**, one species per session, in priority order.

The roster and tier order live in the species build roster (Tier 1 Essential → Tier 2 Richness → Tier 3 Accent). Build in tier order.

---

## Operating principles

These carry the DNA of our existing working agreements. They are not optional.

- **Investigate before you build. Measure twice, cut once.** No geometry is created or tweaked until the species is fully understood *in writing*. Understanding is a deliverable (the dossier), not a feeling.
- **Evidence before "done."** A claim that an asset matches reference must be backed by a side-by-side comparison, not an assertion. No speculation before evidence — the same rule we use on bugs.
- **Self-iterate to satisfaction, then stop and hand off.** Claude critiques its own output against reference and iterates until it genuinely cannot improve it further. *Then* it stops at a human gate. Claude does not advance past a gate on its own.
- **Two hard human gates.** (1) Chris reviews every leaf before it goes on a tree. (2) Chris reviews every tree in the eval area before the next species begins. These are full stops. Claude requests review and waits.
- **The gameplay distance is the bar, not the 1:1 hero render.** A leaf is not "good" because it looks perfect against a herbarium photo. It is good when it survives instancing, the full LOD chain, and AgX lighting at the distances players actually stand. This mirrors the manual smoke-test loop: the real environment is the only quality bar that counts.
- **The line improves itself.** Every species produces lessons-learned. When a lesson is systematic, it is folded back into the archetype library or the skill so the next species benefits. Skill at making realistic, budget-conscious trees should be visibly higher at species #20 than at species #2.
- **Budget-conscious by default.** Fidelity is spent where players can see it. Detail invisible at gameplay distance is wasted VRAM on a constrained card. When in doubt, cheaper.

---

## Phase 1 — Gather all useful data

Goal: a per-species **dossier** that contains everything needed to model the species without going back to the source mid-build. No modeling begins until a species has a complete dossier.

### Dossier contents (per species)

- **Archetype mapping** — which leaf archetype this species belongs to, and the specific parameter deltas from the archetype base (lobe depth, lobe/leaflet count, margin/serration, length:width ratio, tip sharpness, petiole length, surface texture).
- **Leaf morphology** — blade shape, venation pattern (only to the level that *reads* at near distance), margin detail, surface (smooth / waxy / pubescent), adaxial vs abaxial color difference if relevant.
- **Seasonal color states** — spring (new growth / flower), summer (mature foliage mass color), fall (the color that says "this species"), and winter where it matters (e.g. beech marcescence — coppery leaves held through winter).
- **Whole-tree silhouette** — crown form and proportion (spreading, vase, columnar, weeping, conical), since silhouette is what reads at LOD distance.
- **Bark** — character and color, for near-field LOD0.
- **Signature features** — distinctive fruit, flower, or habit (sweetgum gumballs, horse chestnut flower spikes) where they contribute to recognition.
- **Prominence & location** — where this species lives in the park and how close players get to it. This sets the fidelity tier (see Budget). The Mall elms and Reservoir cherries are stood-under; a back-corner specimen is passed at distance.

### Sources and the honest measurement standard

Claude cannot measure a physical leaf, and arbitrary web photos carry no scale. So:

- Prefer **botanical line drawings** and **herbarium specimens**, which frequently include scale bars.
- Extract **proportional** measurements, not absolute ones — length:width, lobe depth as a fraction of blade length, teeth per unit of margin. Proportions transfer to any target size; invented millimeters do not.
- **Cite the source** for each species' key measurements in the dossier.
- Where reference is **ambiguous or conflicting, say so** in the dossier rather than inventing precision. Flagged uncertainty is information; false confidence is a future rework.

### Phase 1 output

- One dossier file per species (suggested: `references/leaves/<species>.md`).
- The master roster annotated with archetype mapping and fidelity tier for every species.

> The dossier is *available* for Chris to review if he wants to catch a misunderstanding cheaply, before any geometry exists. It is not a mandatory gate, but offering it is encouraged for Tier 1 species and for the first member of each archetype.

---

## Phase 2 — Build the archetype leaf library

> **Superseded representation (see top banner):** an archetype's leaf is a **real-photo
> cluster card** (a 2–4-leaf twig sprig — leaves + stems + a joining twig — cut to RGBA;
> hard law 2), not a parametric base *mesh*.
> The parametric-mesh framing below is retained for the *attach/placement contract* it
> defines (still load-bearing), but item 1 ("parametric base mesh") is replaced by "a
> real-photo cluster-card texture per leaf-type, with seasonal variants".

An **archetype** is not one leaf. It is:

1. a **parametric base mesh** that morphs across its whole group on parameters alone, and
2. the **fixed attach contract** every leaf in the group honors.

Target ~10–12 archetypes total (palmate lobed, pinnate lobed, simple elliptical, cordate, simple entire, variable/mitten, compound pinnate, compound palmate, fan, needle clusters, flat/single needles, scale foliage). Most of the ~170 species are then parameter variation, not new geometry.

### The attach contract (this fixes the attach pain)

Every leaf in an archetype must share these conventions exactly, so tree assembly stays trivial and identical across the group. Chris fills the bracketed conventions once; they then hold for the whole library.

- **Origin / pivot:** local origin sits at `[petiole base / attachment point]`, so the leaf rotates naturally when parented to a twig.
- **Axis convention:** `[+Y = tip direction, +Z = adaxial (top) surface normal, +X = lateral]` — pick once, apply everywhere.
- **Scale & units:** real-world scale in `[units]`; a 10 cm leaf is 10 cm. Define the scale anchor.
- **Petiole:** `[included / excluded]`; if included, length convention and where it meets the pivot.
- **Normals:** author foliage normals as `[hemispherical / inflated]` rather than true geometric normals, so leaves light softly under AgX instead of self-shadowing harshly. This is the single biggest lever on whether a tree reads as foliage or as cardboard.
- **LOD card convention:** lower LODs use `[single quad / cross-quad / mesh card]`; define the UV layout so every species in the archetype lands in a consistent atlas region.
- **Wind compatibility:** the attach pivot should double as (or be compatible with) the eventual wind pivot, so wind animation can be added later without re-rigging. (Grass wind is already on the priority list; trees will want the same.)

### Archetype validation gate

An archetype is **not blessed for mass production** until it has been proven against its most *divergent* member, not just its easiest one. Build the base, then build the parameter-extreme of the group (e.g. London plane → sweetgum within palmate lobed: broad-shallow vs star-sharp). If the base stretches to both on parameters alone, the archetype holds. If the divergent member breaks it, fix the archetype now — on species #2 of the group, not species #40.

---

## Phase 3 — Build the trees (per-species loop)

One species per session, in roster tier order. The loop:

1. **Understand.** Load the dossier. Confirm the archetype mapping and the parameter deltas. If anything in the dossier is thin, fill it before proceeding. (Measure twice.)
2. **Derive.** From the dossier, set the archetype parameters for this species. Plan the seasonal color states and the silhouette target.
3. **Build the leaf.** Tweak the archetype to the species. Honor the attach contract — no exceptions.
4. **Self-critique the leaf against reference.** Render side-by-side with the dossier imagery at matched orientation. Check silhouette, proportion (L:W, lobe depth ratio), margin read at near distance, venation only where it reads, and color across every seasonal state. Iterate until it cannot be improved further. Record what was hard.
5. **▣ GATE 1 — Chris reviews the leaf.** Stop. Present the leaf and the side-by-side. Do not put it on a tree until Chris approves. Address feedback, re-present if needed.
6. **Assemble the tree** and build the LOD chain to spec (table below). Skeleton = trunk +
   primary + secondary only (no tertiary; hard law 4). **After every Blender regen, run
   `godot --headless --import` and delete the cached `cache/trees/<species>_*.res` + `.cfg`
   before viewing — a stale cache silently serves the old model (hard law 8).**
7. **Place in the eval area and self-critique the tree.** Verify at gameplay distances, instanced at density, across LOD0 → LOD1 → impostor transitions, under AgX, day and night, on the real terrain. A clean LOD swap (no popping, silhouette and color hold across the transition) is part of the bar. Iterate until satisfied.
8. **▣ GATE 2 — Chris reviews the tree in the eval area.** Stop. Do not start the next species until Chris approves.
9. **Record lessons-learned** and, if a systematic improvement emerged, fold it back into the archetype or the skill (see below).
10. **Advance** to the next species.

### LOD requirements

| Model size | LOD0 | LOD1 | Impostor |
|---|---|---|---|
| L — large tree | ✓ | ✓ | ✓ |
| M — medium tree | ✓ | ✓ | ✓ |
| S — small tree | ✓ | — | ✓ |
| Large bush | ✓ | — | ✓ |

M and L trees occupy screen space across a wide range of distances, so they earn the mid LOD. S trees and large bushes are small enough that the mid tier buys nothing — they jump from near detail straight to impostor.

### The self-critique standard (what "compare critically to reference" means)

- Comparison is **proportional** and against **cited reference**, not pixel-perfect against an arbitrary photo.
- The asset must be **indistinguishable-at-gameplay-distance from intent** — not flawless at 1:1.
- It must survive **instancing + the full LOD chain + AgX lighting**. A result that only looks right as a single hero render at LOD0 has not passed.
- **Flag ambiguous reference** rather than inventing detail to fill the gap.

---

## Lessons-learned & continuous improvement

A living document (suggested: `docs/tree-pipeline-lessons.md`), appended after every species.

Record, per species:

- Parameter deltas that worked, and any that fought the archetype.
- Attach-contract edge cases discovered.
- Recurring pitfalls and how they were solved.
- Measured polycounts and VRAM/atlas cost per LOD, against budget.
- Anything that would make the *next* species faster or better.

The feedback loop is the point: when a lesson is **systematic** (not a one-off quirk of one species), promote it — refine the archetype base, tighten the attach contract, or update the skill. The library and the skill should measurably improve as the roster is worked.

---

## Budget discipline (3060 Ti)

The constraint is VRAM, not time. Every distinct species keeps a leaf atlas resident whether or not that tree is near the camera, so species count is a standing tax — curation already controls it via the roster. Within a species:

- **Fidelity by prominence.** Tier 1 stood-under species (Mall elms, Reservoir cherries) earn full LOD0 detail. Tier 3 passed-at-distance species lean harder on the impostor and the archetype default.
- **Budgets per LOD:** `[Chris to set: LOD0 / LOD1 poly targets, atlas resolution per archetype, LOD-swap distances, impostor capture settings]`. Record actuals in lessons-learned and compare against these.
- **Detail invisible at gameplay distance is wasted.** Recognition at distance comes from silhouette and seasonal color, not vein accuracy. Spend accordingly.

---

## Definition of done

- **A leaf is done** when it passes self-critique against cited reference across all seasonal states, honors the attach contract, and has cleared Gate 1.
- **A tree is done** when its full LOD chain (per the size table) holds up instanced, across LOD transitions, under AgX at gameplay distances, and has cleared Gate 2.
- **A species is done** when its tree is done *and* its lessons-learned are recorded *and* any systematic improvement has been folded back into the line.

Only then does the next species begin.

---

## Working-agreement addenda (Chris, 2026-06-20)

- **Best tool over improvisation.** Use the best tool available rather than hand-rolling a worse version; if a good tool exists but we don't have it, get it. "No need to bite through the tough parts when we have saws and knives scattered around." (Originally cited as the reason to use Mtree's `LeafShapeGenerator` over a hand-rolled PIL outline — **but that path was later rejected too**: leaves are now real-photo cluster cards, see top banner. The principle stands; the example is stale.)
- **Every species starts with its dossier, then a blindspot audit.** Before any geometry, write the dossier (Phase 1) and then explicitly examine it for **blindspots, incomplete data, and contradictions**. The firmer the data foundation, the lower the chance of building the wrong thing. Flagged gaps are resolved (more research) before modeling begins.

## Hard build laws (Chris, 2026-06-22) — see `docs/tree_skeleton_plan.md` §1b

Absolute, every model. Reproduced here as a pointer; the canonical text is §1b.
1. Leaf card first (Gate 1), then sculpt the small (`_s`) model first; `_m`/`_l` derive from it.
2. Leaf card = a real twig sprig of **2–4 leaves + stems + a joining twig** — never a bare leaf.
3. Branch diameter floor **≥ 0.05** on every skeleton (`min_twig_diameter`).
4. Skeleton orders = **trunk + primary + secondary only — no tertiary** (`cap_skeleton_depth` max_depth = 2); the card's twig is the visual tertiary.
5. Card twigs attach to the branches in **real-data patterns** (tip-concentrated vs along-branch, per species).
6. **Trunk apex never bare** unless the data says a bare apex is a real feature.
7. **Every leaf connects to the trunk through branches** (`check_foliage_connectivity.py`) unless the data says otherwise.
8. **Clear the tree cache + reimport after every Blender redesign** (a stale cache serves the old model).
