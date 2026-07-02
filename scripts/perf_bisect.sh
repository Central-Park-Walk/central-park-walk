#!/usr/bin/env bash
# Perf bisect — attributes frame cost to engine subsystems by A/B hiding them.
#
# Usage:  scripts/perf_bisect.sh <location> [config ...]
#   location: name:x,z,yaw (e.g. north_woods:600,-1315,0) or a known name
#   config:   label=diag-hide-list (e.g. noshadow=shadows) — defaults to the
#             full standard matrix when omitted.
#
# Each config is one 60s game run (same protocol as perf_gate.sh: 1080p,
# vsync off, noon/clear/summer, stationary; do NOT touch the windows).
# Reports median fps, process ms, viewport CPU ms, viewport GPU ms from the
# last 10 [PERF] samples. Report saved to perf_reports/ (gitignored).

set -u
GODOT="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_SECONDS="${PERF_GATE_SECONDS:-60}"
MEASURE_SAMPLES=10

declare -A KNOWN=(
  [literary_walk]="-600,1420,0"
  [bethesda]="-480,1020,0"
  [ramble]="-400,600,0"
  [great_lawn]="-99,173,0"
  [north_woods]="600,-1315,0"
)

LOC="${1:?usage: perf_bisect.sh <location> [label=hidelist ...]}"
shift || true
if [[ -n "${KNOWN[$LOC]:-}" ]]; then
  NAME="$LOC"; POS="${KNOWN[$LOC]}"
else
  NAME="${LOC%%:*}"; POS="${LOC#*:}"
fi

# Default matrix: baseline, each subsystem alone, post bundle, floor.
if [ "$#" -gt 0 ]; then
  CONFIGS=("$@")
else
  CONFIGS=(
    "baseline="
    "noshadow=shadows"
    "nosdfgi=sdfgi"
    "nofog=fog"
    "notrees=trees"
    "noundergrowth=undergrowth"
    "nograss=grass"
    "noterrain=terrain"
    "nopost=ssao,ssil,glow"
    "floor=terrain,trees,undergrowth,grass,shadows,sdfgi,fog,ssao,ssil,glow"
  )
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
LABEL="$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo nogit)"
OUT_DIR="$PROJECT_DIR/perf_reports"
mkdir -p "$OUT_DIR"
REPORT="$OUT_DIR/${STAMP}_bisect_${NAME}_${LABEL}.txt"

echo "perf_bisect: $NAME ($POS)  commit=$LABEL  $(date -Iseconds)" | tee "$REPORT"
echo "settings: 1920x1080, vsync off, noon/clear/summer, stationary, ${RUN_SECONDS}s/config" | tee -a "$REPORT"
printf "%-15s %8s %10s %8s %8s %8s %8s %9s %9s %8s %9s %8s\n" "config" "med_fps" "process_ms" "pmax" "pspk" "vpcpu" "vpgpu" "vistri_M" "shtri_M" "mrgpu" "mrtri_M" "samples" | tee -a "$REPORT"

for cfg in "${CONFIGS[@]}"; do
  label="${cfg%%=*}"
  hides="${cfg#*=}"
  extra=()
  if [ -n "$hides" ]; then
    # Value starting with -- is passed through as raw CLI args (space-separated);
    # otherwise it's a --diag-hide list. e.g. dist75=--shadow-dist=75
    if [[ "$hides" == --* ]]; then
      read -r -a extra <<<"$hides"
    else
      extra=("--diag-hide=$hides")
    fi
  fi
  log="$(mktemp)"
  timeout "${RUN_SECONDS}s" "$GODOT" --path "$PROJECT_DIR" \
    --resolution 1920x1080 --disable-vsync \
    -- --pos="$POS" --time=noon --weather=clear --season=summer "${extra[@]+"${extra[@]}"}" \
    >"$log" 2>&1
  if grep -F '[PERF]' "$log" | grep -q "overlay=ON"; then
    echo "WARN: $label contaminated (overlay toggled mid-run) — rerun" | tee -a "$REPORT"
    rm -f "$log"; continue
  fi
  stats="$(grep -F '[PERF]' "$log" | tail -"$MEASURE_SAMPLES" | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^fps=/)     { sub(/fps=/, "", $i);     fps[n] = $i + 0 }
        if ($i ~ /^process=/) { sub(/process=/, "", $i); psum += $i + 0 }
        if ($i ~ /^pmax=/)    { sub(/pmax=/, "", $i);    if ($i + 0 > pmax) pmax = $i + 0 }
        if ($i ~ /^pspk=/)    { sub(/pspk=/, "", $i);    spksum += $i + 0 }
        if ($i ~ /^vpcpu=/)   { sub(/vpcpu=/, "", $i);   csum += $i + 0 }
        if ($i ~ /^vpgpu=/)   { sub(/vpgpu=/, "", $i);   gsum += $i + 0 }
        if ($i ~ /^vistri=/)  { sub(/vistri=/, "", $i);  vtsum += $i + 0 }
        if ($i ~ /^shtri=/)   { sub(/shtri=/, "", $i);   stsum += $i + 0 }
        if ($i ~ /^mrgpu=/)   { sub(/mrgpu=/, "", $i);   mgsum += $i + 0 }
        if ($i ~ /^mrtri=/)   { sub(/mrtri=/, "", $i);   mtsum += $i + 0 }
      }
      n++
    }
    END {
      if (n == 0) { print "0 0 0 0 0 0 0 0 0"; exit }
      for (i = 1; i < n; i++) { v = fps[i]; j = i - 1
        while (j >= 0 && fps[j] > v) { fps[j+1] = fps[j]; j-- } fps[j+1] = v }
      med = (n % 2) ? fps[int(n/2)] : (fps[n/2 - 1] + fps[n/2]) / 2
      printf "%.0f %.1f %.1f %.0f %.1f %.1f %.2f %.2f %.1f %.2f %d", med, psum / n, pmax, spksum, csum / n, gsum / n, vtsum / n / 1e6, stsum / n / 1e6, mgsum / n, mtsum / n / 1e6, n
    }')"
  read -r med pms pmx spk cms gms vtm stm mgm mtm nsamp <<<"$stats"
  if [ "$nsamp" -eq 0 ]; then
    echo "WARN: no [PERF] samples for $label — log tail:" | tee -a "$REPORT"
    tail -5 "$log" | tee -a "$REPORT"
  else
    printf "%-15s %8s %10s %8s %8s %8s %8s %9s %9s %8s %9s %8s\n" "$label" "$med" "$pms" "$pmx" "$spk" "$cms" "$gms" "$vtm" "$stm" "$mgm" "$mtm" "$nsamp" | tee -a "$REPORT"
  fi
  rm -f "$log"
done
echo "report: $REPORT"
