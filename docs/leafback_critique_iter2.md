# Leaf-Back London Plane Skeleton — Critic verdict, iteration 2

Critic (Role 2) · 2026-07-07 · judged against `docs/leafback_tree_planner_spec.md` **v2** (adds AC-14).
Submission: line C with the **growth-ordered, capacity-constrained crown partition** (lowest/oldest
primary now commands the largest sub-crown). One change vs iteration 1; same cloud (781-sprig, seed
20260706), same two-phase growth, same pipe model. Direct A/B against the iteration-1 baseline renders.

---

## 1. Overall verdict

**PASS.** Every *blocking* AC — AC-1…AC-7 **and the new AC-14** — is visually satisfied against the
reference photos. This is a genuine step up from iteration 1's *marginal* pass: the one design gap that
iteration 1 escalated (limbs read as thin wire, no bold primary hierarchy) is now materially fixed. The
primaries read as **bold structural boughs** with a legible lower-thicker-than-higher gradient, the
near-trunk "stand inside the tree" framings gain real heft, and no iteration-1 blocking pass regressed.

Two honesty caveats keep this from being "converged":
- **AC-8 (perf) remains UNMEASURED** — no fps figure supplied. Per the spec this is a convergence gate
  run at/near convergence, so it does **not fail iteration 2**, but it is still unproven and gates the
  finish. Node count *dropped* 1037 → 974, which is a favourable early-warning signal, not a measurement.
- The **secondary→twig** gauge step is soft (1.35× measured vs the ~2× proxy). The *headline* AC-14
  read — bold primaries vs everything else — is clearly met, but the **middle ("medium") tier is
  compressed toward the twigs**, so in the full-crown framings the hierarchy reads closer to
  **thick→fine** than a crisp **thick→medium→fine**. Non-blocking (AC-14's gate is the visible bold
  hierarchy; the ratio is an explicitly tunable proxy), but it is the top AC-14 tuning residual. See §2, §5.

---

## 2. AC-14 assessment (the iteration-2 target) — **PASS**, materially better than baseline

This is what iteration 2 changed, so I judged it first and in depth, A/B against the baseline and against
the reference uplooking/branch-structure photo.

**Do primaries now read as bold structural limbs? — Yes.** The clearest evidence is the trunk→scaffold
transition close-ups (`growth_transition_0`, `growth_transition_1`) and the near-trunk shots
(`growth_fromtrunk_0/1`, `growth_lookup`). Off the trunk, a small number of **substantial boughs** peel
away that you could not mistake for the fine outer twigs; the eye can trace a clear caliber step-down
trunk → primary → secondary → twig. In `growth_transition_1` in particular the three tiers are legible in
one frame. In the crown views (`growth_crown_view1/2`) the bold arcing primaries now read as *structural
limbs* rather than as thin meridian ribs.

**Is the difference real and in the right direction vs baseline? — Yes, unambiguously.** Direct A/B:
- `transition_0` / `transition_1`: baseline branches leave the trunk at nearly the twig gauge (only
  modestly heavier); iteration-2 primaries are visibly heavier, with a real trunk→primary→secondary drop.
- `crown_view0/1`: baseline is a near-uniform "nest of wire"; iteration-2 has clearly boldest sweeping
  limbs standing out of the twig lattice.
- This matches the metrics: lowest primary **115 mm = 0.60·r₀**, squarely inside the AC-14 mature band
  (0.55–0.70·r₀); baseline was 64 mm = 0.34·r₀ (below floor). Primary/secondary gauge 4.42× (≥2× target).

**Are the lower primaries visibly thicker than the higher? — Yes.** Metric caliber low→high =
115,117,102,77 mm (was inverted 64,108,118,114). Visually the lowest primaries are the most massive limbs
in the tree and caliber diminishes with height — the acropetal age gradient the Growth model calls for.
No inversion where an upper primary out-calibers a lower one. The previous **inversion is fixed.**

**The two soft spots, judged by eye:**
- **2.4 % wobble between the two lowest primaries (115 vs 117 mm): negligible / invisible.** A 2 mm
  difference at ~115 mm is far below perceptual threshold at any framing; I cannot see it and it does not
  read as an inversion. Do not spend effort here — it is metric noise, not a defect.
- **Secondary/twig step 1.35× (vs ~2× proxy): visible and mildly bothersome, non-blocking.** In the
  full-crown framings the secondaries do not read as a distinct "medium" population — the middle tier is
  squeezed toward the twig gauge, so the gestalt is bold-primaries-then-fine-mesh rather than a smooth
  three-step taper. It reads *fine* in the near-trunk close-ups (where a medium tier is visible) but
  flattens in the crown views. This is the one place AC-14's "thick→medium→fine" is only partly delivered.

**Caliber-gradient depth (life-stage calibration):** the highest/lowest primary ratio is **0.67**, just
*above* the provisional ≤0.60 proxy — i.e. the gradient is **slightly shallow**. For the *mature* Broad
m-tier REF this reads acceptable (the spec explicitly wants mature "clearly bold but not veteran-extreme,"
and the dramatic reference uplooking photo is arguably a bucket-3 veteran, so I did not hold the model to
that photo's extreme gradient). I judge the current depth **about right for mature** — not a design fault.
Flagging only so the Planner is aware it sits at the shallow edge of the band. See §7.

**Mechanism (AC-6 / AC-14(d)):** the boldness comes from the growth-ordered partition + DBH-anchored,
lower-weighted budget flowing through the *existing* pipe model — not a flat thickness multiplier bolted
onto a wiry skeleton. Node count fell (974 < 1037), consistent with re-partitioning rather than
inflating. This satisfies the "emergent, not multiplied" intent. (Deferred to the Engineer's submission
note for confirmation no flat multiplier was introduced.)

**Verdict on AC-14: PASS.** The visible bold hierarchy and lower-thicker-than-higher gradient — the gate —
are met and are a clear, real advance over baseline. The secondary/twig compression is a tunable residual.

---

## 3. Regression check on AC-1…AC-7 — no regression

The concern was that concentrating branches on the low primary would create a tangle, a thick elbow, or
starve the top. Checked each:

- **AC-1 persistent trunk — PASS, no regression.** The central spine is intact in `growth_transition_0/1`,
  `growth_crown_view0`, `growth_lookup` — a single dominant axis continuing up and thinning, no starburst
  hub. Unchanged by the partition (only the sub-crown assignment changed, not the spine).
- **AC-2 separated heights — PASS, no regression.** Same emergence mechanism; scaffolds still leave the
  trunk at distinct, well-spread heights and azimuths.
- **AC-3 near-trunk sparseness — PASS, improved.** Still a handful of clearly-separated proximal limbs
  with real sky gaps (`growth_fromtrunk_0`, `growth_lookup`), and now those limbs carry the AC-14 heft, so
  the "stand inside the tree" experience reads *better* than iteration 1 (AC-3's own note: sparse + bold
  together make this view). This is the strongest framing in the set.
- **AC-4 monotone density — PASS, no regression.** Radial coarse→fine gradient intact; the re-weighted
  wedge counts (292/238/168/83) redistribute *azimuthally*, not radially — no dense-core/sparse-shell
  inversion introduced.
- **AC-5 no structural artifacts — PASS (all five).** Critically: **the over-loaded low primary did NOT
  produce a tangle or a thick-limb elbow.** In `growth_transition_0/1` the heavy low primary leaves the
  trunk cleanly (~emergence angle, no down-then-up chevron on a thick limb); the larger sub-crown ramifies
  without a knot. No new loops, no long straight non-trunk rods, no coincident nodes visible. One minor
  eye-only item in §5 (a floating twig stub), not an AC-5 thick-limb defect.
- **AC-6 emergent regularity — PASS (visible signatures).** No witch's-broom, no coincident-twig fan, no
  fanned forks; taper reads pipe-model. Node count fell, consistent with emergence not clamping.
- **AC-7 reuse — PASS (discipline).** Same 781-sprig cloud, seed 20260706, DBH/2 = 0.19 m anchor. The one
  change (partition rule) is the specifically-directed AC-14 fix, not an unexplained modification.

**Watch item (not a regression, stays within AC-12):** the top primary is now both thinner (77 mm) and
commands a smaller sub-crown (83 attractors), which can only *nudge* the already-known apex-thinness
(AC-12) slightly further. It does **not** read as a broken leader — the trunk spine, not the top scaffold,
carries the leader — but the crown apex is a touch thinner than in the baseline. Still known-acceptable;
see §5/§7.

---

## 4. The arcy read (AC-11) — reduced but not resolved; still non-blocking

The spec predicted bolder, caliber-graded low primaries would break the thin-meridian silhouette that made
the head-on arcs echo line B. **Partially borne out.** In `growth_crown_view1/2` the bold arcing primaries
now read as *structural limbs* rather than as wiry meridian ribs — a real, if incomplete, improvement over
the baseline's uniform "nest of arcs" (compare baseline `crown_view1`, which is a pure wire nest). The
*heft* helps the among-the-limbs read. But the overall full-crown gestalt across all three azimuths still
leans "ball / nest of sweeping arcs" rather than "majestic open branching," and it is still somewhat worse
off-axis (60°/120°) than head-on, exactly as flagged in iteration 1. So: bold primaries did their part;
the residual is now an **emergence-variety** problem (all primaries still depart at ~the same angle and arc
alike — AC-9), not a caliber problem. Non-blocking (AC-1…AC-5 hold; foliage hides most of it). Remains the
top *quality* residual after AC-8.

---

## 5. Defects the metrics missed (eye-only hunt)

- **Compressed medium tier (see §2).** The full-crown framings read thick→fine because secondaries sit
  near the twig gauge (1.35×). Eye-visible; the metric flagged it as a soft proxy but the *gestalt* cost
  (loss of the smooth three-step taper the reference photo shows) is a Critic call: it is real but minor.
- **One floating twig stub, `growth_transition_1` lower-left.** A short isolated tube segment not obviously
  connected to a parent. Almost certainly a detached leaf-back sprig stub, not a thick-limb structural
  artifact (it is twig-gauge, so outside AC-5(i)). Low priority; confirm it is graph-connected.
- **Apex a touch thinner than baseline** (the thin/small top primary, §3). Within AC-12; watch it doesn't
  cross into a visible void.
- **NOT present (checked and cleared):** no tangle/knot on the loaded low primary; no thick-limb elbow at
  the low emergence; no new loop or self-rejoin; no single-point convergence (origins still distinct); no
  caliber that reads "pasted on" — the boldness reads organic (it tapers through the pipe model, it is not
  a uniform fat cylinder). The bold primaries read *paid for*, not fabricated.

---

## 6. Ambiguity / extra renders

Verdict does **not** hinge on any missing render — no AMBIGUOUS flag. Two low-cost renders would sharpen
follow-up but are not required for PASS:
- A **component-colored or top-down (plan)** wireframe to confirm the `growth_transition_1` floating stub
  is connected (or prune it) and to re-confirm no az-120° ring is a true rejoin.
- One **foliated** crown render at az 0/60/120 to confirm the arcy skeleton reads as an acceptable clad
  dome — the real question behind whether AC-11 stays cosmetic. (Spec says judge the skeleton, so optional.)

---

## 7. Prioritized list for Engineer / Planner

1. **[AC-8, BLOCKING FOR CONVERGENCE — Engineer] Measure performance.** Run `scripts/perf_gate.sh`
   real-park `--park --all-london-plane` at ramble + north_woods; report median fps. Node 974 is a
   favourable proxy but the >45 fps gate is still unproven and it gates "done." Required measurement.
2. **[AC-14 residual, secondary/twig step — Engineer defect-fix] Uncompress the medium tier.** Get the
   secondary→twig gauge closer to a clear step (target ~2×) so the crown reads thick→medium→fine, not
   thick→fine. Likely a twig-seed (`R0`) / terminal-twig-count / secondary-partition tuning within the
   existing pipe model — *not* a new multiplier. Engineer-owned unless it can't be done without changing
   design intent, in which case escalate.
3. **[AC-11 + AC-9, top quality residual — Engineer defect-fix] Break the multi-azimuth arcy read.** Add
   per-scaffold jitter on emergence elevation + mild gravity/light tropism in the core-crossing phase so
   the primaries stop departing at an identical angle and arcing alike. Bold primaries already helped;
   emergence variety is the remaining lever. Target: 60°/120° read no more meridian-arced than head-on.
4. **[AC-14 gradient depth — ESCALATE to Planner (design), LOW/optional] Is 0.67 highest/lowest right for
   mature?** The primary caliber gradient sits at the *shallow* edge of the band (proxy wanted ≤0.60). I
   judge it acceptable for the mature m tier REF and do **not** ask for a change now — but whether
   mature should read a touch steeper (closer to the reference uplooking photo, which may be a veteran) is
   a **Planner v3 calibration question**, not an Engineer guess. Flag only.
5. **[AC-5 hygiene — Engineer, cheap] Confirm/prune the `growth_transition_1` floating twig stub.**
6. **[AC-12 — Engineer] Apex fill / leader-continuation origin at `spine_top`,** now slightly more wanted
   because the top primary shrank. Known-acceptable; after 2/3.
7. **[AC-13 — Engineer] Twig tip-jitter** — cosmetic, lowest priority (unchanged from iteration 1).

Item 1 is a required measurement (the convergence gate). Items 2, 3, 5, 6, 7 are Engineer defect/tuning
fixes. **Item 4 is the only design question for the Planner** — and it is a *low-priority calibration*
note, not a blocker: unlike iteration 1 (where the missing-AC for limb caliber was a real spec gap), v2's
AC-14 now adjudicates limb heft and the model passes it.
