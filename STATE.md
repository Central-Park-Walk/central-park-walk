# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py` — grow a plane from a seed, let form **emerge**.
Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ STOP-AND-RE-DERIVE. Chris (2026-07-16): "we still don't know how to make trees."

iter-44 built the wire (grower `--save` → `leafback_skinner` → `render_skinned.py`; it WORKS, 47k-face
coherent tree, DBH 1.04× census) and rendered the first grown plane. **Chris's verdict: the PNG is garbage,
the fine-twig fix is dead on perf, and we still can't make trees.** Full verdict in LEDGER `## 44`.

Three things are now true, and #3 is the real one:
1. ⛔ **Fine twigs as GEOMETRY are dead** — they blow the in-game bark budget. Crown density = CARDS only.
2. ★★ **The leafless render was a BROKEN INSTRUMENT** (my framing error). This representation keeps its
   crown in the `foliage`/card layer; I stripped 76% of the tree and judged habit off the naked scaffold.
   "Habit is most legible bare" is true of REAL trees, FALSE here. Such a render will always look garbage.
3. ★★★ **44 iterations validated ONE scalar (DBH) and never once looked at form.** No form metric, no
   reference comparison, ever. The healthiest number on the board hid a habit nobody had seen.
   **We have still never looked at a FINISHED (foliated) tree.**

## NEXT — Chris's call, one of two. Do NOT tweak the grower; the diagnosis is what's in question.

- **(A) — my recommendation, cheap, one session: RENDER THE TREE AS IT SHIPS.** Skinned scaffold + leaf
  CARDS via the existing `generate_trees_mtree.py` foliage-placement path (our skinned mesh already carries
  the full attribute contract: stem_id/radius/direction/branch_extent/hierarchy_depth). Zero new bark
  geometry ⇒ respects the budget. Rationale: deciding the grower's fate without ever seeing a finished tree
  = deciding on the strength of the instrument we just proved broken. Judge THAT against `reference_photos/`.
- **(B) — the canonical fork, if he'd rather settle it now: multi-position ADR — KEEP THE GROWER vs DROP IT
  FOR MTREE.** Mtree is an established tool already in this pipeline, already meshing the other species;
  the grower is arguably a 44-iteration reimplementation of it (CLAUDE.md: established tools over
  reimplementations). Prior art first. This is a canonical design change ⇒ **Chris signs off, not me.**

⚠ Whichever runs: the gate is now **FORM against reference photos**, not a scalar. A number may FAIL a
tree; it may never CLEAR one. And do NOT re-tune sap/heart internals — invisible, the bake discards them.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ WE CANNOT MAKE A TREE.** 44 iterations, no acceptable tree. Headline; everything else waits.
2. **★★ NO FORM METRIC EXISTS.** DBH cannot constrain habit. If the deliverable is appearance, an
   appearance gate is the FIRST gate, not the last. Needs deriving (crown breadth/height, fork counts,
   branch density vs `reference_photos/` + UTD crown-diameter) — but only inside (A) or (B) above.
3. **★ THE WIRE — ** RESOLVED (iter-44) **.** grower→skinner→render works; reusable for (A). Not the defect.
4. **★★ SAPWOOD/HEARTWOOD — SHIPPED, τ=34 fit on l-tier (42), NOT vindicated.** Census overlay DEFERRED;
   `r0_series` exposed to re-fit offline without regrowing. ⛔ do not touch — invisible on a standing tree.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ NO FINE-TWIG GEOMETRY** (Chris, iter-44, perf). Crown density comes from CARDS. Never re-propose.
- ⛔ **★★ DO NOT JUDGE HABIT FROM A LEAFLESS SCAFFOLD RENDER** (iter-44). Render it as it ships, or the
  instrument is broken. `--all` skin shatters (foliage = unskinnable leaf POINTS, not twig chains).
- ⛔ **★★★ c_H==c_S VINDICATED (41); RING-AGE is a RE-PARTITION not new wood (42).** DBH bit-identical.
  `Q_MASS=2/E_M`, `c_H=c_S`, HEART_RATIO, `TAU_HEARTWOOD=34`, q/K all DERIVED/OUTPUTS — never tuned.
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS:** EEVEE-Next hangs under xvfb (no GPU) — use Workbench (iter-44). Blender is slow to *exit*
  under xvfb: SIGTERM 143 at timeout fires AFTER the PNG writes — check the file before calling it failed.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (DBH@m only). Agent branches ginkgo/magnolia unmerged. LEDGER has 2 staged
  lessons from iter-44 (scalar-validation; render-as-it-ships) awaiting `/distill`.
- Artifacts: `tmp/plane_m_skel.npz`, `tmp/skinned_plane_m.png` (woody), `tmp/skinned_plane_m_all.png` (shattered).
