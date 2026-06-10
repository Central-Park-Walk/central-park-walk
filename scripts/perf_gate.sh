#!/usr/bin/env bash
# Perf gate — measures FPS at the 5 canonical test locations (docs/workflow.md §5).
#
# Usage:  scripts/perf_gate.sh [label]
#   label defaults to the current short commit hash.
#
# Runs the game windowed at 1920x1080 with vsync disabled, noon/clear/summer,
# stationary at each location. Parses the [PERF] log lines main.gd prints every
# 2s, discards the settle period, and reports median/min FPS and process ms.
# Report saved to perf_reports/<stamp>_<label>.txt (gitignored); summary on stdout.
#
# Target (docs/vision.md): 60 fps at 1080p on RTX 3060 Ti at ALL locations.

set -u
GODOT="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Frame rate is steady within seconds of load (verified 2026-06-09: clean 5-min
# Ramble run held 12-13fps throughout; an earlier "convergence to 35fps" was
# user camera interaction). Measure the LAST $MEASURE_SAMPLES samples (2s cadence).
RUN_SECONDS="${PERF_GATE_SECONDS:-60}"
MEASURE_SAMPLES=10
TARGET_FPS=60
# NOTE: a game window opens per location. Do NOT interact with it (F9,
# screenshots, movement contaminate the measurement).

LABEL="${1:-$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo nogit)}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$PROJECT_DIR/perf_reports"
mkdir -p "$OUT_DIR"
REPORT="$OUT_DIR/${STAMP}_${LABEL}.txt"

# name:x,z,yaw — the 5 canonical test locations
LOCATIONS=(
  "literary_walk:-600,1420,0"
  "bethesda:-480,1020,0"
  "ramble:-400,600,0"
  "great_lawn:-99,173,0"
  "north_woods:600,-1315,0"
)

echo "perf_gate: label=$LABEL  $(date -Iseconds)" | tee "$REPORT"
echo "settings: 1920x1080, vsync off, time=noon weather=clear season=summer, stationary" | tee -a "$REPORT"
printf "%-15s %8s %8s %8s %10s %8s\n" "location" "med_fps" "min_fps" "avg_fps" "process_ms" "samples" | tee -a "$REPORT"

overall_pass=1
for loc in "${LOCATIONS[@]}"; do
  name="${loc%%:*}"
  pos="${loc#*:}"
  log="$(mktemp)"
  timeout "${RUN_SECONDS}s" "$GODOT" --path "$PROJECT_DIR" \
    --resolution 1920x1080 --disable-vsync \
    -- --pos="$pos" --time=noon --weather=clear --season=summer \
    >"$log" 2>&1
  # [PERF] fps=42 process=23.1 physics=1.2 sub=3.20 unacc=19.9 overlay=OFF
  # Reject contaminated runs: overlay toggled ON means someone touched the window.
  if grep -F '[PERF]' "$log" | grep -q "overlay=ON"; then
    echo "WARN: $name run contaminated (overlay toggled mid-run) — rerun without touching the window" | tee -a "$REPORT"
    overall_pass=0
    rm -f "$log"
    continue
  fi
  stats="$(grep -F '[PERF]' "$log" | tail -"$MEASURE_SAMPLES" | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^fps=/)     { sub(/fps=/, "", $i);     fps[n] = $i + 0 }
        if ($i ~ /^process=/) { sub(/process=/, "", $i); psum += $i + 0 }
      }
      n++
    }
    END {
      if (n == 0) { print "0 0 0 0 0"; exit }
      # insertion sort for median
      for (i = 1; i < n; i++) { v = fps[i]; j = i - 1
        while (j >= 0 && fps[j] > v) { fps[j+1] = fps[j]; j-- } fps[j+1] = v }
      med = (n % 2) ? fps[int(n/2)] : (fps[n/2 - 1] + fps[n/2]) / 2
      s = 0; for (i = 0; i < n; i++) s += fps[i]
      printf "%.0f %.0f %.1f %.1f %d", med, fps[0], s / n, psum / n, n
    }')"
  read -r med minf avg pms nsamp <<<"$stats"
  if [ "$nsamp" -eq 0 ]; then
    echo "WARN: no [PERF] samples for $name — game failed to start? log tail:" | tee -a "$REPORT"
    tail -5 "$log" | tee -a "$REPORT"
    overall_pass=0
  else
    printf "%-15s %8s %8s %8s %10s %8s\n" "$name" "$med" "$minf" "$avg" "$pms" "$nsamp" | tee -a "$REPORT"
    awk -v m="$med" -v t="$TARGET_FPS" 'BEGIN { exit !(m < t) }' && overall_pass=0
  fi
  rm -f "$log"
done

if [ "$overall_pass" -eq 1 ]; then
  echo "RESULT: PASS (median >= ${TARGET_FPS} fps at all locations)" | tee -a "$REPORT"
else
  echo "RESULT: FAIL (target ${TARGET_FPS} fps median at all locations)" | tee -a "$REPORT"
fi
echo "report: $REPORT"
