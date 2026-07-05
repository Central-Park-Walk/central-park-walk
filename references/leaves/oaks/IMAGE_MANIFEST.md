# Oak reference image manifest (Phase 2b)

Honest catalog of what's actually on disk under `reference_photos/pin oak/`, what each
image is good for, and the gaps. **Finding: the folder is a 3D-model marketing grab-bag,
not botanical reference.** Only one image is a real specimen, and it shows the WRONG leaf
morphology for the American red-oak group. Per-species flat-leaf / wire-mesh botanical
references must be gathered (iNaturalist CP-geofiltered, per `vegetation_modeling.md` §3)
before Gate-1 leaf work. Dossier leaf morphology comes from cited web botany, not these.

## On-disk images (viewed 2026-06-24)

| file | what it is | useful for | NOT useful for |
|---|---|---|---|
| `colored-fall-autumn-oak-leaves-BG0537.jpg` | **real specimen** — 8 oak leaves on white, full green→yellow→gold→brown→russet fall series | **fall-color palette** (all oaks); the **white-oak / rounded-lobe card** | leaves are **robur-type ROUNDED-lobe** (European white-oak group) — WRONG for bristle-lobed pin/red/scarlet |
| `oaktree01_wireframe02.jpg` | low-poly **card-cluster wireframe**, looking up into a canopy | shows the card-cluster construction we already use; loose canopy-density cross-check | not species-specific; not a real tree |
| `Austrian_oak_Quercus_cerris_1_1000_0002.jpg` | full-tree **3D-model wireframe** labelled *Q. cerris*, asymmetric reaching branch | loose **silhouette/branch-architecture** cross-check for a rounded-irregular oak | a 3D asset, not botany; NOT a leaf reference |
| `redoak_09_031.jpg` | full-tree **line/wireframe render**, dense rounded broadleaf crown, twin-ish leader | loose **rounded-crown silhouette** cross-check (red/white group) | not a real tree; no leaf/bark detail |
| `oak_12.jpg` | (oak photo/render — uninspected in detail) | general silhouette | TBD |
| `shingle-oak-tree-08-02.jpg` | shingle oak (*Q. imbricata*) — an UNLOBED entire-leaf oak, not in our roster | tangential | off-roster species |
| `pin-oak-3d-model-9m-*.jpg` (×4) | **3D-model marketing renders** of a pin-oak asset, multiple angles | rough pin-oak **massing/silhouette** cross-check | commercial 3D renders, not botany |
| `oak/oak-tree-03-3d-model-*.{jpg,webp}` (×3) | more **3D-model renders** of a generic oak | rough silhouette | commercial 3D renders |

## Gaps to fill before Gate-1 (gather per `vegetation_modeling.md` §3)
- **American Lobatae flat-leaf on white** (pin / red / scarlet) showing the bristle-pointed
  lobes + sinus depth — the single most important missing reference (drives the Lobatae card).
- **Winter bare-structure** shots: pin oak (excurrent + drooping lower limbs) and a
  rounded red/white oak — habit lives in the skeleton (the BRIEFs say so).
- **Cerris narrow toothed leaf** (sawtooth / cerris) on white.
- **Bark close-ups**: pale flaky white-oak bark; orange-fissured Turkey-oak bark.
- **CP-geofiltered stand/grove** shots for the §5b coherence target.

## Note
`reference_photos/pin oak/` commingles ≥4 species (cerris, pin, red, shingle) under a
"pin oak" name. When real refs are gathered, split into per-species subfolders
(`reference_photos/oak/<species>/`) so the manifests are clean.
