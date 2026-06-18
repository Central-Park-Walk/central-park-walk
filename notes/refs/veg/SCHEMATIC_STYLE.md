# Schematic style preamble — FIXED, reused for every plant

> Part of the schematic-driven build loop: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md) §7.
> The **schematic is the approval + character layer, never the metric spec.** An image
> model fakes orthographic projection and invents wrong phyllotaxy/leaf shape — read it
> for silhouette, habit, and gesture; **never extract dimensions from its pixels.**
> Numbers live in each plant's `BRIEF.md`, verified against real photos.

**How to use:** paste this preamble verbatim, then append the plant's
`SCHEMATIC_PROMPT.md` subject block. The user runs Gemini (Nano Banana / Gemini Pro
image), brings back the line art, and saves it next to the plant's BRIEF. Keep this
preamble **identical across every plant** so the whole schematic library reads as one
coherent botanical-plate set. Exploit Nano Banana's subject-consistency by generating
the base plate, then *editing* it for variant states (season / view) rather than
re-prompting from scratch.

---

## FIXED PREAMBLE (paste verbatim)

```
Botanical schematic plate in a clean scientific line-illustration style.
Pure black ink linework on a plain pure-white background — monochrome, no
color, no gray washes, no gradients, no fills, no drop shadow. Uniform line
weight for outlines; fine hatching used ONLY to suggest form, sparingly.
Strict ORTHOGRAPHIC projection — true elevations, viewed straight-on, with NO
perspective and NO foreshortening.

Lay the plate out as a labeled multi-view: (1) a FRONT elevation of the whole
plant and (2) a SIDE elevation of the whole plant, side by side, both full
height from base to tip with even margins; plus (3) one or more DETAIL insets
(leaf, node, or flower) drawn larger to one side. Include a simple labeled
vertical SCALE REFERENCE at the left edge — a plain ruler marked in meters —
for proportion only. Each view/inset may carry a short plain text label
(e.g. "front", "side", "leaf"); no other text, no annotations, no numbers
beyond the scale ticks. Consistent drawing convention so the same subject can
be re-rendered in other states without changing the style.
```

---

## Per-plant `SCHEMATIC_PROMPT.md` should add, after the preamble:
- **SUBJECT** line: species, common name, life-form, the stage/season to draw.
- **Form** paragraph: the habit/gesture from BRIEF §1–§2, in plain visual language.
- **The one unmistakable thing** (BRIEF §6) called out explicitly.
- **Detail insets** to include (the diagnostic features — BRIEF §4, §6).
- **AVOID** line: the species-specific failure modes (wrong view, color, the
  common ID confusion, cartoon styling).
- Optional **variant edit prompts** (season/view) exploiting subject consistency.
