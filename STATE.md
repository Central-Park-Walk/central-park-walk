# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py` — grow a plane from a seed, let form **emerge**.
Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ PIVOT (iter-43 decision, Chris 2026-07-16): SKIN THE SKELETON, put a tree on screen.

For 42 iterations the grower produced only a **skeleton of numbers** (branch pos/radius, DBH, sap/heart) —
by design ("no mesh" scope) and validated against census DBH, the only ground truth we have. But the last
several iterations refined **internal** wood physiology (sapwood/heartwood) that is DBH-bit-identical → it
moves NO visible geometry and the bake discards it. Chris asked, rightly, why there's still no tree to look
at. **Decision: stop refining invisible internals; skin the current skeleton and LOOK.** Full reasoning +
the 3060-Ti-can't-run-a-forest concern (resolved: grower is OFFLINE; runtime = MultiMesh lod0 → impostor,
docs/trees.md §1; GPU never simulates) in LEDGER `## 43`.

## NEXT — iter-43 (or 44): WIRE grower → existing skinner → render ONE leafless m-tier plane

The skinner and renderer ALREADY EXIST. This is glue, not authorship. ONE unit of work:
1. **Add skeleton .npz export to the grower.** `grow_tier()` already returns the graph in memory
   (`nodes[{pos,parent,radius,strand}]`, plus top-level `radius`/`strand` arrays, L2245–2252). Add a
   `--save <path.npz>` to `__main__` (L2351) that writes `pos, parent, radius, strand` — the exact keys
   `leafback_skinner.load_graph_npz()` reads (L304–316). ~10 lines; changes NO growth logic.
2. **Skin + render in Blender.** Feed the .npz to `leafback_skinner.load_graph_npz` → `build_tube_mesh(g)`
   (bark tube, leafless — matches F6 scope). Render via / adapting `render_skeleton.py` (white-bg ortho,
   the June v1–v11 path). Output to `tmp/`.
3. **LOOK.** One m-tier London plane, skinned, side view. Does the grown habit read as a plane?

**Verify for real:** run it, open the PNG, judge the *form* (Chris's eye is ground truth — a measurement
may FAIL a skin but may never CLEAR a defect he can see). Announce Blender cost before the headless run.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.**
2. **★★ SAPWOOD/HEARTWOOD — mechanism SHIPPED, τ=34 fit on l-tier (iter-42), NOT vindicated.** The census
   overlay that would test "same untuned τ lands s & m" is **DEFERRED, not cancelled** (Chris redirected to
   skinning). `r0_series` still exposed to re-fit τ per tier later without regrowing. Resume offline anytime.
3. **★ NEW — THE SKIN IS UNSEEN.** No tree has been rendered from the *grower* (June PNGs were the OLD,
   deleted one-shot builder). iter-43 closes this. This is now the headline defect.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ c_H==c_S IS VINDICATED (iter-41).** `Q_MASS=2/E_M`, `c_H=c_S`, `C_NDEF=None`, q/K, HEART_RATIO,
  `TAU_HEARTWOOD=34` all DERIVED/OUTPUTS — do not tune them to buy a number.
- ⛔ **★★ RING-AGE IS A RE-PARTITION, NOT NEW WOOD.** DBH must stay bit-identical. Fit τ on the l-tier only;
  s/m sap_frac are OUTPUTS (the hack-test). "Wide sapwood" ≠ large τ (area, not years — iter-42 correction).
- ⛔ **★ SKIN IS BARK-ONLY, LEAFLESS.** `build_tube_mesh` skins tubes; no leaf cards in iter-43 — leafless
  is the F6 scope AND the "habit most legible bare" brief. Do not smuggle in foliage; that's a later stage.
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS:** never nest `nohup … &` in a `run_in_background` tool. Papers on disk: Aye 2022, Björklund
  1999, Shinozaki I+II, Hellström 2018, WBE. ★★ txt extraction STRIPS symbol glyphs & equation images.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (DBH@m only). Agent branches ginkgo/magnolia unmerged. Distilled 2026-07-15
  (45043f1): iters 34–39 → global rules; raw → `ledger_archive/2026-07.md`.
