#!/usr/bin/env bash
# Perf gate — measures FPS at the 5 canonical test locations (docs/workflow.md §5).
#
# Usage:  scripts/perf_gate.sh [label]
#   label defaults to the current short commit hash.
#
# SCENE (2026-07-04): runs the REAL, fully-populated park by default —
#   --park --all-london-plane → 6808 tree instances, matching what `bin/walk`
#   (and a player) actually sees. This was a silent bug until 2026-07-04: the
#   gate omitted --all-london-plane, so it measured only 1892 trees (~28% of the
#   park, non-london-plane species have no built model → dropped) and every
#   historical gate number (e.g. the 2026-07-01 "ramble 73") is that LIGHT scene,
#   NOT the real park. See project_performance_investigation.md.
#
#   PERF_GATE_LIGHT=1 restores the old 1892-tree diagnostic scene (no
#   --all-london-plane). Use it ONLY to reproduce/compare pre-2026-07-04 numbers;
#   it is NOT the real park and must never be the number you ship against.
#
# The tree count (lod0/impostor instances, same source as the F9 HUD =
# tb.lod0_instances, printed by tree_builder.gd:1207-1217) is logged for EVERY
# location so a wrong-scene run can never again pass unnoticed.
#
# Runs windowed at 1920x1080, vsync disabled, noon/clear/summer, stationary.
# Parses the [PERF] log lines main.gd prints every 2s, discards the settle
# period, reports median/min FPS + process ms + tree counts. Report saved to
# perf_reports/<stamp>_<label>.txt (gitignored); summary on stdout.
#
# Target (docs/vision.md): 60 fps at 1080p on RTX 3060 Ti at the open locations
# (literary_walk, bethesda, great_lawn); 45 fps floor in deep woodland (ramble,
# north_woods) — user decision 2026-06-11. NOTE: these targets predate the
# scene fix; on the real 6808-tree park the open targets will likely fail —
# that is honest, not a regression. Revisit the thresholds with the user.

set -u
GODOT="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Frame rate is steady within seconds of load (verified 2026-06-09: clean 5-min
# Ramble run held 12-13fps throughout; an earlier "convergence to 35fps" was
# user camera interaction). Measure the LAST $MEASURE_SAMPLES samples (2s cadence).
RUN_SECONDS="${PERF_GATE_SECONDS:-60}"
MEASURE_SAMPLES=10
TARGET_FPS=60
# Deep woodland (ramble, north_woods) floor — user decision 2026-06-11 (vision.md).
WOODLAND_TARGET_FPS=45
target_for() { case "$1" in ramble|north_woods) echo "$WOODLAND_TARGET_FPS" ;; *) echo "$TARGET_FPS" ;; esac }

# --- Scene config: real park by default, opt-in light diagnostic scene ---------
if [ "${PERF_GATE_LIGHT:-0}" = "1" ]; then
  SCENE_FLAGS="--park"
  SCENE_DESC="LIGHT DIAGNOSTIC (1892-tree, no --all-london-plane — NOT the real park)"
  EXPECT_TREES=1892
else
  SCENE_FLAGS="--park --all-london-plane"
  SCENE_DESC="REAL PARK (--park --all-london-plane, ~6808 trees)"
  EXPECT_TREES=6808
fi
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
echo "scene: $SCENE_DESC" | tee -a "$REPORT"
echo "settings: 1920x1080, vsync off, time=noon weather=clear season=summer, stationary" | tee -a "$REPORT"
printf "%-15s %8s %8s %8s %10s %8s %14s\n" "location" "med_fps" "min_fps" "avg_fps" "process_ms" "samples" "trees_l0/imp" | tee -a "$REPORT"

# Pull the built tree-instance counts from a location log (same numbers the F9
# HUD shows: tb.lod0_instances / tb.impostor_instances; tree_builder.gd:1207-1217).
tree_count() {  # $1=log field: "mesh" or "impostor"
  local pat; [ "$1" = "mesh" ] && pat="Trees mesh tier:" || pat="Trees impostor tier:"
  grep -F "$pat" "$2" | tail -1 | sed -nE 's/.*MMIs \/ ([0-9]+) instances.*/\1/p'
}

overall_pass=1
for loc in "${LOCATIONS[@]}"; do
  name="${loc%%:*}"
  pos="${loc#*:}"
  log="$(mktemp)"
  timeout "${RUN_SECONDS}s" "$GODOT" --path "$PROJECT_DIR" \
    --resolution 1920x1080 --disable-vsync \
    -- $SCENE_FLAGS --pos="$pos" --time=noon --weather=clear --season=summer \
    >"$log" 2>&1
  # [PERF] fps=42 process=23.1 physics=1.2 sub=3.20 unacc=19.9 overlay=OFF
  # Reject contaminated runs: overlay toggled ON means someone touched the window.
  if grep -F '[PERF]' "$log" | grep -q "overlay=ON"; then
    echo "WARN: $name run contaminated (overlay toggled mid-run) — rerun without touching the window" | tee -a "$REPORT"
    overall_pass=0
    rm -f "$log"
    continue
  fi
  tl0="$(tree_count mesh "$log")"; tl0="${tl0:-?}"
  timp="$(tree_count impostor "$log")"; timp="${timp:-?}"
  # Catch the silent wrong-scene failure this whole gate exists to prevent.
  if [ "$tl0" != "?" ] && [ "$tl0" -lt $((EXPECT_TREES * 3 / 4)) ]; then
    echo "WARN: $name built $tl0 lod0 trees, expected ~$EXPECT_TREES for scene '$SCENE_DESC' — WRONG SCENE / build failure. FPS below is NOT trustworthy." | tee -a "$REPORT"
    overall_pass=0
  fi
  stats="$(grep -F '[PERF]' "$log" | tail -"$MEASURE_SAMPLES" | awk '
    {
      # Skip truncated final line (timeout SIGTERM mid-print → fps=0/vistri=0).
      keep = 0
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^fps=/)     { sub(/fps=/, "", $i);     ff = $i + 0; if (ff > 0) keep = 1 }
        if ($i ~ /^process=/) { sub(/process=/, "", $i); pp = $i + 0 }
      }
      if (keep) { fps[n] = ff; psum += pp; n++ }
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
    printf "%-15s %8s %8s %8s %10s %8s %14s\n" "$name" "$med" "$minf" "$avg" "$pms" "$nsamp" "$tl0/$timp" | tee -a "$REPORT"
    awk -v m="$med" -v t="$(target_for "$name")" 'BEGIN { exit !(m < t) }' && overall_pass=0
  fi
  rm -f "$log"
done

if [ "$overall_pass" -eq 1 ]; then
  echo "RESULT: PASS (median >= ${TARGET_FPS} fps open / >= ${WOODLAND_TARGET_FPS} fps woodland)  [scene: $SCENE_DESC]" | tee -a "$REPORT"
else
  echo "RESULT: FAIL (target ${TARGET_FPS} fps open / ${WOODLAND_TARGET_FPS} fps woodland, median)  [scene: $SCENE_DESC]" | tee -a "$REPORT"
fi
echo "report: $REPORT"
