#!/usr/bin/env bash
# Headless eval-plot capture for single-species model review.
#
# Renders the Great Lawn eval plot (eval_plot_builder.gd) for one species and
# saves stills from a few canned vantage points (overview / mid / closeup).
#
# CRITICAL (2026-06-19): the default FSR2 temporal upscaler makes
# get_viewport().get_texture().get_image() HANG under xvfb (no frame resolves,
# process never quits, no PNG). Disable it with --upscale=bilinear:1.0 for any
# headless capture. Confirmed working: RTX 3060 Ti + Vulkan under xvfb-run.
#
# Usage:
#   scripts/eval_capture.sh <species> [outdir] [time] [season]
# Example:
#   scripts/eval_capture.sh london_plane notes/london_plane_eval 13 summer
set -u
SPECIES="${1:?usage: eval_capture.sh <species> [outdir] [time] [season]}"
OUT="${2:-notes/${SPECIES}_eval}"
TIME="${3:-13}"
SEASON="${4:-summer}"
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$PROJECT_DIR/$OUT"

# CRITICAL (2026-06-21, CORRECTED): tree GEOMETRY loads via tree_builder ->
# park_loader._load_glb_scene -> load("res://models/trees/<sp>.glb"), which goes
# through Godot's IMPORT system and returns .godot/imported/<glb>-<hash>.scn — NOT
# GLTFDocument on the raw GLB (the earlier note here claimed GLTFDocument; that was
# WRONG and cost an entire session of stale "identical" renders: the .scn stayed
# at the pre-regen mtime, so every regen was invisible). So a Blender regen of a
# tree GLB requires `godot --import` to refresh the .scn BEFORE the runtime cache
# can pick it up. Two steps, both required:
#   1) re-import so the .scn matches the new GLB,
#   2) drop the runtime .res cache so it rebuilds from the fresh .scn.
# (The runtime .res cache mtime-stamp self-invalidation still helps, but it rebuilds
# from the .scn — so without step 1 it faithfully rebuilds STALE geometry.)
G_IMPORT="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
echo "re-importing changed resources (.glb -> .scn) ..."
timeout 580 xvfb-run -a -s "-screen 0 1920x1080x24" "$G_IMPORT" --headless --import \
  --path "$PROJECT_DIR" > /tmp/eval_import.log 2>&1 && echo "import done" || echo "import WARN (see /tmp/eval_import.log)"
TREE_CACHE="$HOME/.local/share/godot/app_userdata/Central Park Walk/cache/trees"
if [ -d "$TREE_CACHE" ]; then
  # find -delete (NOT rm with a quoted-prefix glob — that silently matched nothing
  # on the spaced path and left a stale cache; 2026-06-21). Verify the count.
  find "$TREE_CACHE" -name "${SPECIES}_*.res" -delete
  find "$TREE_CACHE" -name "${SPECIES}.cfg" -delete
  echo "cleared runtime tree cache for $SPECIES ($(find "$TREE_CACHE" -name "${SPECIES}_*.res" | wc -l) .res remain)"
fi

# Stand-mode layout (single matched species): size-graded specimen row at Z=150,
# 3x3 grove at Z=80, default spawn faces north (yaw 0 -> -Z) from Z=308.
# pose = "x,z,yaw"
declare -A POSES=(
  [overview]="-99,308,0"   # whole plot: size-graded row + grove, labels
  [mid]="-99,190,0"        # ~40m from the specimen row — full trees
  [closeup]="-99,168,0"    # ~18m from the row — bark + leaf detail
)

cap() { # name pose
  local name="$1" pose="$2"
  rm -f /tmp/eval_shot.png
  timeout 200s xvfb-run -a -s "-screen 0 1920x1080x24" "$G" --path "$PROJECT_DIR" \
    --resolution 1920x1080 --disable-vsync \
    -- --screenshot --screenshot-file=/tmp/eval_shot.png \
    --upscale=bilinear:1.0 --eval-plot="$SPECIES" --pos="$pose" \
    --time="$TIME" --weather=clear --season="$SEASON" --cloud-seed=1 \
    > "$PROJECT_DIR/$OUT/$name.log" 2>&1
  if [ -f /tmp/eval_shot.png ]; then
    mv /tmp/eval_shot.png "$PROJECT_DIR/$OUT/$name.png"
    echo "captured $name ($pose)"
  else
    echo "FAIL $name — no screenshot (see $OUT/$name.log)"
  fi
}

for n in overview mid closeup; do
  cap "$n" "${POSES[$n]}"
done
echo "done -> $OUT/"
