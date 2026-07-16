# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-41: THE SAPWOOD "DEFICIT" IS A DEFECT, NOT BIOLOGY. Track A adjudicated it from the paper.

Chris said "continue" → I took Track A (validate sap_frac vs the on-disk census/paper). It did NOT close
board #2 as biology — it REOPENED it as a **named defect with a published fix**. Read `tmp/papers/aye2022`
(the heartwood paper the ratchet is already built on) + verified the heartwood TRIGGER against the wiring:
- Aye §Discussion (txt L189): the grower's heartwood model = Aye's **explicitly-unrealistic "no reusable
  pipes"** assumption. Real sapwood lives **~60 yr** (Björklund 1999), decoupled from the ~3–12 yr leaf life.
- WIRING (`ratchet` L1299–1383): heartwood is banked ONLY by branch death (`_kill_subtree`), **monotone,
  never resurrected**; NO ring-age term exists; a living trunk can never form an aged core. That IS the defect.
- iter-32's signature is explained: sap 0.45–0.51x too small, heart 1.77–2.63x too big (sapling 3.30x too much).

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips FOLD — ** RESOLVED (iter-38) **.** /n_tips divisor dropped; n_tips 135–273.
2. **★★★ SAPWOOD "DEFICIT" — ADJUDICATED (iter-41): a DEFECT, fix = Track B (ring-age τ_heartwood).** The
   grower has no aged-living-core heartwood; heartwood comes only from shed branches (Aye's no-reuse artifact).
   NOT the shed gate (iter-40), NOT c_H (vindicated below). See NEXT.
3. **★ THE GATE IS NOT CONDEMNING BIGNESS (iter-40).** S≡1 baseline ships (l DBH 1.25×, H 23.4m, 273 tips).
   Do NOT code a shed-gate fix (premise refuted). Size-law/R_TIP-prior all DEAD/refuted (rails).

## NEXT — iter-42: implement Track B, the ring-age heartwood trigger. (Chris may redirect on his iter-41 verdict.)

- **The one change:** in `ratchet()`, convert wood older than **τ rings from the cambium** to heartwood,
  DECOUPLED from branch death (a new term; the shed-branch banking can stay or fold in). This is a FIDELITY
  fix, independent of the economy (sap_frac absent from the gate, iter-40) — expect NO DBH/economy change.
- **τ is a DERIVATION, not a free knob:** fit ONE τ to the **~50%-of-basal-area sapwood** census target for
  Platanus (wide sapwood; grower comment L1322). One param, one robust allometric target = passes the
  ≤1-tuned-param hack-test. Anchor sanity: Björklund ~60 yr (pine); plane's wide sapwood ⇒ τ likely ≥ that.
- **Pre-registered prediction:** (a) sapling heartwood 3.30x→~0 (saplings have none); (b) old l-tree gets a
  physical inner core. OPEN: does it also land the m/l sap/heart split on census, or only fix the sapling?
- **Then measure** (the farmable grind, subagent per §0): instrument sap/heart AREA per tier, overlay census
  (`plane_bench.py` 5×{s,m,l} ≈ 25 min, or one l-tree ≈ 17 min). Do NOT run it before τ is set.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ c_H==c_S IS VINDICATED (iter-41): Aye says reusable pipes even out c_H→c_S.** Do NOT tune
  HEART_RATIO to buy sapwood. `Q_MASS=2/E_M`, `c_H=c_S` DERIVED, `C_NDEF=None` on purpose — all OUTPUTS.
- ⛔ **★★★ q/K & HEART_RATIO ARE OUTPUTS.** Emergent R_TIP overshoots BECAUSE q is un-tunable.
- ⛔ **★★ n=1 CANNOT MEASURE A RATIO / PAIR BEFORE YOU RATIO** (30, 39). `plane_bench.py` 5×{s,m,l} ≈ 25 min.
- ⚠ **HARNESS:** never nest `nohup … &` in a `run_in_background` tool (false "completed" while job detaches);
  let run_in_background own the python directly. Recover a detached job with ONE `tail --pid=<pid>`, no poll.
- ⚠ **Papers on disk** (`tmp/papers/`): Aye 2022 (heartwood — READ iter-41), Shinozaki I+II, Hellström 2018,
  WBE. ★★ txt extraction STRIPS symbol glyphs & equation images — read numbers from prose/xml/`eqs.png`.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
- Distilled 2026-07-15 (commit 45043f1): iters 34–39 lessons → global rules; raw → `ledger_archive/2026-07.md`.
