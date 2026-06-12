#!/usr/bin/env bash
# Sky capture set: cloud shape (noon) + dawn/dusk color sweep.
# Usage: scripts/sky_captures.sh [outdir] [extra godot args...]
#   scripts/sky_captures.sh /tmp/sky_before
#   scripts/sky_captures.sh /tmp/sky_after --cloud-seed=7
# Poses: Great Lawn center (open dome) looking E and W so dawn/dusk sweeps
# face the sun side; noon shape shots use both + a pitched-up sky shot.
# Each run loads the full scene (~40 s) and auto-captures at +8 s.
set -u
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-/tmp/sky_captures}"
shift || true
mkdir -p "$OUT"

cap() { # name, then all remaining args passed through
  local name="$1"; shift
  rm -f /tmp/godot_screenshot.png
  timeout 80s "$G" --path "$PROJECT_DIR" --resolution 1920x1080 --disable-vsync \
    -- --screenshot --weather=clear --season=summer --cloud-seed=7 "$@" \
    > "$OUT/$name.log" 2>&1
  if [ -f /tmp/godot_screenshot.png ]; then
    mv /tmp/godot_screenshot.png "$OUT/$name.png"
    echo "captured $name"
  else
    echo "FAIL $name (no screenshot)"
  fi
}

GL_E="--pos=-99,173,90"    # Great Lawn, facing east (dawn side)
GL_W="--pos=-99,173,-90"   # Great Lawn, facing west (dusk side)

# Cloud shape (noon)
cap noon_sky_up    $GL_W --time=12 --pitch=25 "$@"
cap noon_eye_w     $GL_W --time=12 --pitch=8  "$@"
cap noon_eye_e     $GL_E --time=12 --pitch=8  "$@"

# Dawn sweep (sun rises ENE; yaw -100..-95 in keyframes → screen east)
for t in 5.0 5.3 5.6 5.9 6.2 6.5; do
  cap "dawn_${t}" $GL_E --time=$t --pitch=12 "$@"
done

# Dusk sweep (sun sets W; keyframe yaw 95)
for t in 19.0 19.5 19.8 20.1 20.4 20.7 21.0; do
  cap "dusk_${t}" $GL_W --time=$t --pitch=12 "$@"
done
echo DONE
