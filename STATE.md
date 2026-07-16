# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py` — grow a plane from a seed, let form **emerge**.
Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — iter-44 DONE: THE WIRE IS BUILT. First skinned plane on screen; habit reads SPARSE.

The grower→skinner→render wire now works end to end (glue only, growth logic untouched, DBH bit-identical):
- `plane_grower.py --save <npz>` — faithful dump of pos/parent/radius/strand (+alive/foliage masks, root/H).
- `render_skinned.py` — loads via `leafback_skinner.load_graph_npz` → `build_tube_mesh` → Workbench render.
  Prunes to the WOODY scaffold by default (`~foliage`, F6 leafless rail); `--all` skins everything (debug).
- `render_skeleton.py::main()` guarded so its calibrated camera/sun import cleanly.

**The LOOK (Chris, judge `tmp/skinned_plane_m.png`):** m-tier, 17.7 in DBH (1.04× census), 47,056 bark
faces, one coherent connected clean-tubed tree. ✅ WIRE WORKS. ❌ but the woody crown is **sparse/spindly**
with whippy vertical leaders + a trunk lean — reads younger/airier than a 40-yr plane's stout-limbed
billowing crown. Confound checked & killed: `--all` render (`tmp/skinned_plane_m_all.png`) is shattered
fragments, so the sparseness is REAL, not an over-prune. Full read in LEDGER `## 44`.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ NEW HEADLINE — THE LEAFLESS HABIT IS MISSING ITS FINE-TWIG CLOUD.** A winter plane's signature
   twiggy crown lives ENTIRELY in the grower's `foliage` layer, which is isolated leaf-cluster POINTS, not
   skinnable woody twig chains. The woody scaffold alone can't carry the habit ⇒ sparse render. iter-45.
2. **★ THE SKIN IS SEEN — ** partially RESOLVED (iter-44) **.** A grown plane is on screen; wire works.
   Downgraded from "unseen" to "seen but sparse". The remaining defect is #1 above.
3. **★★ SAPWOOD/HEARTWOOD — mechanism SHIPPED, τ=34 fit on l-tier (iter-42), NOT vindicated.** Census
   overlay to test "same untuned τ lands s & m" DEFERRED (not cancelled); `r0_series` exposed to re-fit
   offline without regrowing. ⛔ do NOT re-tune it now — it is invisible on a standing tree (iter-43).

## NEXT — iter-45: give the leafless crown its fine wood, so the habit reads as a plane

ONE hypothesis to pick with Chris after he looks (see LEDGER 44 "NEXT"):
- (a) grower promotes persistent short-shoots → thin woody twig CHAINS the skinner can tube, OR
- (b) export/skinner builds thin tubes from foliage-node parent chains.
Also worth a look: crown breadth/density of the woody scaffold itself; does the trunk lean hold across
seeds (needs n>1, `plane_bench.py`). Do NOT re-tune sap/heart internals — invisible, bake discards them.

## Rails — each cost a session; do not re-litigate

- ⛔ **★ SKIN IS BARK-ONLY, LEAFLESS** (F6). Woody-scaffold prune is the default & correct; foliage nodes
  are NOT skinnable (proven iter-44: `--all` shatters). Fine twigs must come as thin WOOD, not leaf points.
- ⛔ **★★★ c_H==c_S VINDICATED (41); RING-AGE is a RE-PARTITION not new wood (42).** DBH bit-identical.
  `Q_MASS=2/E_M`, `c_H=c_S`, HEART_RATIO, `TAU_HEARTWOOD=34`, q/K all DERIVED/OUTPUTS — never tuned.
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS:** EEVEE-Next hangs under xvfb (no GPU) — use Workbench for skeleton renders (iter-44).
  Blender under xvfb is slow to *exit* (SIGTERM 143 at timeout is AFTER the PNG writes — check the file).
  Papers on disk: Aye 2022, Björklund 1999, Shinozaki I+II, Hellström 2018, WBE.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (DBH@m only). Agent branches ginkgo/magnolia unmerged. Distilled 2026-07-15
  (45043f1): iters 34–39 → global rules; raw → `ledger_archive/2026-07.md`.
- iter-44 secondary TODO: Workbench render bg is grey not the briefed white (`background_color` ignored).
