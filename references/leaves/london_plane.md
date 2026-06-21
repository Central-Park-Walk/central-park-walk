# Leaf Dossier — London Planetree (*Platanus × acerifolia*, syn. *P. × hispanica*)

**Phase 1 deliverable** (tree-leaf-pipeline-brief). Written before any geometry.
**Status:** morphology resolved by credibility-weighted, adversarially-verified deep research (2026-06-20). Citations + confidence per point below. Supersedes the earlier single-source draft.

---

## Verified morphology consensus (build to THIS, not to any single photo or judgment call)

| Trait | Consensus | Confidence | Key sources |
|---|---|---|---|
| Lobes | **3–5, with 5 most typical**; rarely to 7; entire/asymmetric forms occur on the same tree | HIGH (unanimous) | OSU, MoBot, NC State, Trees&Shrubs Online (Bean/Kew), USNA, peer-reviewed polymorphism study |
| Sinus depth | **Moderately deep, angular — ~1/3 of the blade.** DEEPER than American sycamore (<½ to base), SHALLOWER than Oriental plane. NOT cut to the midrib, NOT maple-deep | HIGH | FNA genus key, OSU, MoBot, NC State |
| Proportion | **Broad: about as wide as long to slightly wider** (blade L/W ≈ 0.8–1.0). Individual lobes about as long as wide, often longer than wide | HIGH (qualitative; no canonical ratio) | OSU, FNA (occidentalis note), MoBot |
| Lobe tips | **Pointed / acuminate** (typical). "Rounded lobes" is a minority cultivar phrasing | MEDIUM–HIGH | RHS, efloras/Flora of China, polymorphism study |
| Margin | **Coarse, sparse, forward-pointing teeth, ranging to entire.** No fine serration | HIGH | OSU, NC State, MoBot, FNA |
| Base | Broadly **truncate to shallowly cordate or broadly cuneate** | MEDIUM (inferred from blade outline) | OSU, RHS, FNA |
| Size | Large, ~10–25 cm; width frequently reaching ~20–25 cm (these are upper bounds) | HIGH | RHS, OSU, MoBot, Trees&Shrubs Online |
| Arrangement | **Alternate, simple** (single most reliable separator from maple) | HIGH | OSU, NC State, RHS |
| Venation | Palmate, ~3 main veins from the base | HIGH | RHS, OSU |

### The contradiction, resolved
The "shallow/angular/pointed" vs "rounded/deeper" split across sources is **real intra-hybrid polymorphism plus a terminology split, not an error to average.** *P. × acerifolia* is the hybrid of American sycamore × Oriental plane, so its leaf is intrinsically intermediate and variable (a single tree ranges from entire to typical 5-lobed; cultivars span shallow-lobed 'Liberty'/'Bloodgood' to deeply-lobed 'Columbia'/'Augustine Henry'). **Build to the dominant/typical condition: moderately-deep angular sinuses, pointed-acuminate tips, coarse sparse forward teeth.**

### Cross-species diagnostics
- **vs American sycamore (*P. occidentalis*):** plane has **deeper** sinuses, lobes about as long as / longer than wide, and **paired (1–2)** fruit balls; sycamore has shallow broad sinuses (<½ to base), terminal lobe wider than long, **solitary** fruit balls. [FNA]
- **vs Oriental plane (*P. orientalis*):** plane is **less** deeply lobed (Oriental = deep narrow sinuses cut ~to the middle, 5–7 narrow lobes); seed balls ~2 (intermediate; sycamore 1, Oriental 3–6).
- **vs maples (*Acer*):** resemblance is superficial — plane is **alternate** (maple opposite), ~3 main veins (maple 5–7), winter bud concealed in the swollen petiole base.

### IMG_4070 verdict
The user-supplied `reference_photos/london planetree/IMG_4070-...jpg` (flat, 5 lobes, sharp acuminate tips, coarse forward teeth, moderately-deep angular sinuses, wider-ish than tall) is **REPRESENTATIVE of the hybrid (HIGH confidence)** — every feature sits inside the documented envelope and matches the typical condition. It is not diagnostic of either parent; the intermediate condition *is* the hybrid. So it's a **valid visual cross-check** at Gate 1 — but the build targets the consensus descriptors above, with IMG_4070 as corroboration, not as the sole authority.

---

## Seasonal color states
- **Spring:** new growth bronze/reddish, hairy; flowers monoecious (yellowish male, reddish female), inconspicuous. [NC State]
- **Summer:** medium–dark green, matte, slightly leathery; paler/greenish-white beneath.
- **Fall:** **dull yellow-brown, not showy** [NC State]. *This is why plane sits beside maple & sweetgum — it is the drab-fall species; the others carry vivid fall color.*
- **Winter:** deciduous; **paired spiky fruit balls** persist on bare branches; mottled exfoliating bark is the winter signature.

## Whole-tree silhouette
70–100 ft tall × 60–75 ft wide; pyramidal young → open, spreading, irregular with massive limbs at maturity. [NC State]

## Bark (LOD0 signature)
Mottled camouflage exfoliation — light brown/gray-green outer flaking to creamy-olive inner. [NC State]

## Signature features
Mottled exfoliating bark; paired 1–1.5 in spiky seed balls; large alternate maple-like leaves; bud concealed in petiole base.

## Prominence & location (sets fidelity tier)
Common CP path/allée tree; players stand under it → high-fidelity / Tier-1-ish. Project comment cites ~2,411 census instances — **still to verify** against `convert_to_godot.py` tree data + locations.

---

## Archetype mapping → Mtree `LeafShapeGenerator` starting params
Palmate-lobed archetype (with maple = deep/rounded, sweetgum = star-sharp). Plane = **broad, moderate-depth, pointed** member. Starting hypotheses for the creator (tune at build, then Gate 1):
- Superformula **m ≈ 5** (5 lobes); `aspect_ratio` ≈ **1.0–1.15** (about as wide as long to slightly wider — *NOT* the 1.4+ I previously asserted).
- `margin_type = LOBED`, **moderate** `tooth_depth` (sinuses ~1/3 of blade — deeper than sycamore, not maple-deep), **high** `tooth_sharpness` (acuminate tips), modest `tooth_count` for **coarse, sparse forward teeth**.
- Truncate-to-cuneate broad base; gentle `midrib_curvature` + slight `edge_curl`; light venation density (reads at near distance only).

## Sources & credibility notes
- **Primary:** Flora of North America (genus key + *P. occidentalis* hybrid note), RHS, Oregon State Landscape Plants, USNA cultivar doc, peer-reviewed *Platanus* leaf-polymorphism study, Flora of China (efloras).
- **Secondary:** Missouri Botanical Garden, NC State Extension, OSU, Virginia Tech dendrology, Trees & Shrubs Online (Bean/Kew), Wikipedia.
- **Discounted by adversarial verification (note for the future):** NC State Extension's **"rounded lobes"** phrasing was refuted 0–3 (not the dominant tip shape), and its leaf-proportion figure **"6–7 in long × 8–10 in wide" (W/L≈1.4) was refuted 1–2 as too wide.** NC State's "deeper sinuses than sycamore" *did* hold up. So: trust NC State on sinus-depth-vs-sycamore, discount its rounded-tip and over-wide-proportion claims.

## Remaining open (quantitative) questions — not blocking the build
1. A primary-flora base descriptor specifically for the hybrid (currently inferred).
2. A source-backed numeric L:W range (only qualitative consensus exists).
3. Quantified fraction of pointed vs rounded-lobed specimens.
4. Numeric tooth count / geometry per lobe margin (sources say only "coarse").
