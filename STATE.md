# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py` — grow a plane from a seed, let form **emerge**.
Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-42: THE RING-AGE HEARTWOOD TRIGGER (Track B) IS CODED, τ DERIVED (=34 yr), COMMITTED.

The iter-41 heartwood defect (the grower's only heartwood was Aye's branch-death bank, its OWN no-reuse
artifact) now has its fix. Sapwood = the wood laid down in the **last τ=34 years** (outer rings);
everything older ages into heartwood, DECOUPLED from branch death. It RE-PARTITIONS the built cross-section
— adds no wood, **DBH bit-identical** (l-tier still 36.2in / 1.29× census, confirmed). Ring-age split is
now the headline `sap_frac`; old lenses kept as `sap_frac_pipe` / `a_heart_deathbank`.

**τ DERIVED, not guessed:** the l-tier (104 yr) trunk hit √0.5 of final girth at yr 69/104 → τ=34 lands it
at 50% basal-area sapwood. ⚠ 2× below Björklund's ~60 yr (pine): my "wide sapwood ⇒ τ≥60" prior was WRONG
— "wide" is a width/area fact, not a years fact; a vigorous plane reaches wide sapwood in fewer years.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** /n_tips divisor dropped; n_tips 135–273.
2. **★★★ SAPWOOD "DEFICIT" — MECHANISM SHIPPED + τ DERIVED (iter-42).** Ring-age trigger coded, τ=34 fit on
   the l-tier. NOT yet vindicated: τ was fit to l (⇒ l=50% by construction). The real test = does the SAME
   τ land s & m? = iter-43 overlay. Smoke: 6-yr tree reads 0 heart / 100% sap ✓ (prediction a's mechanism).
3. **★ THE GATE IS NOT CONDEMNING BIGNESS (iter-40).** S≡1 baseline ships (l DBH 1.25×, H 23.4m, 273 tips).

## NEXT — iter-43: the census overlay (the farmable grind), the hack-test proper

- **ONE change is DONE; this is the VERIFY.** Farm to a subagent (§0): `plane_bench.py` 5×{s,m,l} ≈ 25 min,
  sap/heart AREA per tier vs census. Predicted: (a) sapling ~0 heart (15<34), (b) l has a core (50% by fit).
  **The open question:** does the untuned τ=34 also land the **m** (47 yr) split? If m fails, the 34-vs-60
  tension is structural — suspect the model's near-LINEAR radial growth (real planes may decelerate → larger
  τ). Bench reads `st["sap_frac"]` = the ring-age split; `r0_series` lets the overlay re-fit τ per tier.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ c_H==c_S IS VINDICATED (iter-41).** Do NOT tune HEART_RATIO to buy sapwood. The fix was the
  ring-age TRIGGER (a new term), orthogonal to c_H. `Q_MASS=2/E_M`, `c_H=c_S`, `C_NDEF=None`, q/K, HEART_RATIO
  all DERIVED/OUTPUTS — do not tune them.
- ⛔ **★★ RING-AGE IS A RE-PARTITION, NOT NEW WOOD.** DBH must stay bit-identical; if a τ change moves DBH,
  something fed back that must not. Fit τ on the **l-tier** (mature = census 50%); s/m sap_frac are OUTPUTS,
  never retuned (the hack-test). "Wide sapwood" ≠ large τ (it's area, not years — the iter-42 correction).
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS:** never nest `nohup … &` in a `run_in_background` tool. Papers on disk: Aye 2022 (heartwood),
  Björklund 1999 (sapwood ~60 yr, pine), Shinozaki I+II, Hellström 2018, WBE. ★★ txt extraction STRIPS
  symbol glyphs & equation images — read numbers from prose/xml/`eqs.png`.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (DBH@m only). Agent branches ginkgo/magnolia unmerged. Distilled 2026-07-15
  (45043f1): iters 34–39 → global rules; raw → `ledger_archive/2026-07.md`.
