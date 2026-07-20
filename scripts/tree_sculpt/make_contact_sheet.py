#!/usr/bin/env python3
"""Compose Blender review frames with labels using system Pillow."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+")
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--labels", default="[]")
    parser.add_argument("--reference")
    ns = parser.parse_args()
    labels = json.loads(ns.labels)
    paths = ([ns.reference] if ns.reference else []) + ns.images
    if ns.reference:
        labels = ["reference"] + labels
    opened = [Image.open(p).convert("RGB") for p in paths]
    cell = 512
    cols = 3
    rows = (len(opened) + cols - 1) // cols
    top = 52
    canvas = Image.new("RGB", (cols * cell, top + rows * (cell + 28)), (20, 23, 27))
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 16), ns.title, fill=(240, 240, 240))
    for i, image in enumerate(opened):
        x = (i % cols) * cell
        y = top + (i // cols) * (cell + 28)
        image.thumbnail((cell, cell))
        canvas.paste(image, (x + (cell - image.width) // 2, y))
        draw.text((x + 10, y + cell + 5), labels[i] if i < len(labels) else Path(paths[i]).stem,
                  fill=(220, 220, 220))
    Path(ns.output).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(ns.output)


if __name__ == "__main__":
    main()

