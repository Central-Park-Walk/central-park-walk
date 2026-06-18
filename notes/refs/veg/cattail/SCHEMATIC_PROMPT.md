# Schematic prompt — Broadleaf Cattail (*Typha latifolia*)

> Schematic = approval + character layer only. Metrics live in [`BRIEF.md`](./BRIEF.md);
> never read dimensions off the pixels. Fixed preamble: [`../SCHEMATIC_STYLE.md`](../SCHEMATIC_STYLE.md).
> **First test plant of the schematic-driven loop** ([`docs/vegetation_modeling.md`](../../../../docs/vegetation_modeling.md) §7).

**To run:** paste the FIXED PREAMBLE from `../SCHEMATIC_STYLE.md`, then the SUBJECT block
below. Bring back the line art and save it in this folder (e.g. `schematic_v1.png`).

---

## SUBJECT block (paste after the preamble)

```
SUBJECT: A common broadleaf cattail (Typha latifolia), a tall emergent
freshwater-marsh plant, drawn as a SINGLE mature shoot at late-summer stage,
rising from a simple horizontal waterline at its base.

Form: a strictly VERTICAL, unbranched shoot — never arching, never bending.
A small fan of long, flat, sword-shaped strap leaves rises vertically from one
clasping sheathed base at the waterline; the leaves are notably WIDE and flat
(the broadleaf trait), all roughly the same height, splaying only modestly and
straightening back to vertical. From the center rises ONE round, leafless stalk
standing slightly above the leaves, bearing at its top the classic cattail
flower spike: a dense, smooth, sausage-shaped brown cylinder (the "hot-dog"
female seed head) capped DIRECTLY by a slightly narrower pointed spike (the male
section) with NO gap between the two — they touch. The cylinder is roughly 6–10
times longer than it is wide.

THE ONE UNMISTAKABLE THING: the brown no-gap "hot-dog" cylinder on a bare stalk
held rigidly above a strict-vertical, very-wide strap-leaf shoot.

DETAIL INSETS to include: (a) a single leaf in cross-section, showing the very
wide, flat, slightly D-shaped blade; (b) the flower spike enlarged, showing the
male section sitting directly on the female cylinder with NO bare gap between
them.

AVOID: any perspective or 3/4 view; any color; arching or drooping leaves; thin
grass-like blades; a visible bare gap of stem between the two spike sections
(that is the narrowleaf species, not this one); a torch/firework or cottony
look; cartoon styling.
```

---

## Optional variant edits (run as edits on the approved plate — keep subject consistent)

- **Young / vegetative (spring):** "Same plant and style, young spring shoot: the vertical leaf fan only, NO flower stalk and NO spike yet, leaves slightly shorter."
- **Winter / senescent:** "Same plant and style, late-winter: leaves shredded and tan, a few bent, the brown cylinder burst open and releasing wispy cottony seed down from one side."
- **Colony silhouette (interaction, secondary plate):** "Same style and scale, a stand of 8–12 of these shoots packed close at a water's edge, reading as a continuous vertical wall of strap leaves with brown spikes scattered through it — the dense colony, not spaced individuals."

---

## After approval → build mapping (from BRIEF §8)
Generator `make_cattail()` (`scripts/make_undergrowth.py:2038`), `SPECIES` idx 25; re-wire
placement into `ZONE_SPECIES[7]` Waterside as dense colony patches; validate on the
**colony wall** (hero), not a single shoot.
