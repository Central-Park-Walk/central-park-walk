#!/usr/bin/env bash
# Cloud flow flip-book: fixed pose, one frame every few seconds of real
# time. Verifies clouds TRANSLATE with the wind rather than churning
# through their own shapes (2026-06-11 flow fix; reference:
# cp_clouds_UXNL4CTVq-Y time-lapse). Walk bot at ~zero speed = stationary
# camera with interval captures.
# Usage: scripts/cloud_flow_check.sh [outdir-under-project] [extra args...]
set -u
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-notes/flow_check}"
shift || true
rm -rf "$PROJECT_DIR/$OUT"
timeout 200s "$G" --path "$PROJECT_DIR" --resolution 1280x720 --disable-vsync \
  -- --pos=-99,173,-90 --pitch=20 --time=12 --weather=clear --cloud-seed=7 \
  --walk --walk-speed=0.01 --walk-interval=5 --walk-duration=100 \
  --walk-dir="$OUT" "$@" 2>&1 | grep -E "Walk bot|FAILED|ERROR" | tail -5
ls "$PROJECT_DIR/$OUT"/*.png 2>/dev/null | wc -l
