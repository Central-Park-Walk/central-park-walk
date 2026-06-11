#!/usr/bin/env bash
# Sheep Meadow reference-comparison captures.
# Mirrors the views in notes/refs/sheep_meadow_FRlNuZ4zz8U/ (real-footage frames)
# so game output can be compared against ground truth, plus a 60 s forward-walk
# sampled at 0.3 s to expose motion effects stills can't show (wind flow, LOD/
# crossfade pops, grass swim, dapple movement).
#
# Conditions match the footage: midday, late summer, clear.
# Yaw: 0=N 90=W 180=S 270=E. Meadow bounds: X -900..-600, Z 1500(N)..2100(S).
set -u
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$PROJECT_DIR/notes/refs/sheep_meadow_game}"
mkdir -p "$OUT"

COND=(--time=13 --season=1.7 --weather=clear)

cap() { # name, then pose args
  local name="$1"; shift
  rm -f /tmp/godot_screenshot.png
  timeout 100s "$G" --path "$PROJECT_DIR" --resolution 1920x1080 --disable-vsync \
    -- --screenshot "${COND[@]}" "$@" \
    > "$OUT/$name.log" 2>&1
  if [ -f /tmp/godot_screenshot.png ]; then
    mv /tmp/godot_screenshot.png "$OUT/$name.png"
    echo "captured $name"
  else
    echo "FAIL $name (no screenshot, see $OUT/$name.log)"
  fi
}

# Stills mirroring the video views (timestamps refer to FRlNuZ4zz8U)
cap nw_across_meadow   --pos=-680,1900,45            # 0:50 — NW across meadow to tree line
cap w_cpw_treeline     --pos=-700,1750,90            # 2:08 — W: tree line + CPW behind
cap crown_at_edge      --pos=-650,1650,315           # 4:10 — single big crown at meadow edge
cap undercanopy_east   --pos=-620,1700,200           # 6:08 — under-canopy wear/shade zone
cap s_skyline_hero     --pos=-750,1560,180           # 8:08 — S across meadow, skyline behind
cap perimeter_path     --pos=-880,1800,250 --pitch=-2  # 9:28 — perimeter looking into meadow

# 60 s forward walk, south end heading north, sampled every 0.3 s (~200 frames)
WALK_DIR="notes/refs/sheep_meadow_game/walk"
mkdir -p "$PROJECT_DIR/$WALK_DIR"
timeout 200s "$G" --path "$PROJECT_DIR" --resolution 1920x1080 --disable-vsync \
  -- --walk --pos=-720,2020,0 "${COND[@]}" \
  --walk-duration=60 --walk-interval=0.3 --walk-speed=1.4 --walk-settle=12 \
  --walk-dir="$WALK_DIR" \
  > "$OUT/walk.log" 2>&1
echo "walk frames: $(ls "$PROJECT_DIR/$WALK_DIR"/walk_*.png 2>/dev/null | wc -l)"
echo DONE
