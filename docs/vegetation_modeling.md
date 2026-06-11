# Vegetation modeling — the reference-first method

Written 2026-06-11. This is a **project-wide discipline**, not a one-off plan: it
governs every plant model in the park — the tree redesign
([`tree_model_redesign.md`](tree_model_redesign.md)), the spicebush, and the whole
post-sprint model-redo program (dozens of shrubs, ferns, herbs, grasses, wetland and
meadow species). Read it before modeling *any* plant.

It exists because of a specific, diagnosed failure in the current models.

---

## 1. The failure this method corrects

The current vegetation was built from *rules* ("stems radiate up and out," "leaves
cluster along branches") without looking at what the real plant actually does. The
results, in the user's words (2026-06-11, ground truth —
[[feedback-real-world-observation]]):

- **Wrong habit.** The spicebushes look **V-shaped** instead of *flowing over
  themselves*. Real *Lindera benzoin* is a multi-stemmed shrub whose primary stems
  arch and whose secondary growth droops and layers, so the plant cascades into a
  mound. The rule produced a vase because nobody modeled the droop and the layering.
- **No interaction.** Each tree "occupies its 3D cylinder, branches rarely touching or
  interacting." Crowns are self-contained balls with air between them.
- **No coherence.** "The forest seems made up of individual trees, rather than being a
  coherent ecological feature." Undergrowth helps the feeling but does not supply it.

The root cause is single: **the models encode how to draw the data, but not what the
finished plant ought to look like or how it ought to behave.** This method supplies the
missing half.

> "Claude needs to understand not only how to draw the data, but what the final drawing
> ought to look like, and how it ought to behave."

That understanding comes from **reference** — real photographs and video of the actual
plant — and it must cover three things a silhouette alone never captures: **habit,
interaction, and behavior.**

---

## 2. The three things every model must get right (beyond silhouette)

A correct outline is necessary and not sufficient. Judge — and build — for these:

### Habit — how the plant flows over itself
The plant's characteristic *form and gesture*: arching vs upright vs weeping vs
mounding; where it forks; whether stems droop and layer over each other or stand
apart; symmetry vs the lopsided reaching of a real plant competing for light. This is
what makes the spicebush a cascade and not a V, and a weeping willow a curtain and not
a sphere. **You cannot deduce habit from data — you observe it in photographs and copy
it.** Habit is the single biggest realism lever and the one the current models miss.

### Interaction — how it meets its neighbors
Real plants are not instanced in isolation; they grow *into each other*. Tree crowns
interlace and merge into a ceiling; shrubs in a thicket overlap into a continuous mass;
ferns and groundcover knit the floor. A model that is too tidy, too symmetric, or too
self-contained at its silhouette edge cannot interlock — it reads as a separate object
no matter how it's placed. **Model crowns/forms that are full to their edge and
slightly asymmetric, so neighbors fill each other's gaps.** And see §4 — interaction is
also a *placement* property, judged on the stand, not the individual.

### Behavior — how it moves and changes
How the plant responds to wind (a stiff oak crown vs a trembling birch vs a whole
spicebush bouncing on its arching stems) and how it changes through the seasons (leaf
flush, summer mass, fall color and drop, bare winter structure, bloom). Behavior is
specified and validated against **video** reference, not guessed. Wind is a shared
field so a stand moves as one mass with per-plant local variation
([[reference-aaa-wind]], [[project-species-wind]]); the per-species biomechanics
already exist in the wind shaders — tune them to the reference, don't leave them
generic.

---

## 3. The reference set — gather this before modeling anything

For each species, assemble a reference set under `notes/refs/veg/{species}/` (bulk
images/frames gitignored; a tracked one-page `BRIEF.md`). Source it **in this priority
order** (confirmed with the user 2026-06-11):

1. **iNaturalist, geo-filtered to Central Park.** Research-grade observations of the
   actual park population — multiple individuals, angles, and seasons, real photos.
   This is the primary, data-first source: it shows *these* plants, in *this* park.
   (WebSearch/WebFetch can pull observation pages and image URLs.)
2. **Walking-tour and time-lapse video, via claudetube** ([[reference-claudetube]]).
   The best source for **habit-in-context** (how the plant sits among its neighbors)
   and **behavior** (wind motion, seasonal state). The user already supplies these
   (Sheep Meadow walk, cloud time-lapse) and **will provide more walk videos on
   request** — ask when a species' habit or motion is unclear from stills.
3. **Conservancy / NYBG / NYC Parks and other reliable institutional sources.** Central
   Park Conservancy plant pages, NYBG, extension fact sheets — already cited in
   [[reference-cp-botany-full]] and [[reference-vegetation-modeling]]. Use these for
   authoritative form, dimensions, and seasonal data.
4. **User-supplied photos**, where the user has them for a specific plant.

A complete set shows: full-plant **habit** (summer mass *and* bare/winter structure —
the skeleton is where habit is most legible), **interaction** (the plant growing among
others — a thicket, a stand, a grove, not an isolated specimen on a lawn), branching/
stem **structure**, leaf/flower/bark **detail**, and **seasonal** states (flush, summer,
fall, winter, bloom). If any of those is missing, the model will guess that aspect and
guess wrong.

### `BRIEF.md` — the falsifiable target
One page per species, tracked in git, written from the reference set. It states, in
checkable terms: the **habit** in one sentence ("multi-stemmed, primary stems arch to
~3 m then secondary growth droops and layers into a mound — cascades, never a V"); the
**interaction** behavior (thicket-forming / crowns merge / solitary); the **layer** it
occupies (canopy / sub-canopy / shrub / herb / floor); **density** bucket tied to its
real number (LAI, stems/m², cover %); **behavior** (wind character + seasonal
timeline); and **the one thing that makes it unmistakable.** This is the document the
visual Definition of Done is judged against — "looks better" is not a checklist item
(workflow.md §2).

### Two things the reference is NOT
- **Not photogrammetry capture.** Using *existing* photos/video as art direction is
  different from going to the park to shoot capture sets — the hard no-field-capture
  rule ([[project-no-field-capture]]) still holds. We look at references; we don't
  capture geometry from them.
- **Not a shipped asset, and not traced.** Reference images are inputs to
  understanding, never copied into the repo as assets and never traced into geometry.
  The models stay original procedural creations, fully in-repo and MIT-distributable
  ([[feedback-distributable-assets]]). Looking at a photo to learn a plant's form is
  not copying the photo. AI-generated images are an acceptable art *target* only to
  fill a gap a real reference can't, clearly labeled, and likewise never traced.

---

## 4. The unit of design is the stand, not the specimen

Coherence (failure #3) is emergent — it cannot be fixed one model at a time, because it
*is* the relationship between models. So the unit of design and of validation shifts:

- **Validate on the scene.** The test capture for woodland is a North Woods / Ramble
  **stand**, judged for canopy closure, crown interlace, and layered structure — not a
  thumbnail of one tree. The test capture for spicebush is a **thicket**, judged for
  overlapping cascading masses — not one shrub. A model that passes its thumbnail but
  reads as an isolated object in the stand has failed.
- **Coherence is built from four levers together** (detailed for trees in
  [`tree_model_redesign.md`](tree_model_redesign.md) §"forest coherence"): crown/form
  fullness to the silhouette edge; correct crown width vs the *real* (census) spacing,
  so crowns that should overlap actually do; height layering (emergent / canopy /
  sub-canopy / shrub / herb / floor) instead of a uniform ceiling; and asymmetric,
  interlocking per-instance variation so neighbors mesh instead of tile.
- **Undergrowth is connective tissue, not the fix.** The user is explicit: undergrowth
  helps the feeling but does not supply coherence. The canopy and the layering have to
  carry it; the floor and shrub layers thicken it.

---

## 5. Workflow per plant

1. **Gather the reference set** (§3) and write `BRIEF.md`. No geometry before this.
2. **Re-baseline** the current model against the brief (render it, look at it, record
   what's actually wrong) — check, don't estimate (workflow.md §3).
3. **Model habit first** (§2): get the gesture/flow right before detail. For the
   spicebush that means arching multi-stem + drooping layered secondaries; for a tree
   it's the branch architecture and crown reach.
4. **Density + detail** to the brief's bucket (leaf/needle mass, texture, bark/stem),
   within the perf budget (vegetation is fragment-bound — see
   [`tree_model_redesign.md`](tree_model_redesign.md) §2; gain density from
   form/texture/placement, not raw card overdraw).
5. **Behavior** (§2): tune wind biomechanics and seasonal response to the video
   reference.
6. **Per-instance variation**: widen the seed envelope to span the real plant's range
   (age/sun/soil — [[feedback-research-before-generator]]) so a stand never tiles.
7. **Validate on the stand** (§4) plus the per-model DoD, then commit. For trees, run
   the full downstream chain + harness in
   [`tree_model_redesign.md`](tree_model_redesign.md) §8–9.

---

## 6. How this changes the manual's quality bar

`DESIGN.md` already requires "visual changes tested against reference images, not
against feeling." This method makes that operational for vegetation and raises it: the
reference must capture **habit, interaction, and behavior**, the **BRIEF.md** is the
falsifiable target, and **the stand is a validation unit** alongside the individual
model. Any vegetation model that was not built against a reference set is provisional,
regardless of how it scores in isolation.
