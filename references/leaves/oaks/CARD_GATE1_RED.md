# RED OAK — Lobatae leaf-cluster card · GATE 1 self-critique (Phase 3, step 1)

**Build order (FIDELITY_CALL.md):** Skeleton A + Lobatae card → RED OAK (template).
Step 1 = leaf-cluster card → finalize at **Gate 1** → *then* build `_s` structure.
**This is the Gate-1 stop: the card is NOT yet on a tree.** No skeleton/scatter/placement
work was done (scatter_weight is a separate Phase-3 carry-over, out of this loop).

## Asset under review
- `textures/leaves/oak_lobatae_cluster.png` (summer, 1024², RGBA)
- `textures/leaves/oak_lobatae_cluster_fall.png` (fall base, 1024², RGBA)
- Shared **pin + red** Lobatae card (FIDELITY_CALL §NEAR); this pass validates it **for red**.
- Built by `scripts/vegetation/make_oak_cluster_from_photo.py` from Chris's GIMP-composited
  sprig `reference_photos/oak/red_oak_sprig.jpg`.

## Cited reference (oak_red.yaml `leaf:` + `sources:`)
`reference_image: null` on disk → morphology comes from **USDA SRS Silvics (ag_654) + FEIS
querub**, realised through a **real specimen leaf**: `_sources/cand3.jpg` = Wikimedia Commons
*Quercus rubra-(EU).jpg* (see `_sources/PROVENANCE.txt`). Dossier spec:
length 12–23 cm · width 10–15 cm · **L/W ~1.5** · **7–9 lobes** · **sinus depth 0.50 (MODERATE)**
· **bristle-tipped** · alternate.

## Measured (tmp/measure_oak_leaf2.py, radial profile off cand3.jpg)
| trait | dossier (red) | measured on the card's source leaf | verdict |
|---|---|---|---|
| lobing | bristle-**lobed**, 7–9 | bristle-lobed; 5 major radial tips (apex + 2 pairs) + small basal pair ⇒ 7–9 | ✅ |
| sinus depth | **0.50** (moderate; pin=0.75 deep) | **median 0.50** (deepest mid-leaf ~0.72, shallower 0.44–0.50) | ✅ reads as red, NOT pin |
| bristle tips | yes | present on every lobe apex | ✅ |
| L/W | ~1.5 | ~**1.9–2.2** (this specimen is elongated) | ⚠ slender end of red-oak range |
| species | *Q. rubra* | real *Q. rubra* specimen → authentic by construction | ✅ |

## Construction
4-leaf sprig on a forking twig, tips outward, chroma-keyed clean off the green bg, centred.
Bottom-anchored stem (LP cluster-card method) → connectivity-friendly when placed. This is the
SETTLED real-photo cluster-card representation (tree-pipeline-lessons.md), not a procedural blade.

## Findings
1. **Morphology is faithful and correctly RED, not pin.** The pin/red discriminator is sinus
   depth (red 0.50 vs pin 0.75); the card's source leaf medians at **0.50**. The one genuinely
   distinctive Lobatae differentiator is carried correctly.
2. **⚠ Minor — L/W ~2.0 vs dossier ~1.5.** The chosen specimen is slenderer than the red-oak
   average. Within natural variation (red oak spans ~1.4–2.2) and it still reads unmistakably as
   red oak, but it is not the "typical" broad-obovate red leaf. Optional: source a broader
   specimen if Chris wants the average silhouette. **Not a blocker.**
3. **Minor — baked specular sheen.** A few glossy highlights from the photo sit in the albedo
   (same as the accepted LP card). Cosmetic; can be knocked back if desired.
4. **Fall base is intentionally neutral russet-brown** — per-species fall HUE is shader-side
   (`FALL_COLORS`), so one card serves pin/red. Its brownness is by design, not a defect.

## Provenance note (honesty)
This card was first built and **Gate-1 approved by Chris in the prior (7-taxon) session**. The
roster was since re-scoped to 3 oaks, but the **Lobatae card spec is unchanged** (bristle-lobed,
red = moderate 0.50 sinus, shared with pin). Rebuilding from the same source + method yields the
identical file, so this pass **re-validates the existing card against the now-frozen 3-oak
dossier** rather than churning it.

## ⚑ FLAG for the PIN phase (Chris, Gate-1 review 2026-07-04) — note, do NOT fix now
The **bottom-right leaf** of the 4-leaf cluster reads with **visibly deeper sinus cuts** than the
other three — closer to **pin's ~0.75-deep** range than red's 0.50. On this red card it is fine as
natural leaf-to-leaf variation on one twig (and was accepted as-is). **Why it's written down:** this
same Lobatae card is the **default shared pin+red card** (FIDELITY_CALL §NEAR; "deep-sinus pin card"
held in reserve). When pin reuses it, **that one already-deeper leaf may already be doing some of
pin's silhouette work** once instanced — which could be a *feature* (cheap partial pin read on the
shared card) or a reason to look again (uneven — one deep leaf among three moderate). **Resolve at
the pin Lobatae Gate-1**, per the FIDELITY_CALL open split; don't rediscover it from scratch.
(Chris observed this directly on the render. My automated radial measure of that leaf was too
crop-sensitive to pin a firm number — deepest cuts ~0.6, median ~0.4 — so the flag rests on the
direct visual read, not a disputed metric.)

## VERDICT → ✅ GATE 1 APPROVED (Chris, 2026-07-04)
Card **satisfies the red-oak Lobatae spec** (measured) and is **accepted as-is** as the red/pin
shared card. Chris reviewed the reference/build/fall comparison directly: reads unmistakably as red
oak; the L/W deviation is within natural variation, not a blocker. One note carried forward (not
fixed): the deeper bottom-right leaf → PIN-phase flag above. **Next: Skeleton A → red `_s`.**
