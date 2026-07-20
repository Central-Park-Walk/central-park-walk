#!/usr/bin/env python3
"""Inkscape habit traces → world-space primary polylines (photo-match authority).

Chris W-37: W-36/W-37 procedural scaffolds "not matching at all" — use Inkscape
on the locked plates. One SVG per stage under ``traces/``; path ``id``s are
named primaries. Front-plate mapping: SVG +x → world +X, SVG −y → world +Z
(camera looks from −Y). Optional ``data-y`` on a path sets constant world Y
depth; otherwise Y ≈ 0.12·X so the scaffold is not paper-thin.

Inkscape (flatpak): ``flatpak run org.inkscape.Inkscape``
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from habit_refs import STAGE_REFS

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
REF_DIR = PROJ / "tmp" / "tree_sculpt" / "habit_refs"
TRACE_DIR = HERE / "traces"
INKSCAPE = ["flatpak", "run", "org.inkscape.Inkscape"]

# Plate pixels (must match ref_habit_overlay._fit cell size).
PLATE = 640

# Model crown height (m) used to scale plate → world. Scaffold tips land near this.
STAGE_HEIGHT_M = {
    "young": 10.5,
    "mature": 12.8,
    "veteran": 14.6,
}

NS = {"svg": "http://www.w3.org/2000/svg"}


def inkscape_bin() -> list[str]:
    return list(INKSCAPE)


def ensure_plate(stage: str) -> Path:
    plate = REF_DIR / f"{stage}_ref_plate.png"
    if not plate.is_file():
        raise FileNotFoundError(f"missing {plate}; run ref_habit_overlay.py first")
    return plate


def write_template_svg(stage: str, force: bool = False) -> Path:
    """SVG with linked plate + empty guide paths for hand-tracing in Inkscape."""
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    out = TRACE_DIR / f"{stage}_primaries.svg"
    if out.is_file() and not force:
        return out
    plate = ensure_plate(stage)
    # Relative href from traces/ → tmp/... (Inkscape resolves vs SVG location).
    href = Path(os_relpath(plate, TRACE_DIR))
    # Seed empty named paths near bole so the Layers panel lists them.
    guides = {
        "young": ["trunk", "tier1", "tier2", "tier3", "tier4", "tier5", "tier6", "tier7"],
        "mature": ["trunk", "west_low", "east_low", "north_mid", "south_mid", "crown_reiterate"],
        "veteran": ["trunk", "v_west", "v_east", "v_north", "v_south", "v_crown"],
    }[stage]
    path_xml = []
    for i, sid in enumerate(guides):
        # Placeholder stubs (replaced by authored d= in the committed SVGs).
        x0, y0 = 320, 600 - i * 8
        path_xml.append(
            f'    <path id="{sid}" class="primary" data-role="primary" '
            f'style="fill:none;stroke:#00e5ff;stroke-width:3;stroke-linecap:round" '
            f'd="M {x0},{y0} L {x0},{y0 - 20}"/>'
        )
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{PLATE}" height="{PLATE}" viewBox="0 0 {PLATE} {PLATE}">
  <title>habit primary traces · {stage} · {STAGE_REFS[stage]['file']}</title>
  <desc>{STAGE_REFS[stage]['why']} Trace visible heavy wood only. Path ids are strand ids.</desc>
  <image id="ref_plate" x="0" y="0" width="{PLATE}" height="{PLATE}"
         xlink:href="{href.as_posix()}" preserveAspectRatio="none"/>
  <g id="primaries" inkscape:label="primaries" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
{chr(10).join(path_xml)}
  </g>
</svg>
"""
    out.write_text(svg)
    return out


def os_relpath(target: Path, start: Path) -> str:
    return Path(os_path_rel(target, start)).as_posix()


def os_path_rel(target: Path, start: Path) -> str:
    import os

    return os.path.relpath(target, start)


_CMD_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)


def _polygonize_path_d(d: str) -> list[tuple[float, float]]:
    """Flatten SVG path to a polyline (absolute coords). Enough for M/L/C/Q/S/H/V/Z."""
    tokens = [t for t in _CMD_RE.findall(d) if t[0] or t[1]]
    pts: list[tuple[float, float]] = []
    cx = cy = 0.0
    start = (0.0, 0.0)
    i = 0
    flat: list[str] = []
    for cmd, num in tokens:
        if cmd:
            flat.append(cmd)
        else:
            flat.append(num)
    while i < len(flat):
        t = flat[i]
        if t.isalpha():
            cmd = t
            i += 1
        else:
            cmd = "L"
        rel = cmd.islower()
        cmd = cmd.upper()

        def num():
            nonlocal i
            v = float(flat[i])
            i += 1
            return v

        if cmd == "M":
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            cx, cy = x, y
            start = (cx, cy)
            pts.append((cx, cy))
            while i < len(flat) and not flat[i].isalpha():
                x, y = num(), num()
                if rel:
                    x, y = cx + x, cy + y
                cx, cy = x, y
                pts.append((cx, cy))
        elif cmd == "L":
            while i < len(flat) and not flat[i].isalpha():
                x, y = num(), num()
                if rel:
                    x, y = cx + x, cy + y
                cx, cy = x, y
                pts.append((cx, cy))
        elif cmd == "H":
            while i < len(flat) and not flat[i].isalpha():
                x = num()
                cx = cx + x if rel else x
                pts.append((cx, cy))
        elif cmd == "V":
            while i < len(flat) and not flat[i].isalpha():
                y = num()
                cy = cy + y if rel else y
                pts.append((cx, cy))
        elif cmd == "C":
            while i < len(flat) and not flat[i].isalpha():
                x1, y1, x2, y2, x, y = num(), num(), num(), num(), num(), num()
                if rel:
                    x1, y1 = cx + x1, cy + y1
                    x2, y2 = cx + x2, cy + y2
                    x, y = cx + x, cy + y
                # Sample cubic.
                p0 = (cx, cy)
                for k in (1, 2, 3):
                    t = k / 3.0
                    u = 1.0 - t
                    px = u**3 * p0[0] + 3 * u**2 * t * x1 + 3 * u * t**2 * x2 + t**3 * x
                    py = u**3 * p0[1] + 3 * u**2 * t * y1 + 3 * u * t**2 * y2 + t**3 * y
                    pts.append((px, py))
                cx, cy = x, y
        elif cmd == "Q":
            while i < len(flat) and not flat[i].isalpha():
                x1, y1, x, y = num(), num(), num(), num()
                if rel:
                    x1, y1 = cx + x1, cy + y1
                    x, y = cx + x, cy + y
                p0 = (cx, cy)
                for k in (1, 2):
                    t = k / 2.0
                    u = 1.0 - t
                    px = u**2 * p0[0] + 2 * u * t * x1 + t**2 * x
                    py = u**2 * p0[1] + 2 * u * t * y1 + t**2 * y
                    pts.append((px, py))
                cx, cy = x, y
        elif cmd == "S":
            while i < len(flat) and not flat[i].isalpha():
                x2, y2, x, y = num(), num(), num(), num()
                if rel:
                    x2, y2 = cx + x2, cy + y2
                    x, y = cx + x, cy + y
                pts.append((x, y))
                cx, cy = x, y
        elif cmd == "Z":
            pts.append(start)
            cx, cy = start
        else:
            # Skip unknown command args until next letter.
            while i < len(flat) and not flat[i].isalpha():
                i += 1
    # Dedup consecutive.
    out: list[tuple[float, float]] = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.5:
            out.append(p)
    return out


def _parse_svg_paths(svg_path: Path) -> dict[str, dict]:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    # Handle default ns.
    tag = lambda t: t.split("}")[-1]
    found: dict[str, dict] = {}
    for el in root.iter():
        if tag(el.tag) != "path":
            continue
        sid = el.get("id")
        d = el.get("d")
        if not sid or not d:
            continue
        if sid in ("ref_plate",):
            continue
        depth = el.get("data-y")
        found[sid] = {
            "plate_pts": _polygonize_path_d(d),
            "data_y": float(depth) if depth not in (None, "") else None,
        }
    return found


def plate_to_world(
    stage: str,
    paths: dict[str, dict],
    bole_xy: tuple[float, float] | None = None,
) -> dict:
    """Map plate polylines → world XYZ. Scale uses full crown (all path tips)."""
    if "trunk" not in paths or len(paths["trunk"]["plate_pts"]) < 2:
        raise ValueError(f"{stage}: SVG needs a trunk path with ≥2 points")
    trunk_pts = paths["trunk"]["plate_pts"]
    # Bole = lowest trunk point (max SVG y).
    bole = max(trunk_pts, key=lambda p: p[1])
    if bole_xy:
        bole = bole_xy
    # Crown tip = highest point among all strands (min SVG y) so primaries
    # that reach the leaf shell do not inflate past STAGE_HEIGHT_M.
    all_pts = [p for meta in paths.values() for p in meta["plate_pts"]]
    tip = min(all_pts, key=lambda p: p[1])
    height_px = max(8.0, bole[1] - tip[1])
    height_m = STAGE_HEIGHT_M[stage]
    scale = height_m / height_px
    bx, by = bole

    def map_pt(x: float, y: float, data_y: float | None) -> tuple[float, float, float]:
        wx = (x - bx) * scale
        wz = (by - y) * scale
        wy = data_y if data_y is not None else 0.12 * wx
        return (round(wx, 4), round(wy, 4), round(wz, 4))

    world: dict[str, list[tuple[float, float, float]]] = {}
    for sid, meta in paths.items():
        world[sid] = [map_pt(x, y, meta["data_y"]) for x, y in meta["plate_pts"]]
    return {
        "stage": stage,
        "bole_plate": [bx, by],
        "tip_plate": [tip[0], tip[1]],
        "scale_m_per_px": scale,
        "height_m": height_m,
        "strands": world,
    }


def load_stage_traces(stage: str) -> dict:
    svg = TRACE_DIR / f"{stage}_primaries.svg"
    if not svg.is_file():
        raise FileNotFoundError(svg)
    paths = _parse_svg_paths(svg)
    return plate_to_world(stage, paths)


def export_trace_png(stage: str) -> Path:
    """Rasterize SVG (plate + cyan paths) via Inkscape for eye check."""
    svg = TRACE_DIR / f"{stage}_primaries.svg"
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out = REF_DIR / f"{stage}_inkscape_trace.png"
    cmd = inkscape_bin() + [
        str(svg),
        "--export-type=png",
        f"--export-filename={out}",
        "-w",
        str(PLATE),
        "-h",
        str(PLATE),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out


def write_world_json(stage: str) -> Path:
    data = load_stage_traces(stage)
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out = REF_DIR / f"{stage}_trace_world.json"
    out.write_text(json.dumps(data, indent=2) + "\n")
    return out


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stages", nargs="*", default=["mature", "veteran"])
    ap.add_argument("--template", action="store_true", help="write empty SVG templates")
    ap.add_argument("--force-template", action="store_true")
    ap.add_argument("--export-png", action="store_true", help="Inkscape-rasterize traces")
    ap.add_argument("--json", action="store_true", default=True, help="write world JSON")
    args = ap.parse_args()
    for stage in args.stages:
        if args.template or args.force_template:
            p = write_template_svg(stage, force=args.force_template)
            print("TEMPLATE", p)
        if args.export_png:
            p = export_trace_png(stage)
            print("TRACE_PNG", p)
        if args.json and (TRACE_DIR / f"{stage}_primaries.svg").is_file():
            p = write_world_json(stage)
            data = json.loads(p.read_text())
            print("WORLD_JSON", p, "strands", list(data["strands"]))


if __name__ == "__main__":
    main()
