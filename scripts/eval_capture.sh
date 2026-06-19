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
