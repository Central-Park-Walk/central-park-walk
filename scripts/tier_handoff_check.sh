#!/usr/bin/env bash
# Mesh↔impostor handoff DoD (docs/trees.md §2 item 1, §4d): capture each
# tier pure (--tier-isolate) plus a no-trees plate at a viewpoint with
# canopy at the ~240m handoff, then report mean |ΔRGB| over canopy pixels.
# Usage: scripts/tier_handoff_check.sh [pos] [time ...]
#   pos default: bethesda yaw 0 (-480,1020,0 — tree band at 220-290m)
#   times default: noon (pass e.g. "8 12 17" for the full §2 matrix)
set -u
G="${GODOT:-/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
POS="${1:--480,1020,0}"
shift || true
TIMES=("${@:-12}")
OUT=/tmp/tier_handoff
mkdir -p "$OUT"

cap() { # name, extra args...
  local name="$1"; shift
  rm -f /tmp/godot_screenshot.png
  timeout 80s "$G" --path "$PROJECT_DIR" --resolution 1920x1080 --disable-vsync \
    -- --screenshot --pos="$POS" --weather=clear --season=summer "$@" \
    > "$OUT/$name.log" 2>&1
  if [ -f /tmp/godot_screenshot.png ]; then
    mv /tmp/godot_screenshot.png "$OUT/$name.png"; echo "captured $name"
  else
    echo "FAIL $name"; fi
}

for t in "${TIMES[@]}"; do
  cap "mesh_$t"     --time="$t" --tier-isolate=mesh
  cap "impostor_$t" --time="$t" --tier-isolate=impostor
  cap "notrees_$t"  --time="$t" --diag-hide=trees
done

python3 - "$OUT" "${TIMES[@]}" <<'EOF'
import sys
import numpy as np
from PIL import Image

out = sys.argv[1]
def load(n):
    return np.asarray(Image.open(f"{out}/{n}.png").convert('RGB'), dtype=np.float32) / 255.0

for t in sys.argv[2:]:
    mesh, imp, plate = load(f"mesh_{t}"), load(f"impostor_{t}"), load(f"notrees_{t}")
    mmask = np.abs(mesh - plate).mean(axis=2) > 0.02
    imask = np.abs(imp - plate).mean(axis=2) > 0.02
    both = mmask & imask
    union = mmask | imask
    iou = both.sum() / max(union.sum(), 1)
    d = np.abs(mesh - imp).mean(axis=2)[both]
    gr_mesh = (mesh[..., 1] - mesh[..., 0])[both].mean()
    gr_imp = (imp[..., 1] - imp[..., 0])[both].mean()
    print(f"t={t}h  canopy px={both.sum()}  mean|dRGB|={d.mean():.4f}  "
          f"p95={np.percentile(d, 95):.4f}  silhouette IoU={iou:.2f}  "
          f"G-R mesh={gr_mesh:+.3f} imp={gr_imp:+.3f} "
          f"({'sign OK' if gr_mesh * gr_imp >= 0 else 'HUE FLIP'})")
    print(f"  DoD: mean<0.05 -> {'PASS' if d.mean() < 0.05 else 'FAIL'}")
EOF
