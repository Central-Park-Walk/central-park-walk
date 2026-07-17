# STATE — cpw / tree-sculptor

**Target:** A shared-visible Blender sculptor that hand-authors London-plane form and compiles to game-ready GLBs.

## Now
- Thread live. Source authority: `models/tree_sources/london_plane.blend`.
- Visible bridge open: `blender4 … --python scripts/tree_sculpt/live_bridge.py`.
- Stages authored: young, mature, veteran + variants mature_open / mature_upright.
- Compiler path proven: Bézier → graph → `leafback_skinner` → cards → wind → GLB (~2s/stage).
- Appearance: first honest reference-overlay reviews exist; crown still thinner/more open than reference (not a realism PASS yet).
- Perf: isolated 240-tree Multimesh (no impostor/proxy) = **15 fps** on 3060 Ti after card budget thin. Full-park swap gate blocked by Auto-review; production `london_plane_{s,m,l}.glb` unchanged.

## Open worklist
1. `TS-1` Chris appearance verdict on `tmp/tree_sculpt/london_plane_mature_review.png`.
2. `TS-2` Fill crown mass by sculpting more secondaries (not denser cards) until reference massing holds.
3. `TS-3` Bake impostors for sculpted GLBs + run real 6808-tree park gate with temporary swap (needs approval).
4. `TS-4` Generalize workstation to a second species after London plane passes appearance.

## Next hypothesis
If secondary carriers are densified while keeping card sprays at budget 3, the crown will read continuous like the reference without returning to the 14-fps dense-card failure.
