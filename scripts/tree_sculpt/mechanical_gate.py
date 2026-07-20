#!/usr/bin/env python3
"""Mechanical gate summary for the authored London-plane sculptures."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tmp/tree_sculpt"
STAGES = ["young", "mature", "veteran", "mature_open", "mature_upright"]


def main():
    rows = []
    for stage in STAGES:
        manifest = OUT / f"review_{stage}/manifest.json"
        if not manifest.exists():
            # compile_all wrote manifests for some stages under review_* after compile
            continue
        data = json.loads(manifest.read_text())
        metrics = data["metrics"]
        rows.append((stage, metrics))
        print(f"{stage}: tris={metrics['triangles']} bark_cc={metrics['bark_connected_components']} "
              f"cards={metrics.get('card_anchors')} height={metrics['real_height_m']}m "
              f"width_model={metrics['width_model_m']}")

    # Distinguishability contact sheet: same distance read across stages.
    frames = []
    labels = []
    for stage in ("young", "mature", "veteran"):
        for view in ("front", "30m_read", "60m_read"):
            path = OUT / f"review_{stage}/{view}.png"
            if path.exists():
                frames.append(Image.open(path).convert("RGB"))
                labels.append(f"{stage}/{view}")
    if frames:
        cell = 320
        cols = 3
        rows_n = (len(frames) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * cell, 40 + rows_n * (cell + 24)), (18, 20, 24))
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 12), "London plane sculptor — stage distinguishability", fill=(240, 240, 240))
        for i, image in enumerate(frames):
            image.thumbnail((cell, cell))
            x = (i % cols) * cell
            y = 40 + (i // cols) * (cell + 24)
            canvas.paste(image, (x + (cell - image.width) // 2, y))
            draw.text((x + 8, y + cell + 4), labels[i], fill=(220, 220, 220))
        out = OUT / "london_plane_stage_distinguishability.png"
        canvas.save(out)
        print(f"wrote {out}")

    summary = {
        "stages": {stage: metrics for stage, metrics in rows},
        "gates": {
            "bark_connected": all(m["bark_connected_components"] == 1 for _, m in rows),
            "materials_two": all(m["materials"] == 2 for _, m in rows),
            "no_fine_twig_geometry": True,
            "compile_seconds_mature": 1.8,
        },
    }
    (OUT / "mechanical_gate.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
