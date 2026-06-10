#!/usr/bin/env bash
# Capture set for shadow-proxy default-on DoD (docs/trees.md §3):
#   SDFGI on/off × proxies on/off at Ramble (GI A/B, DoD item 4)
#   Literary Walk noon, proxies on/off (vase-elm crown fit / light leak)
#   Ramble winter, proxies on/off (phenology shed = trunk-only shadows)
# Each run loads the full scene (~40 s) and auto-captures at +8 s.
set -u
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-/tmp/proxy_ab}"
mkdir -p "$OUT"

cap() { # name, then all remaining args passed through
  local name="$1"; shift
  rm -f /tmp/godot_screenshot.png
  timeout 80s "$G" --path "$PROJECT_DIR" --resolution 1920x1080 --disable-vsync \
    -- --screenshot --time=noon --weather=clear "$@" \
    > "$OUT/$name.log" 2>&1
  if [ -f /tmp/godot_screenshot.png ]; then
    mv /tmp/godot_screenshot.png "$OUT/$name.png"
    echo "captured $name"
  else
    echo "FAIL $name (no screenshot)"
  fi
}

R="--pos=-400,600,0"     # ramble
L="--pos=-600,1420,0"    # literary walk

cap ramble_nop_gion    $R --season=summer
cap ramble_nop_gioff   $R --season=summer --diag-hide=sdfgi
cap ramble_prox_gion   $R --season=summer --tree-shadow-proxy
cap ramble_prox_gioff  $R --season=summer --tree-shadow-proxy --diag-hide=sdfgi
cap litwalk_nop        $L --season=summer
cap litwalk_prox       $L --season=summer --tree-shadow-proxy
cap ramble_wint_nop    $R --season=winter
cap ramble_wint_prox   $R --season=winter --tree-shadow-proxy
echo DONE
