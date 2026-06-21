# Tree & Leaf Pipeline — Lessons Learned

Living document, appended after every species (per `tree-leaf-pipeline-brief.md`).
Promote *systematic* lessons into the archetype library, the attach contract, or the skill.

---

## Cross-cutting lessons (not species-specific)

- **REALISM PATH = real-leaf alpha-cutout CARDS, not procedural 3D geometry.** (2026-06-20, hard lesson) Per the deep-research report (`docs/research-game-ready-leaves.md` §1–2): industry-standard realistic leaves are alpha cards textured from a **photographed/scanned real leaf on white**, or CC0 leaf atlases (ambientCG). SpeedTree's primary leaf representation is cards with 1-bit alpha. A flat reference photo like `IMG_4070` *is* a finished leaf texture — cut it to RGBA (`scripts/vegetation/cut_leaf_texture.py`) and you have a real, correctly-veined, correctly-toothed, species-distinct leaf in one pass. **Do this before reaching for any generator.** Trying to procedurally generate the leaf shape with Mtree's superformula produced sweetgum-stars and burned a session. See [[feedback_do_the_research]] — we researched the method then ignored it.
- **Mtree veins are a `vein_distance` per-vertex attribute, not geometry.** They drive a shader / bake into the card texture. A plain BSDF on the raw mesh shows only `vein_displacement` ridges → reads as an "asterisk". If Mtree is used at all, it is a secondary VARIATION tool whose output bakes to the leaf atlas.


- **Use Mtree's `LeafShapeGenerator`, not hand-rolled outlines.** (2026-06-20) The project spent effort on a PIL parametric outline + scattered-card leaf system while Mtree already shipped a full procedural leaf creator: superformula contour (`m,a,b,n1,n2,n3,aspect_ratio`), `margin_type` + `tooth_count/depth/sharpness`, space-colonization **venation as real 3D geometry**, and **deformation** (`midrib_curvature, cross_curvature, vein_displacement, edge_curl`), with `seed`/`asymmetry_seed`. It is fully headless-scriptable:
  ```python
  gen = m_tree.LeafShapeGenerator()
  apply_preset_to_generator(gen, "MAPLE")   # or set params directly
  gen.seed = ...; gen.asymmetry_seed = ...
  cpp = gen.generate(); create_leaf_mesh_from_cpp(mesh, cpp)
  ```
  Because venation is real geometry, the painted-vein texture is largely unnecessary. Presets present: OAK, MAPLE, BIRCH, WILLOW, PINE.
  **Verified against installed m_tree 5.5.0** (2026-06-20, local source-check): `LeafShapeGenerator` (+`triangulate`/`compute_uvs`), all five presets, and the `mt_LeafShapeNode` node are all real. A deep-research run that "refuted" these was reading the stale **v4.x GitHub master** — web repo state ≠ installed binary; trust the `.so` on disk. **Unused capability also in the binary:** `LeafLODGenerator.generate_card` + `generate_billboard_cloud` (Mtree can emit leaf cards / billboard clouds itself — candidate for mid/far LOD; see `docs/research-game-ready-leaves.md`).
- **Best tool over improvisation; acquire the tool if missing.** General heuristic now in the brief addenda. Check the framework/addon before writing generation code.
- **Dossier first, then a blindspot audit.** Each species starts with a written dossier (`references/leaves/<species>.md`); then explicitly hunt blindspots / incomplete / contradictory data and resolve before modeling. Sources frequently disagree (see plane below) — flag, don't average blindly.
- **Read the addon's socket tooltips for parameter semantics — don't trust old code comments.** (2026-06-20) `leaf_shape_node.py` `PARAM_DESCRIPTIONS` is authoritative: `n1`=Roundness (LOW=puffy/broad, HIGH=thin/spiky), `n2`/`n3`=Lobe Shape (LOW=bulging/broad, HIGH=pinched/angular), `m`=lobe count, `aspect_ratio`=W:H. A stale comment in `build_plane_leaf.py` had `n1` inverted and cost several wasted sweeps producing sweetgum-stars. For a broad-lobed palmate leaf (plane/maple family): low-ish `n1`, moderate `n2`, lobes from the CONTOUR, and `DENTATE` (not `LOBED`) margin for the teeth.
- **Beware tracing the wrong reference.** (2026-06-20) An earlier traced "plane" outline was actually maple-like (deep narrow lobes) and dragged the model toward maple for several iterations. Trust flat herbarium-style photos + cited morphology over a trace of unknown provenance.

## Archetype: palmate lobed

- Members so far: maple (deep, rounded sinuses), **London plane** (broad, shallow-to-moderate, angular sinuses, wider-than-tall), sweetgum (star-sharp). Validate the base against the divergent pair (plane ↔ sweetgum) before mass use.

---

## Per-species

### London planetree (*Platanus × acerifolia*) — IN PROGRESS
- Dossier: `references/leaves/london_plane.md`. Consensus target (deep-research, adversarially verified): 5 lobes, **moderately-deep angular sinuses (~1/3 of blade**, deeper than sycamore / shallower than Oriental plane), **pointed-acuminate tips**, coarse sparse forward teeth, **broad blade ~as wide as long to slightly wider (L/W ≈ 0.8–1.0)**, dull yellow-brown fall.
- **Corrections to earlier single-source claims:** proportion is NOT W/L≈1.4 (refuted 1–2); sinuses are NOT "shallow" — they're moderate (deeper than sycamore). NC State's "rounded lobes" refuted 0–3; trust NC State only on sinus-depth-vs-sycamore.
- **Lesson — single secondary sources mislead:** the whole shallow-vs-deep / rounded-vs-pointed muddle dissolved only under multi-source credibility weighting; the hybrid's leaf is *intrinsically polymorphic*, so any one photo/source is a sample, not the truth.
- **IMG_4070 validated** as representative of the hybrid (high confidence) → usable as a Gate-1 visual cross-check, not as sole authority.
- Open: CP prominence/locations (verify in `convert_to_godot.py`); precise numeric L:W / tooth count (sources qualitative only — not build-blocking).
- **Leaf build (2026-06-20) — SOLVED the "pale green star". Root cause: the prior `build_plane_leaf.py` drove the superformula toward a SWEETGUM star (the species plane must be distinct from). Two compounding errors, both from trusting old code comments over the addon's own tooltips:**
  - **`n1` (Roundness): LOW = puffy/broad, HIGH = thin/spiky.** The old comment had it backwards (claimed n1<1 = star). Plane wants **n1 ≈ 0.85** (broad).
  - **`n2`/`n3` (Lobe Shape): LOW = bulging/broad, HIGH = pinched/angular.** Old build used n2=3–4.5 (spiky); plane wants **n2 ≈ 2.7** (broad moderate lobes). n2≈1.8 over-bulges into a toothed disc with no 5-lobe read; n2≈2.9 starts to deepen toward star. The 5-lobe palmate read lives in **n2 ≈ 2.4–2.9**.
  - **Margin must be `DENTATE`, not `LOBED`, for the teeth.** `LOBED` barely cuts at tooth_depth<0.45 (gave round blobs) AND consumes the single margin pass so there's no budget for teeth. With lobes coming from the CONTOUR (m=5 + n1/n2), `DENTATE` is free to supply the **coarse sparse forward teeth** — `tooth_count≈9, tooth_depth≈0.18, sharpness≈0.88` reads as coarse (count 12 / depth 0.10 = too-fine scalloping).
  - **General lesson (folded up top):** read the installed addon's socket tooltips for parameter semantics; do NOT trust prior code comments — they had `n1` inverted and cost several wasted sweeps. After 2 star-shaped sweeps the diagnosis (not the params) was wrong.
  - **Gate-1 candidate params:** `m=5, n1=0.85, n2=n3=2.7, aspect_ratio=1.08, DENTATE tooth_count=9 tooth_depth=0.18 tooth_sharpness=0.88`, venation Open, midrib_curvature=0.06 cross_curvature=0.10 vein_displacement=0.22 edge_curl=0.04. ~391v/702f. Measured dims W/L≈1.05 (matches consensus). Renders: `notes/london_plane_leaf/GATE1_v2_top.png` + `_3q.png`. **Awaiting Gate-1 review.**
  - **Distinctiveness confirmed vs the trio:** plane = broad lobes + angular sinuses + coarse teeth; maple = rounded (U) sinuses + vivid red/orange fall (new ref `reference_photos/Red Maple/fa29...jpg`); sweetgum = deep narrow star + fine serration + vivid crimson fall. Plane's drab yellow-brown fall is the autumn differentiator (material/season stage, not geometry).
- (Tree assembly, Gate 2, polycounts/VRAM — to be filled after Gate 1.)
