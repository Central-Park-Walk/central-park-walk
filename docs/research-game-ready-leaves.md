# Research — Realistic, game-ready tree leaves (Blender → Godot 4)

**Recovered & synthesized 2026-06-20.** This is the report from deep-research workflow
`wf_928de905` (question: best proven way to produce realistic game-ready broadleaf leaves
for a Godot 4 game built in Blender, free/local tools preferred). The workflow's own
Synthesize step crashed (`afterSynthesis: 0`), so it returned 17 verified claims unmerged;
this document is the hand-synthesis of those verified claims. **No claim here is un-vetted:**
each went through 3-vote adversarial verification. Votes shown as `(confirm-refute)`.

- Coverage: 5 search angles, **22 sources**, 98 claims extracted, 25 verified, **17 confirmed / 8 refuted**.
- Source quality tags from the run: `primary` = vendor/engine docs & source repos; `forum`/`blog` = practitioner.

---

## 1. Industry standard — cards vs 3D vs hybrid (and how SpeedTree does it)

**Consensus: hybrid, distance-driven. 3D/leaf-mesh near → leaf *cards* (billboards) → single billboard impostor far.** This is unanimous across the two primary sources (SpeedTree docs, NVIDIA GPU Gems 3).

- SpeedTree uses a **hybrid distance-based LOD**: full 3D geometry near camera, geometric
  resolution + effects reduced smoothly with distance, finally fading into a **billboard image**
  that matches most of its lighting state. *(SpeedTree docs, 3-0)*
- Leaves exist as **both card and mesh instances** simultaneously — not purely one or the other.
  Card-based rendering is the *primary* representation; fronds/leaves use **1-bit (alpha-cutout)
  transparent textures**. *(SpeedTree docs 3-0; NVIDIA GPU Gems 3 "Next-Generation SpeedTree
  Rendering" 3-0)*
- **Leaf LOD = fewer, bigger leaf instances with distance.** Since SpeedTree 5.0 they *abandoned*
  alpha-test "fizzling"; instead some % of leaf instances are gradually **shrunk to nothing while
  the survivors scale up**, driven by **per-vertex LOD scales in the vertex shader**.
  *(SpeedTree docs, 3-0)* — relevant if we ever want smooth canopy LOD instead of popping.
- The **3D→billboard transition is made smooth with alpha-to-coverage** (3D tree alpha fades out
  as billboard fades in); the shader picks from an **array of billboard images** matching the
  camera azimuth + that instance's rotation. *(SpeedTree docs, 3-0)* — this is exactly the
  octahedral-impostor idea we already use.

**Takeaway for us:** our existing lod0(3D) → lod1(mesh) → octahedral-impostor chain *is* the
industry-standard shape. The gap is leaf *quality* at the near tier, not the LOD architecture.

## 2. Getting the leaf image (textures, atlases, licensing)

- **ambientCG "Leaf Set 004" and the whole ambientCG library are CC0** — free, no attribution,
  commercial-OK, no redistribution restriction. *(ambientCG, 3-0)* → **safe for a distributable
  game.** This is the cleanest licensing path if we go the textured-card route.
- (Forum/secondary sources in the set also point to OpenGameArt CC0 vegetation packs and
  ~200 free photo-scanned leaf textures via cgchannel, plus the katsbits photo→alpha-mask
  method. These are lower-credibility and not independently re-verified here — treat as leads,
  not settled facts.)

**Licensing pitfall to remember:** "free to download" ≠ "free to redistribute in a shipped game."
CC0 is the only tag in this set that was *primary-source confirmed* clean for distribution.
Per project rule [[feedback_distributable_assets]], prefer CC0 or our own originals.

## 3 & 4. Blender / Mtree specifics  ✅ CONTRADICTION RESOLVED (local source-checked 2026-06-20)

The web claims here looked contradictory, but **the conflict was a version mismatch.** The
research's GitHub claims read the **old v4.x `MaximeHerpin/modular_tree` master branch**; our
machine runs **m_tree 5.5.0** (installed at
`~/.config/blender/4.5/extensions/user_default/modular_tree`, compiled
`m_tree.cpython-311-x86_64-linux-gnu.so`). I grepped the *installed* source to settle it.

**What the Blender-Extensions listing claimed — CONFIRMED true for our installed 5.5.0:**
- **Fully procedural 3D leaf geometry from math** — Superformula outline, margin detail
  (serrate/dentate/crenate/**lobed**), **space-colonization veins**, surface curvature (midrib
  curvature, cross-cupping, edge curl, vein ridges). The `.so` exports `Mtree::LeafShapeGenerator`
  (`generate`, `triangulate`, `compute_uvs`) and `Mtree::VenationGenerator::generate_veins`.
- **Auto leaf distribution on thin branches via geometry nodes** ("Add Leaves": Density, Max
  Radius, Scale/Rotation variation, custom Leaf Object slot). *(extensions.blender.org, 3-0)*

**Claims that were REFUTED in the web run but are FALSE for our installed version** — i.e. the
web run was wrong *for us* because it looked at v4.x:
- ~~"No leaf node in the menu"~~ → **`mt_LeafShapeNode` IS registered** (`node_categories.py:39`,
  in the `LeafShapeNode` class list). There is a user-facing leaf node.
- ~~"No OAK/MAPLE/BIRCH/WILLOW/PINE presets"~~ → **all five presets exist** in
  `presets/leaf_presets.py` (`LEAF_PRESETS`, `apply_preset_to_generator(gen, name)`).
- ~~"Leaf C++ files are empty stubs"~~ → leaf code is fully implemented in the compiled module.

**→ Our `tree-pipeline-lessons.md` was CORRECT.** `m_tree.LeafShapeGenerator()` +
`apply_preset_to_generator(gen,"MAPLE")` + the five presets are real in 5.5.0. No fix needed;
the doc is now stamped "verified against installed 5.5.0."

**Bonus capability the local grep surfaced (not in the web report):** the `.so` also exports a
`Mtree::LeafLODGenerator` with **`generate_card`** and **`generate_billboard_cloud`**. Mtree can
generate leaf *cards* and *billboard clouds* itself — directly useful for the mid/far LOD tiers
in §1, possibly removing the need for a separate card-atlas step. **Unexplored — worth a look
before building a custom card path.**

## 5. Godot-side rendering (transparency, impostors, MSAA)

Strong primary-source agreement here:

- **Use Alpha Scissor** for foliage in Godot 4 `StandardMaterial3D` — hard edges + correct
  sorting; semi-transparent areas below threshold aren't drawn. *(Godot docs, 3-0)*
- **Avoid alpha-blend for overlapping cards** — blended transparent surfaces have sorting
  issues and render in the wrong order. *(Godot docs, 3-0)* This is *why* scissor is preferred.
- **Cost of scissor: edge aliasing.** Standard MSAA does *not* anti-alias alpha-test cutout
  edges → "harsh, noticeable aliasing on trees." *(godot-proposals #1273, 2-0)*
- **Fix = alpha-to-coverage (Godot "Alpha Antialiasing" / Alpha Edge Blend|Clip), which
  requires MSAA 3D ≥ 2x** in Project Settings. *(Godot docs, 1-1 — weak vote, but matches the
  SpeedTree/NVIDIA primary sources in §1 on alpha-to-coverage being the standard fix.)*
- **Octahedral impostors (the far tier):** the wojtekpil Godot-Octahedral-Impostors baker imitates
  a 3D object from many angles using **one plane** *(3-0)*; for foliage use **hemisphere capture,
  not full sphere** (full sphere only helps if the object is seen from below) *(3-0)*; baker
  produces **albedo + depth + normal (+ optional ORM)** → **runtime-lit impostors**, not flat
  lit-color bakes *(3-0)*. This validates the runtime-lit-impostor decision already in
  [[mission_fable5_sprint]].

---

## Bottom line / what to act on

1. **Architecture is right.** 3D-near → card/mesh-mid → octahedral hemisphere impostor (albedo+depth+normal, runtime-lit) is literally the SpeedTree pattern. Don't rearchitect.
2. **Near-tier leaf realism is the real problem** ("pale green star"). Two viable routes, not mutually exclusive:
   - **Procedural 3D** via Mtree's leaf generator (Superformula + space-colonization veins) — *pending the local-source verification above.*
   - **Textured alpha-scissor cards** from **CC0 ambientCG leaf sets** — licensing-clean, fast, proven.
3. **Godot material settings are settled:** Alpha Scissor + alpha-to-coverage AA + MSAA 3D ≥ 2x.
4. **Our Mtree doc is verified, not broken.** Local source-check (2026-06-20) confirms
   `LeafShapeGenerator` + OAK/MAPLE/BIRCH/WILLOW/PINE presets + `mt_LeafShapeNode` all exist in
   installed **5.5.0**. The web run's refutations applied to old v4.x — ignore them for our build.
5. **Try Mtree's own `LeafLODGenerator.generate_card` / `generate_billboard_cloud`** before
   hand-building a card atlas — it may already cover the mid/far leaf LOD.

### On the "refuted" web claims — superseded by local source-check
The web run refuted "Mtree ships presets" and "leaf C++ is implemented" based on **v4.x GitHub**.
For our **installed 5.5.0** those refutations are wrong: presets, the leaf node, and the compiled
leaf code all exist (verified). Lesson: **web repo state ≠ installed version — check the binary on
disk** ([[feedback_check_dont_estimate]]).
- (Several Terrain3D-instancer and SIsilicon-impostor claims got `0-0` — **unverified, not refuted**; not enough votes. Don't cite them as established.)

### Sources (22; primary unless noted)
SpeedTree LOD docs · NVIDIA GPU Gems 3 ch.4 (SpeedTree rendering) · Godot StandardMaterial3D docs ·
godot-proposals #1273 + godot PR #40364 (alpha-to-coverage) · Mtree (extensions.blender.org +
github MaximeHerpin/modular_tree) · wojtekpil & SIsilicon Godot-Octahedral-Impostors ·
Terrain3D instancer docs · ambientCG LeafSet004 (CC0) · polycount foliage threads (forum) ·
cgchannel scanned-leaf / Graswald (secondary) · katsbits, asawicki alpha-test, NVIDIA mipmap
white-edge (blog/forum).
