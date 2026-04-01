#!/bin/bash
# Regenerate all tree species, one species+tier at a time.
# Mtree mesher segfaults at certain seed+height combos, so isolating
# each run prevents one crash from killing the entire batch.

SPECIES="oak elm cathedral_elm maple pine cherry birch honeylocust callery_pear willow linden london_plane ginkgo magnolia deciduous"
TIERS="s m l"

cd "$(dirname "$0")/.."

for sp in $SPECIES; do
    for tier in $TIERS; do
        echo "=== Generating $sp $tier ==="
        timeout 120 blender4 --background --python scripts/generate_trees_mtree.py -- --species "$sp" --tier "$tier" 2>&1 | tail -8
        if [ $? -ne 0 ]; then
            echo "*** FAILED: $sp $tier (crash or timeout) ***"
        fi
        echo ""
    done
done

# Dead tree (no tiers)
echo "=== Generating dead tree ==="
timeout 60 blender4 --background --python scripts/generate_trees_mtree.py -- --species dead 2>&1 | tail -5

echo ""
echo "=== DONE ==="
