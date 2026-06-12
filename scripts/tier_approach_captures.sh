#!/usr/bin/env bash
# Tier-approach continuity captures (walk-around 2026-06-11 #1).
#
# Reproduces the user's drive line: Conservatory Water → Belvedere,
# --pos=-53,884,11 (heading 11° ≈ toward (-11,670)), 13:00 clear July.
# Two walk-bot runs over the same 220 m line:
#   walk_default — shipped rendering
#   walk_nofog   — volumetric fog density zeroed (--fog-cal=:::0:)
# Analysis: scripts/tier_approach_check.py <dir> --compare <dir>
#   steps in BOTH runs   = tier handoff (impostor→lod2 ~250 m, lod2→near ~60 m)
#   trend/steps only in default = fog veil
#
# NOTE: windowed run — do not touch the game windows (headless is a dummy
# renderer, no screenshots; rendering.md §6b family gotcha).
set -u
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_BASE="notes/tier_approach"
POS="${POS:--53,884,11}"
TIME="${TIME:-13}"
SPEED=2.4      # m/s -> 2.4 m per frame at interval 1
DURATION=92    # 92 s * 2.4 = 220.8 m, the full user line
SETTLE=12

run_walk() { # name, extra args...
  local name="$1"; shift
  rm -rf "$PROJECT_DIR/$OUT_BASE/$name"
  mkdir -p "$PROJECT_DIR/$OUT_BASE/$name"
  echo "== walk: $name $* =="
  timeout $((DURATION + SETTLE + 150))s "$G" --path "$PROJECT_DIR" \
    --resolution 1920x1080 --disable-vsync \
    -- --pos="$POS" --time="$TIME" --weather=clear --season=summer \
    --walk --walk-speed=$SPEED --walk-duration=$DURATION --walk-interval=1 \
    --walk-settle=$SETTLE --walk-dir="$OUT_BASE/$name" "$@" \
    > "$PROJECT_DIR/$OUT_BASE/$name.log" 2>&1
  echo "   frames: $(ls "$PROJECT_DIR/$OUT_BASE/$name" | wc -l)"
}

run_walk walk_default
run_walk walk_nofog --fog-cal=:::0:

echo "analyze:"
echo "  python3 scripts/tier_approach_check.py $OUT_BASE/walk_default --compare $OUT_BASE/walk_nofog"
