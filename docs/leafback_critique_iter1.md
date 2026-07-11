# Leaf-Back London Plane Skeleton — Critic verdict, iteration 1

Critic (Role 2) · 2026-07-07 · judged against `docs/leafback_tree_planner_spec.md` v1
Submission: line C (persistent central trunk + 4 distributed scaffolds + two-phase growth), unchanged.

---

## 1. Overall verdict

**MARGINAL PASS** — every *blocking* AC (AC-1…AC-7) is visually satisfied against the reference
photos; **AC-8 (perf gate) is UNMEASURED** and must be run before this can be called *converged*.
This is a genuine, material advance over lines A (tangle) and B (lantern cage), not a rubber stamp —
but it is a "structurally reads as a tree" pass, **not** a "majestic specimen" pass. The full-crown
framings still read as a wiry ball / meridian-arc shell; only the near-trunk framings read
convincingly tree-like. Because the tree will be clad in foliage (shell filled, interior hidden) and
the near-trunk "stand inside the tree" experience — the project's core — does read correctly, the
residual crown-view weaknesses fall on the known-acceptable side (AC-9/11/12) rather than blocking.

Two honesty caveats that keep this from being a clean PASS:
- **AC-8 unmeasured** — no fps figure in the submission. Blocking *for convergence*. Deferred, not
  failed, at iteration 1, but it gates the finish.
- The **"arcy" crown read (AC-11)** is more pronounced and appears in *more* azimuths than the spec's
  "head-on only, otherwise cosmetic" description anticipates (it is actually *worst* at az 60°/120°,
  not az 0°). Still classified known-acceptable/non-blocking, but it is the #1 thing to fix next and
  it brushes up against the tree/not-tree line. See §3 and §5.

---

## 2. Per-AC assessment

### AC-1 — Persistent central trunk/leader — **PASS (marginal)**
Judged from `crown_view0`, `cmp_crown` row C (head-on frame), `transition_0/1`, `fromtrunk_0`.
In the head-on frames the trunk is unambiguously a single vertical axis that **continues up through
the crown and thins** — it does *not* stop at a low fork or become a starburst hub (the A/B failure).
`spine_top` 10.6 m ≈ 0.74·H, above the ~0.6·CH bar; taper is monotonic base→top (190→183→157→114 mm).
Marginal because the leader's *continuation into the upper crown* is thin and a little weak — it hands
off to the top scaffold rather than remaining a clearly dominant axis to ~75 % height (this is the
AC-12 apex residual, not an AC-1 fail). In the axial views (`fromtrunk_1`, `lookup`) everything
projects to a point at the trunk tip, but that is expected foreshortening in an up-the-trunk view and
is contradicted by the side views, so it is not single-point convergence.

### AC-2 — N scaffolds at well-separated heights — **PASS**
Judged from `transition_0/1` and `cmp_crown` row C. Scaffolds attach at y = 4.6 / 6.7 / 8.5 / 10.6 m
(spread ≈ 6 m ≈ 0.6·CH) at azimuths 0/138/275/52 — well separated in both height and angle. In the
transition close-ups I can see limbs leaving the trunk at *distinct points along its length*, not
bunched in one band. No two primaries share a near-identical height+angle.

### AC-3 — Near-trunk sparseness ("stand inside the tree") — **PASS (marginal)**
Judged from `fromtrunk_0/1`, `cmp_fromtrunk`, `lookup`. Near the trunk the viewer sees a *handful* of
clearly-separated proximal limbs with **real sky gaps between them** (`fromtrunk_0` is the clearest:
~4–5 limbs radiating, open sky close in). Innermost density bands are genuinely sparse (2, 11 tips).
This is the strongest, most tree-like framing in the set and it is why this is a PASS rather than a
FAIL. **Marginal** on one point: the spec's intent says *thick, legible* limbs; line C's proximal
limbs read **thin and wiry**, only slightly heavier than the twigs — nothing like the bold structural
limbs in the reference uplooking photo. Sparseness (the AC-3 metric core) is met; the missing *heft*
is a pipe-model/thickness question, flagged in §3 and escalated in §5.

### AC-4 — Distance-scaled branching density (monotone) — **PASS**
Metric 2→11→35→102→92 is monotone increasing to the shell peak (mild apex fall-off = AC-12,
acceptable). Visually confirmed in `fromtrunk_0` and `cmp_fromtrunk`: coarse/open near the axis,
progressively finer and denser toward the envelope. No inversion, no uniform-throughout density in
the near-trunk framing. (The *crown-view* framings look more uniformly dense — see §3 — but that is
the outer-shell tangle, and the radial gradient is real where it matters.)

### AC-5 — No structural artifacts — **PASS (all five sub-checks)**
- (i) thick-limb elbow: `transition_0/1` show no thick down-then-up chevron; worst thick-junction
  bend = 60° = the designed emergence angle. The 9 bends >150° are all on ~17 mm terminal twigs
  (AC-13 tip-jitter), not scaffolds. **PASS.**
- (ii) long straight edge: 0 non-trunk edges >3 m; the long horizontal rod in the crown/transition
  frames is the **trunk itself** rendered on its side by the camera framing (allowed). The big crown
  sweeps are curved and subdivided, not straight rods. **PASS.**
- (iii) node-collapse: min non-trunk edge 0.05 m, no zero-length/coincident nodes. **PASS.**
- (iv) loops: metric asserts acyclic. Visually, `crown_view2` (az 120°) and `cmp_crown` row C middle
  show a strong arc that *reads* like a near-closed ring — I judge this a projection overlap of two
  arcing branches, not a true rejoin, consistent with the acyclic metric. **PASS**, with a request in
  §4 to confirm.
- (v) single-point convergence: scaffolds originate at 4 distinct trunk nodes (transition shots).
  **PASS.**

### AC-6 — Emergent regularity, not hard caps — **PASS (visible signatures)**
Valence {1:576, 2:198, 3:20, 4:1}, %v1 72.5, sibling-angle min 22° — no witch's-broom, no
coincident-twig fan, no artificially fanned forks in any frame. Taper reads as pipe-model, not a
profile table. Whether the code contains a literal cap is a Planner design-review item, not a render
fail; nothing in the renders looks *clamped*.

### AC-7 — Reuse of validated data/components — **PASS (discipline)**
Submission uses 781-sprig cloud, seed 20260706, DBH/2 = 0.19 m root radius hit by the pipe model. No
unexplained modification noted. Satisfied by default.

### AC-8 — Performance ceiling >45 fps — **NOT MEASURED (deferred blocking gate)**
No fps figure supplied; node count 1037 is in line with prior line C. Per the spec this is run
at/near convergence, so its absence does not fail iteration 1 — but it is **blocking for
convergence** and remains unproven. Must run `scripts/perf_gate.sh` (real-park `--all-london-plane`)
at ramble + north_woods before this line can be declared done.

### AC-9 — Scaffold emergence variety — **residual (known-acceptable)**
Confirmed present: all four primaries leave at the same ~60° and arc similarly (`cmp_crown` row C,
`crown_view1/2`). Mechanically uniform. Non-blocking; feeds the AC-11 fix.

### AC-10 — Wedge-boundary reachability — **PASS (residual within tolerance)**
93.3 % ≥ 90 % threshold. Faint seam gaps expected under foliage but above the promote-to-blocking
line. Non-blocking.

### AC-11 — "Arcy" frontal read — **residual (known-acceptable) — but worse than spec anticipates**
See §3. Present and, unusually, *strongest at az 60°/120°* (`crown_view1`, `crown_view2`, `cmp_crown`
row C middle+right) rather than confined to head-on. Still non-blocking per its classification, but
this is the top next-fix. Flagged explicitly because it is the closest thing to a tree/not-tree
concern.

### AC-12 — Apex density — **residual (known-acceptable)**
Crown top reads slightly thin in `crown_view0` and `lookup`; density tails 102→92. Mild, not a void.
Non-blocking.

### AC-13 — Twig tip-jitter — **residual (known-acceptable)**
9 bends >150°, all on the thinnest terminal twigs; not visible as structural kinks. Cosmetic.

---

## 3. Defects the metrics missed (eye-only hunt)

- **Wiry-ball / nest gestalt in the full-crown framings.** `crown_view0` reads as "a ball of wire on
  a stick"; `crown_view1` and `crown_view2` read as "a nest of sweeping arcs." Against the reference
  photos (the majestic uplooking shot; the nyc11 full specimen) the defining feature — a dramatic
  **thick→medium→fine limb hierarchy** — is absent. Line C's limbs are nearly one gauge throughout;
  scaffolds are only marginally heavier than twigs. The metrics can't see this because taper *is*
  monotonic and valence *is* clean; the eye sees "no bold primaries." **This is the single biggest
  gap between line C and a real London plane.** It is a thickness/heft problem (pipe-model + small
  5 m crown packed with terminal twigs keeps scaffolds thin), not a topology problem.
- **Arcy meridian echo, multi-azimuth (AC-11).** Present, and *worse off-axis* than head-on — the
  opposite of the spec's expectation. From az 60°/120° line C's silhouette still rhymes with line B's
  lantern ribs. Foliage will hide most of it, but among the three "full-crown" standard framings, all
  three lean ball/arc rather than majestic-branching.
- **Radial-from-a-point in one near-trunk frame.** `fromtrunk_1` reads as the crown radiating from a
  single node at the trunk tip — a faint echo of B's cage — whereas `fromtrunk_0` reads correctly as
  trunk→few limbs→crown. The two near-trunk shots disagree; the structure is angle-sensitive.
- **NOT present (checked and cleared):**
  - Clustered/bunched scaffold origins — **no**, origins are spread over ~6 m of trunk.
  - Single-point convergence (pinned-fork hub) — **no**, 4 distinct origins (side views confirm).
  - Straight unnatural rods — **no** (the only long straight member is the trunk).
  - Thick-limb elbows — **no**.
  - Loops / self-rejoining — **no true loop** (acyclic; the az-120° "ring" is a projection overlap —
    confirm per §4).
  - Hollow-shell/lantern cage — **no**; line C has a real trunk with interior crossing branches and
    distinct origins, decisively past B's single-point lantern.
  - Uniform density where distance-scaling should apply — **only in the outer-shell tangle**; the
    near-trunk radial gradient is correct.

---

## 4. Where I'd need another render to be sure

- **AC-5(iv) loop confirm:** an orthographic *top-down* (plan) view of the wireframe, or the same
  az-120° crown view with each connected component / the four scaffold subtrees color-coded. The
  az-120° "ring" in `crown_view2` reads as a closed loop and I am inferring (from the acyclic metric)
  that it is two overlapping arcs. A colored or top-down frame would settle it directly rather than by
  trusting the metric.
- Not needed for the verdict, but would sharpen the AC-11/AC-3-heft discussion: **one foliated
  (leaf-clad) crown render** at az 0/60/120, to confirm the arcy/wiry-ball skeleton reads as an
  acceptable dome once cladded (the spec says judge skeleton, so this is optional, but it is the real
  question behind whether AC-11 truly stays cosmetic).

---

## 5. Prioritized defect list for the Engineer / Planner

1. **[AC-8, BLOCKING FOR CONVERGENCE — Engineer] Measure performance.** Run
   `scripts/perf_gate.sh` real-park `--all-london-plane` at ramble + north_woods; report median fps.
   Unproven >45 fps gate. Not a render fix; a required measurement before "done."
2. **[AC-11 + AC-9, top tuning residual — Engineer] Kill the multi-azimuth arcy read.** Add
   per-scaffold jitter on emergence elevation + mild gravity/light tropism in the core-crossing phase
   so the four primaries stop departing at an identical ~60° and arcing identically. Target: the
   az-60°/120° frames should read no more meridian-arced than head-on. "Make this specific defect go
   away" — Engineer-owned.
3. **[Cross-cutting "not majestic" — ESCALATE to Planner] Limb heft / bold-primary hierarchy.** The
   biggest gap to the reference photos is that scaffolds read as thin wire, not thick structural
   limbs. The spec has no AC that captures *absolute primary-limb thickness* — AC-4/AC-6 only demand
   monotone/emergent taper, which line C satisfies while still looking wiry. **Design question:** does
   the spec need an AC for primary-limb caliber (e.g. scaffold radius as a fraction of DBH at
   emergence), or is thin-limb-clad-in-foliage acceptable for the park-scale use? This is a spec gap,
   not a defect the current rubric blocks on — Planner call.
4. **[AC-5(iv) — Engineer, cheap] Produce the loop-confirm render** (top-down or component-colored) so
   the az-120° ring is provably a projection overlap, not a rejoin. Low effort, closes an ambiguity.
5. **[AC-12 — Engineer] Apex fill / leader continuation.** Add a short dedicated
   leader-continuation origin at `spine_top` so the crown top stops reading thin and the central axis
   stays dominant a touch higher. Known-acceptable; do after 2.
6. **[AC-13 — Engineer] Twig tip-jitter** — apply the core-crossing directional blend to shell twig
   tips. Cosmetic; lowest priority.

Items 2, 4, 5, 6 are "make this specific defect go away" Engineer fixes. Item 1 is a required
measurement. **Item 3 is the one design decision to escalate to the Planner** — it is the difference
between "reads as a tree" (achieved) and "reads as a *majestic London plane*" (not yet), and the
current spec does not adjudicate it.
