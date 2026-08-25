# STATE — cpw / tree-sculptor · updated 2026-08-25

**Target:** Blender sculptor → game-ready London-plane GLBs.

## Where we are
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. **W-40 plates
REJECTED by Chris (TS-1 verdict 2026-08-25):** overlays are not coupled to
the photos. Claude looked and confirmed on the mature overlay — TWO fault
families: **(a) REGISTRATION** — cyan silhouette spills past the photo strip
both sides onto letterbox (composite scale/aspect; mechanical), coverage
inverted (real crown uncovered, cyan over sky), tips = unreadable speckle;
**(b) HABIT** — naked central mast to apex vs photo's multi-leader fork at
~¼ height; near-horizontal "menorah" limbs + drooping streamer tips.
⚠ **The overlay is a broken instrument:** no habit verdict may be read
through it, either direction, until registration is fixed and overlays
re-rendered honestly. Tip-host shell counts stay frozen (288/1920/1260).

## Budget (post W-39 bare / cards / tip_hosts)
young **62388** / **3720** / 155 · mature **126108** / **15864** / 661 ·
veteran **141768** / **17040** / 710.

## Open work
- `TS-1` habit · **FAILED — W-40 plates rejected.** Fix overlay registration
  FIRST, re-render honest overlays, only then judge habit (then the mast/
  menorah/streamer faults, if they survive an honest overlay).
- `KB-0` sculpt_kb DESIGN v2 + `EXAM_SAMPLE.md` (worked item #0) ·
  **awaiting_user_signoff**. R4/R5 CONFIRMED by Chris ("on-point") → key
  extended K6/K7; **`FAULT_LEXICON.md` founded (7 entries)**. Roster now sits
  **Fable 5 vs Opus 5 vs Qwen-VL** (his hunch: model difference — Fable
  caught what Opus shipped; blind exam separates acuity from attention).
- `TS-7` crotches **PASS** · `TS-6` garden layout shipped (W-30)
- `TS-9` elbows deferred · `TS-5` bark dial · `TS-3` impostors · `TS-4` species

## ★ ONE NEXT HYPOTHESIS
> The overlay compositor misregisters silhouette vs locked ref (scale/aspect
> of the composite). Verify the projection mechanically in shape_fit/overlay
> code BEFORE any habit refit or new ref hunt — the instrument must stop
> lying before any reading through it means anything.

## Look at
`tmp/tree_sculpt/habit_refs/mature_habit_overlay.png` (the rejected
instrument) · `docs/sculpt_kb/EXAM_SAMPLE.md` (the exam, made concrete) ·
`docs/sculpt_kb/DESIGN.md` (pre-test v2).
