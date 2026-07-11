# ⛔ The leaf-back line is DEPRECATED — read this before opening any `leafback_*` file

**Deprecated 2026-07-09. Do not implement anything in these documents.**
The live tree generator is the **developmental grower**: `scripts/plane_grower.py`,
specified in [`grower_reiterate_design.md`](grower_reiterate_design.md).

## What leaf-back was, and why it died

Leaf-back filled a crown *envelope* with leaf/sprig cards and then connected them inward to
a trunk. It went merge → space-colonization → trunk-scaffold, and its metrics kept passing.

It died for the reason that became **Standing Rule 3**: it was a **snapshot, not a process.**
It fitted an appearance instead of producing one, and it read as a wire cage — a hanging
basket — from every angle, because nothing about it had been *grown* by anything. (It also
failed the AC-8 perf gate ~5×, but that was the symptom, not the disease.)

**It was not wrong, and it is not wasted.** It produced the per-tier crown envelopes we still
use as growth boundaries, it forced the "depth is an OUTPUT, not a parameter" lesson (learned
4× since), and its Critic failure produced the post-mesh integrity gate that is now the
Engineer's definition of done. Superseded is the good outcome for a scaffold.

## ✅ What SURVIVED — still live, still used

| File | Why it lives |
| --- | --- |
| **`scripts/leafback_skinner.py`** | **The production skinner.** Generator-agnostic: it consumes a `(pos, parent, radius, strand, root)` graph and derives all 5 contract attributes itself. **The grower emits exactly that shape** — this is its downstream mesh path, unchanged. *A skeleton is a skeleton; the `leafback` in the filename is now a historical artifact.* |
| `scripts/leafback_graph.py`, `scripts/leafback_skeleton.py` | Hold the per-tier crown **envelope tables** (Ovoid / Dome / Spread, from the iNat measurements). These survive as **growth boundaries and validation checkpoints** for the grower. Frozen — do not edit. |
| The measured envelopes, DBH/height/tier distributions | Validation targets for the grower's *outputs*. |

## ⛔ What DIED

Leaves-as-attractors · the persisted leaf field · the World-A/World-B framing · clumping and
margin terms · `dk` as an economy knob · the unforked core-crossing leader (the "garden-hose
arc") · shell-only attractor placement (the "lantern") · AC-14's `w^(p/2)` growth partition
(diagnosed as a **clock substitute** — a one-shot grower can't let a low limb *earn* its
caliber, so it was handed the answer).

**⛔ The generator wiring is NOT on master, deliberately.** `generate_trees_mtree.py`'s
`leafback_skeleton: True` path routes London plane through the failed pipeline. It lives only
on the **`leafback-archive`** branch. London plane stays on Mtree until the grower passes its
5 criteria — the project's own rule is *no mesh, no perf, no cards until then*.

## Where the reasoning lives

The full record — the pipeline, the Critic protocol, the mesh-disconnection diagnosis, the
LOD0 density escalation, the topology redesign, the planner spec — is kept in this directory
as **history**, and the complete working tree as it stood at deprecation is on the
**`leafback-archive`** branch. Read it to understand *why* the grower is shaped the way it
is. Do not read it for a plan.
