"""Locked per-stage habit photographs + multi-example shape corpus.

Shared by Blender (no Pillow) and the overlay / shape-fit scripts. Edit here +
`docs/tree_sculptor.md` together.

``STAGE_REFS`` — one locked plate per stage (photo-match overlay identity).
``CORPUS`` — additional whole-tree examples used to measure tier shape priors
(fork height, aspect). Leaf / trunk crops stay out.

W-40 (Chris on W-39): a good reference shows the *entire* tree, alone or easy
to separate from its environment. Nursery-with-person, incomplete shells, and
crowns that merge into background woodland are out.
"""
from __future__ import annotations

# W-40: all three locks replaced for isolation / whole-tree readability.
STAGE_REFS = {
    "young": {
        # Commons: File:Platanus xhispanica.habit.jpg (CC BY-SA 3.0)
        "file": "Platanus_xhispanica_habit.jpg",
        "crop_frac": (0.12, 0.04, 0.88, 0.96),
        "why": "Young whole tree alone against sky; central leader; upright oval; no person/pots.",
    },
    "mature": {
        # geograph 7338525 — Philip Halling (CC BY-SA 2.0)
        "file": "london_plane_geograph_7338525.jpg",
        "crop_frac": (0.12, 0.02, 0.88, 0.96),
        "why": "Mature whole tree alone in open field; full crown silhouette; easy sky separation.",
    },
    "veteran": {
        # geograph 7373536 — Bob Harvey (CC BY-SA 2.0); winter = full wood readable
        "file": "london_plane_geograph_7373536.jpg",
        "crop_frac": (0.16, 0.02, 0.84, 0.90),
        "why": "Large whole tree alone on bank; bare crown against sky; heavy low scaffold readable.",
    },
}

# Whole-tree examples for automated shape measurement (W-39+). Locked plate is
# always included again so the corpus median is not blind to the overlay authority.
CORPUS = {
    "young": [
        {
            "file": STAGE_REFS["young"]["file"],
            "crop_frac": STAGE_REFS["young"]["crop_frac"],
            "why": "locked young habit",
        },
    ],
    "mature": [
        {
            "file": STAGE_REFS["mature"]["file"],
            "crop_frac": STAGE_REFS["mature"]["crop_frac"],
            "why": "locked mature field specimen",
        },
        {
            "file": "A149-03_hero_l.jpg",
            "crop_frac": (0.12, 0.02, 0.88, 0.98),
            "why": "open-park mature dome; low heavy scaffold; clear bole (prior corpus)",
        },
        {
            "file": "london_plane_geograph_7923058.jpg",
            "crop_frac": (0.12, 0.02, 0.88, 0.96),
            "why": "alone in field; autumn thinning; full silhouette",
        },
    ],
    "veteran": [
        {
            "file": STAGE_REFS["veteran"]["file"],
            "crop_frac": STAGE_REFS["veteran"]["crop_frac"],
            "why": "locked winter bank veteran",
        },
        {
            "file": "platanus_hispanica_poznan_dendrological_2.JPG",
            "crop_frac": (0.18, 0.02, 0.82, 0.96),
            "why": "tall whole tree; mottled bole; ascending scaffold into crest",
        },
        {
            # Structure-only (not whole silhouette) — keep for heavy-wood prior only.
            "file": "majestic-london-plane-tree-urban-architectural-photography-showcase-greenery-cityscape-captivating-photograph-353509813_branch_structure.jpg",
            "crop_frac": (0.05, 0.02, 0.55, 0.98),
            "why": "readable heavy wood through tip islands (structure, not whole silhouette)",
        },
    ],
}
