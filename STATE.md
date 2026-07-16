# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-42: THE RING-AGE HEARTWOOD TRIGGER (Track B) IS CODED & COMMITTED (44ff3e1). τ still being DERIVED.

The heartwood defect (iter-41: the grower's only heartwood was Aye's branch-death bank, its OWN no-reuse
artifact) now has its fix. Sapwood = the wood laid down in the **last τ years** (outer rings); everything
older ages into heartwood, DECOUPLED from branch death (Björklund 1999, ~60 yr sapwood life). It
RE-PARTITIONS the built cross-section — adds no wood, DBH/economy bit-identical (read-only history snapshot
+ pure lookup). Ring-age split is now the headline `sap_frac`; old lenses kept as `sap_frac_pipe` /
`a_heart_deathbank`. Smoke test (6-yr tree): 0 heart, 100% sap ✓ (prediction a's mechanism).

## ⏳ IN FLIGHT AT HAND-OFF — do NOT /clear until this lands (a /clear kills the auto-resume)

- **τ DERIVATION grow** (l-tier, 104 yr, ~17 min): background job `b3d8n70a5` → `tmp/iter42_ltier_derive.txt`.
  It prints `tau_50%` = the τ that lands the mature trunk at 50% basal-area sapwood. **On resume:**
  read that file, set `TAU_HEARTWOOD` in `plane_grower.py` to the derived integer (sanity: near ~60),
  re-confirm the l-tier base split, commit, then hand off for the census overlay. If the grow died, just
  rerun `python3 scripts/plane_grower.py l`.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** /n_tips divisor dropped; n_tips 135–273.
2. **★★★ SAPWOOD "DEFICIT" — MECHANISM SHIPPED (iter-42), τ pending.** Ring-age trigger coded; awaiting the
   derived τ + the per-tier census overlay to confirm it lands the split (not just the sapling).
3. **★ THE GATE IS NOT CONDEMNING BIGNESS (iter-40).** S≡1 baseline ships (l DBH 1.25×, H 23.4m, 273 tips).

## NEXT — finish τ (above), THEN iter-43: the census overlay (the farmable grind)

- **Verify predictions across tiers:** instrument sap/heart AREA per tier, overlay census. Pre-registered:
  (a) sapling heart 3.30x→~0, (b) old l-tree gets a physical core. OPEN: does τ also land the m/l split on
  census, or only fix the sapling? `plane_bench.py` 5×{s,m,l} ≈ 25 min → **farm to a subagent (§0)**.
- The bench reads `st["sap_frac"]` = now the ring-age split, so its verdict machinery already measures the
  new thing. `r0_series` in the output lets the overlay re-fit τ per tier without regrowing.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ c_H==c_S IS VINDICATED (iter-41): Aye says reusable pipes even out c_H→c_S.** Do NOT tune
  HEART_RATIO to buy sapwood. The fix was the TRIGGER (a new term), orthogonal to c_H. `Q_MASS=2/E_M`,
  `c_H=c_S`, `C_NDEF=None` all DERIVED/OUTPUTS. q/K & HEART_RATIO are OUTPUTS — do not tune them.
- ⛔ **★★ RING-AGE IS A RE-PARTITION, NOT NEW WOOD.** DBH must stay bit-identical; if a change to τ moves
  DBH, something fed back that must not. Fit τ on the **l-tier** (mature = census 50%), never the m (47 yr
  < 60 would force τ≈20 and contradict Björklund). s/m sap_frac are OUTPUTS, never retuned (hack-test).
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS:** never nest `nohup … &` in a `run_in_background` tool. Recover a detached job with ONE
  `tail --pid=<pid>`, no poll. Papers on disk: Aye 2022 (heartwood), Björklund 1999 (sapwood ~60 yr),
  Shinozaki I+II, Hellström 2018, WBE. ★★ txt extraction STRIPS symbol glyphs & equation images.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
- Distilled 2026-07-15 (commit 45043f1): iters 34–39 lessons → global rules; raw → `ledger_archive/2026-07.md`.
