"""
Generate tree models for Central Park Walk using Mtree (Modular Tree).

Creates scale-aware tree variants with size-appropriate branch density.
Trees are generated at real-world heights, then normalized to 5m model
space for the existing Godot pipeline. Leaf cards are placed at branch
tips using the project's crossed-quad system.

Requires: Blender 4.5+ with Modular Tree addon installed.
Run:  blender4 --background --python scripts/generate_trees_mtree.py
      blender4 --background --python scripts/generate_trees_mtree.py -- --species oak
      blender4 --background --python scripts/generate_trees_mtree.py -- --species oak --tier l
"""

import bpy
import bmesh
import sys
import os
import math
import random
import time
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Setup paths and imports
# ---------------------------------------------------------------------------
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from leaf_card_utils import create_leaf_material, make_leaf_cards

# Enable Mtree addon
bpy.ops.preferences.addon_enable(module='bl_ext.user_default.modular_tree')
ADDON_DIR = os.path.expanduser(
    "~/.config/blender/4.5/extensions/user_default/modular_tree"
)
sys.path.insert(0, ADDON_DIR)
from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_mesh_from_cpp

MODEL_DIR = os.path.join(PROJ, "models", "trees")
MODEL_H = 5.0       # Normalized model height for Godot pipeline
N_VARIANTS = 5       # Variants per tier
RADIAL_PTS = 6       # Radial segments for trunk/branch cylinders (game quality)
SMOOTH_ITER = 1      # Mesh smoothing iterations


def clean_nan_vertices(obj):
    """Remove NaN/inf vertices from mesh and return (height, width) of valid bbox."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    to_remove = []
    valid_xs, valid_ys, valid_zs = [], [], []
    for v in bm.verts:
        if (math.isnan(v.co.x) or math.isnan(v.co.y) or math.isnan(v.co.z) or
                math.isinf(v.co.x) or math.isinf(v.co.y) or math.isinf(v.co.z)):
            to_remove.append(v)
        else:
            valid_xs.append(v.co.x)
            valid_ys.append(v.co.y)
            valid_zs.append(v.co.z)

    if to_remove:
        bmesh.ops.delete(bm, geom=to_remove, context='VERTS')

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    if not valid_zs:
        return 0.0, 0.0

    h = max(valid_zs) - min(valid_zs)
    w = max(valid_xs) - min(valid_xs)
    return h, w


# ===========================================================================
# SPECIES CONFIGURATIONS
# ===========================================================================
# Each species defines botanical parameters mapped to Mtree's API.
# Height tiers: s=small, m=medium, l=large with real-world target heights.
# Branch density and sub-branch density scale naturally with tree size.
# ===========================================================================

SPECIES = {
    # ----- Deciduous broad-crowned -----
    "oak": {
        "name": "Red Oak (Quercus rubra)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.22,
        "trunk_shape": 0.5,       # Radius falloff curve
        "up_attraction": 0.5,
        "trunk_randomness": 0.8,
        "branch_start": 0.20,
        "branch_end": 0.95,
        "branch_density": 1.2,
        "branch_length_ratio": 0.40,
        "branch_angle": 55,
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.4,
        "branch_split_prob": 0.55,
        "branch_split_angle": 40.0,
        "branch_flatness": 0.30,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.8,
        "sub_density": 1.6,            # Red oak: dense rounded crown (was 1.5)
        "sub_length_ratio": 0.15,
        "sub_angle": 50,
        "sub_gravity": 12.0,
        "sub_stiffness": 0.1,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.3,
        "sub_split_angle": 35.0,
        "sub_flatness": 0.4,
        "sub_resolution": 0.5,
        "bark_color": (0.22, 0.18, 0.12),
        "bark_roughness": 0.92,
        "leaf_shape": "lobed",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 881,
        "leaf_cluster_size_range": (0.25, 0.55),
        "leaf_flatten_range": (0.40, 0.70),
        "base_seed": 100,
        "seed_step": 23,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 12]},
            "m": {"target_h": 18, "height_range": [12, 20]},
            "l": {"target_h": 25, "height_range": [20, 30]},
        },
    },

    "elm": {
        "name": "American Elm (Ulmus americana)",
        "crown_shape": "Spherical",   # Mtree doesn't have 'vase'; we shape via gravity/up_attraction
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.7,          # Elm trunks grow straight up
        "trunk_randomness": 0.5,
        "branch_start": 0.22,
        "branch_end": 0.92,
        "branch_density": 1.3,
        "branch_length_ratio": 0.45,   # Longer arching branches
        "branch_angle": 35,            # More upright then arching
        "branch_gravity": 12.0,        # Strong gravity creates droop
        "branch_stiffness": 0.15,
        "branch_up_attraction": 0.6,   # Branches go UP first, then arch
        "branch_split_prob": 0.5,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.8,
        "sub_density": 1.5,            # Vase elm: famously dense canopy (was 1.2, orig 1.8)
        "sub_length_ratio": 0.15,
        "sub_angle": 55,
        "sub_gravity": 15.0,           # Heavy droop on sub-branches
        "sub_stiffness": 0.08,
        "sub_up_attraction": -0.2,     # Sub-branches droop
        "sub_split_prob": 0.3,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.25,
        "sub_resolution": 0.4,
        "bark_color": (0.30, 0.25, 0.18),
        "bark_roughness": 0.88,
        "leaf_shape": "elliptic",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 777,
        "leaf_cluster_size_range": (0.25, 0.55),
        "leaf_flatten_range": (0.40, 0.70),
        "base_seed": 42,
        "seed_step": 17,
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 14]},
            "m": {"target_h": 20, "height_range": [14, 22]},
            "l": {"target_h": 28, "height_range": [22, 30]},
        },
    },

    "cathedral_elm": {
        "name": "Cathedral American Elm (Literary Walk)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.16,            # Short trunk — fork low for vase shape
        "trunk_shape": 0.5,
        "up_attraction": 0.4,          # Less vertical pull — let branches spread
        "trunk_randomness": 0.4,
        "branch_start": 0.14,          # Fork very low (typical mature elm)
        "branch_end": 0.85,
        "branch_density": 1.1,
        "branch_length_ratio": 0.52,   # Longer main branches to reach across path
        "branch_angle": 55,            # Wide vase angle (was 40) — 55° creates arch
        "branch_gravity": 6.0,         # Less gravity — branches sweep UP then out
        "branch_stiffness": 0.20,
        "branch_up_attraction": 0.35,  # Moderate upward pull for vase arch shape
        "branch_split_prob": 0.55,
        "branch_split_angle": 50.0,    # Wide secondary splits (was 45)
        "branch_flatness": 0.50,       # Strong lateral spread (was 0.35)
        "branch_break_chance": 0.01,
        "branch_resolution": 0.7,
        "sub_density": 1.5,            # Dense canopy curtain
        "sub_length_ratio": 0.18,
        "sub_angle": 55,               # Sub-branches spread wide too
        "sub_gravity": 16.0,           # Heavy droop — canopy curtain hangs down
        "sub_stiffness": 0.06,
        "sub_up_attraction": -0.4,     # Strong downward pull for drooping curtain
        "sub_split_prob": 0.35,
        "sub_split_angle": 35.0,
        "sub_flatness": 0.35,
        "sub_resolution": 0.4,
        "bark_color": (0.28, 0.23, 0.16),
        "bark_roughness": 0.90,
        "leaf_shape": "elliptic",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 888,
        "leaf_cluster_size_range": (0.30, 0.60),
        "leaf_flatten_range": (0.40, 0.70),
        "base_seed": 101,
        "seed_step": 23,
        "tiers": {
            "s": {"target_h": 15, "height_range": [12, 18]},
            "m": {"target_h": 22, "height_range": [18, 26]},
            "l": {"target_h": 30, "height_range": [26, 35]},
        },
    },

    "maple": {
        "name": "Sugar Maple (Acer saccharum)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.6,
        "trunk_randomness": 0.5,
        "branch_start": 0.22,
        "branch_end": 0.95,
        "branch_density": 1.4,
        "branch_length_ratio": 0.35,
        "branch_angle": 45,
        "branch_gravity": 6.0,
        "branch_stiffness": 0.25,
        "branch_up_attraction": 0.45,
        "branch_split_prob": 0.5,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,       # More oval than flat
        "branch_break_chance": 0.02,
        "branch_resolution": 0.8,
        "sub_density": 1.6,
        "sub_length_ratio": 0.13,
        "sub_angle": 45,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.15,
        "sub_up_attraction": 0.3,
        "sub_split_prob": 0.3,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.5,
        "bark_color": (0.38, 0.32, 0.26),
        "bark_roughness": 0.88,
        "leaf_shape": "palmate",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 552,
        "leaf_cluster_size_range": (0.22, 0.50),
        "leaf_flatten_range": (0.45, 0.60),
        "base_seed": 300,
        "seed_step": 29,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14]},
            "m": {"target_h": 18, "height_range": [14, 22]},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Conifers -----
    "pine": {
        "name": "Austrian Pine (Pinus nigra)",
        "crown_shape": "Conical",
        "trunk_frac": 0.15,
        "trunk_shape": 1.0,           # Straighter conifer trunk
        "up_attraction": 0.7,
        "trunk_randomness": 0.3,
        "branch_start": 0.12,
        "branch_end": 0.95,
        "branch_density": 2.0,         # Dense whorled branches
        "branch_length_ratio": 0.35,
        "branch_angle": 60,            # More horizontal
        "branch_gravity": 10.0,
        "branch_stiffness": 0.15,
        "branch_up_attraction": 0.0,
        "branch_split_prob": 0.4,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.5,
        "branch_break_chance": 0.01,
        "branch_resolution": 0.8,
        "sub_density": 2.5,
        "sub_length_ratio": 0.12,
        "sub_angle": 45,
        "sub_gravity": 14.0,
        "sub_stiffness": 0.1,
        "sub_up_attraction": 0.0,
        "sub_split_prob": 0.3,
        "sub_split_angle": 35.0,
        "sub_flatness": 1.0,          # Flat needle tiers
        "sub_resolution": 0.4,
        "bark_color": (0.28, 0.22, 0.18),
        "bark_roughness": 0.92,
        "leaf_shape": "needle",
        "leaf_n": 18,
        "leaf_tex_size": 1024,
        "leaf_seed": 601,
        "leaf_cluster_size_range": (0.28, 0.55),
        "leaf_flatten_range": (0.40, 0.60),
        "base_seed": 400,
        "seed_step": 29,
        "tiers": {
            "s": {"target_h": 8, "height_range": [6, 10]},
            "m": {"target_h": 14, "height_range": [10, 18]},
            "l": {"target_h": 20, "height_range": [18, 25]},
        },
    },

    # ----- Deciduous small ornamental -----
    "cherry": {
        "name": "Yoshino Cherry (Prunus x yedoensis)",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.5,
        "trunk_randomness": 0.6,
        "branch_start": 0.22,
        "branch_end": 0.90,
        "branch_density": 1.3,
        "branch_length_ratio": 0.42,   # Graceful spreading
        "branch_angle": 50,
        "branch_gravity": 9.0,
        "branch_stiffness": 0.15,
        "branch_up_attraction": 0.3,
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.35,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.8,
        "sub_density": 1.5,
        "sub_length_ratio": 0.14,
        "sub_angle": 50,
        "sub_gravity": 12.0,
        "sub_stiffness": 0.1,
        "sub_up_attraction": 0.1,
        "sub_split_prob": 0.25,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.35,
        "sub_resolution": 0.5,
        "bark_color": (0.35, 0.20, 0.14),
        "bark_roughness": 0.72,
        "leaf_shape": "elliptic",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 443,
        "leaf_cluster_size_range": (0.20, 0.45),
        "leaf_flatten_range": (0.50, 0.75),
        "base_seed": 200,
        "seed_step": 19,
        "tiers": {
            "s": {"target_h": 7, "height_range": [5, 9]},
            "m": {"target_h": 12, "height_range": [9, 16]},
            "l": {"target_h": 18, "height_range": [16, 22]},
        },
    },

    # ----- Multi-stem / white bark -----
    "birch": {
        "name": "Gray Birch (Betula populifolia)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.30,
        "trunk_shape": 0.7,
        "up_attraction": 0.6,
        "trunk_randomness": 0.7,
        "branch_start": 0.28,
        "branch_end": 0.95,
        "branch_density": 1.0,
        "branch_length_ratio": 0.35,
        "branch_angle": 50,
        "branch_gravity": 10.0,
        "branch_stiffness": 0.12,
        "branch_up_attraction": 0.3,
        "branch_split_prob": 0.4,
        "branch_split_angle": 30.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.03,
        "branch_resolution": 0.7,
        "sub_density": 1.2,
        "sub_length_ratio": 0.12,
        "sub_angle": 55,
        "sub_gravity": 14.0,
        "sub_stiffness": 0.08,
        "sub_up_attraction": -0.15,    # Drooping branchlets
        "sub_split_prob": 0.2,
        "sub_split_angle": 25.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.4,
        "bark_color": (0.82, 0.78, 0.72),
        "bark_roughness": 0.65,
        "leaf_shape": "elliptic",
        "leaf_n": 12,
        "leaf_tex_size": 1024,
        "leaf_seed": 551,
        "leaf_cluster_size_range": (0.18, 0.40),
        "leaf_flatten_range": (0.40, 0.70),
        "base_seed": 300,
        "seed_step": 23,
        "tiers": {
            "s": {"target_h": 6, "height_range": [4, 8]},
            "m": {"target_h": 9, "height_range": [8, 12]},
            "l": {"target_h": 14, "height_range": [12, 16]},
        },
    },

    # ----- Compound leaves / airy -----
    "honeylocust": {
        "name": "Honeylocust (Gleditsia triacanthos)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.55,
        "trunk_randomness": 0.6,
        "branch_start": 0.22,
        "branch_end": 0.95,
        "branch_density": 1.0,
        "branch_length_ratio": 0.38,
        "branch_angle": 48,
        "branch_gravity": 7.0,
        "branch_stiffness": 0.18,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.5,
        "branch_split_angle": 38.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.7,
        "sub_density": 1.2,
        "sub_length_ratio": 0.12,
        "sub_angle": 48,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.15,
        "sub_split_prob": 0.25,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.4,
        "bark_color": (0.35, 0.28, 0.20),
        "bark_roughness": 0.88,
        "leaf_shape": "compound",
        "leaf_n": 12,
        "leaf_tex_size": 1024,
        "leaf_seed": 661,
        "leaf_cluster_size_range": (0.20, 0.42),
        "leaf_flatten_range": (0.45, 0.65),
        "base_seed": 400,
        "seed_step": 29,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14]},
            "m": {"target_h": 18, "height_range": [14, 22]},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Tight pyramidal -----
    "callery_pear": {
        "name": "Callery Pear (Pyrus calleryana)",
        "crown_shape": "Conical",
        "trunk_frac": 0.20,
        "trunk_shape": 0.8,           # Strong central leader
        "up_attraction": 0.8,
        "trunk_randomness": 0.3,
        "branch_start": 0.18,
        "branch_end": 0.95,
        "branch_density": 1.5,
        "branch_length_ratio": 0.30,
        "branch_angle": 35,            # Sharply upward
        "branch_gravity": 5.0,
        "branch_stiffness": 0.3,
        "branch_up_attraction": 0.55,
        "branch_split_prob": 0.5,
        "branch_split_angle": 30.0,
        "branch_flatness": 0.15,
        "branch_break_chance": 0.01,
        "branch_resolution": 0.8,
        "sub_density": 1.8,
        "sub_length_ratio": 0.12,
        "sub_angle": 40,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.2,
        "sub_up_attraction": 0.4,
        "sub_split_prob": 0.3,
        "sub_split_angle": 25.0,
        "sub_flatness": 0.2,
        "sub_resolution": 0.5,
        "bark_color": (0.42, 0.36, 0.28),
        "bark_roughness": 0.82,
        "leaf_shape": "ovate",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 557,
        "leaf_cluster_size_range": (0.22, 0.48),
        "leaf_flatten_range": (0.50, 0.70),
        "base_seed": 350,
        "seed_step": 23,
        "tiers": {
            "s": {"target_h": 8, "height_range": [6, 10]},
            "m": {"target_h": 14, "height_range": [10, 18]},
            "l": {"target_h": 20, "height_range": [18, 24]},
        },
    },

    # ----- Weeping -----
    "willow": {
        "name": "Weeping Willow (Salix babylonica)",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.28,
        "trunk_shape": 0.4,
        "up_attraction": 0.7,
        "trunk_randomness": 0.5,
        "branch_start": 0.25,
        "branch_end": 0.90,
        "branch_density": 1.2,
        "branch_length_ratio": 0.40,
        "branch_angle": 50,
        "branch_gravity": 6.0,
        "branch_stiffness": 0.4,
        "branch_up_attraction": 0.5,
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.01,
        "branch_resolution": 0.8,
        # Willow sub-branches: long, drooping curtains
        "sub_density": 1.2,
        "sub_length_ratio": 0.30,      # Long drooping strands
        "sub_angle": 65,
        "sub_gravity": 25.0,           # Strong droop (reduced from 200 — crashed Mtree core)
        "sub_stiffness": 0.05,
        "sub_up_attraction": -0.4,     # Downward tendency (reduced from -0.8)
        "sub_split_prob": 0.05,
        "sub_split_angle": 20.0,
        "sub_flatness": 0.0,
        "sub_resolution": 0.4,
        "bark_color": (0.40, 0.35, 0.28),
        "bark_roughness": 0.88,
        "leaf_shape": "lanceolate",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 801,
        "leaf_cluster_size_range": (0.18, 0.40),
        "leaf_flatten_range": (0.55, 0.75),
        "sub_min_height": 14,          # Sub-branches only on mature willows
        "base_seed": 50,
        "seed_step": 41,
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 14]},
            "m": {"target_h": 16, "height_range": [14, 20]},
            "l": {"target_h": 22, "height_range": [20, 26]},
        },
    },

    # ----- Dense symmetrical -----
    "linden": {
        "name": "Linden (Tilia americana)",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.26,
        "trunk_shape": 0.65,
        "up_attraction": 0.65,
        "trunk_randomness": 0.3,       # Very straight
        "branch_start": 0.24,
        "branch_end": 0.95,
        "branch_density": 1.4,
        "branch_length_ratio": 0.35,
        "branch_angle": 45,
        "branch_gravity": 6.0,
        "branch_stiffness": 0.25,
        "branch_up_attraction": 0.4,
        "branch_split_prob": 0.5,
        "branch_split_angle": 32.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.01,
        "branch_resolution": 0.8,
        "sub_density": 1.6,
        "sub_length_ratio": 0.13,
        "sub_angle": 45,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.15,
        "sub_up_attraction": 0.25,
        "sub_split_prob": 0.3,
        "sub_split_angle": 28.0,
        "sub_flatness": 0.25,
        "sub_resolution": 0.5,
        "bark_color": (0.35, 0.30, 0.24),
        "bark_roughness": 0.85,
        "leaf_shape": "ovate",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 773,
        "leaf_cluster_size_range": (0.22, 0.48),
        "leaf_flatten_range": (0.45, 0.60),
        "base_seed": 500,
        "seed_step": 37,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14]},
            "m": {"target_h": 18, "height_range": [14, 22]},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Tall open -----
    "london_plane": {
        "name": "London Plane (Platanus x acerifolia)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.30,
        "trunk_shape": 0.6,
        "up_attraction": 0.6,
        "trunk_randomness": 0.5,
        "branch_start": 0.28,
        "branch_end": 0.95,
        "branch_density": 1.1,
        "branch_length_ratio": 0.38,
        "branch_angle": 50,
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.55,
        "branch_split_angle": 40.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.8,
        "sub_density": 1.6,            # London plane: massive broad canopy (was 1.4)
        "sub_length_ratio": 0.14,
        "sub_angle": 50,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.3,
        "sub_split_angle": 35.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.5,
        "bark_color": (0.48, 0.45, 0.36),
        "bark_roughness": 0.75,
        "leaf_shape": "lobed",
        "leaf_n": 12,
        "leaf_tex_size": 1024,
        "leaf_seed": 447,
        "leaf_cluster_size_range": (0.25, 0.55),
        "leaf_flatten_range": (0.45, 0.65),
        "base_seed": 200,
        "seed_step": 31,
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 15]},
            "m": {"target_h": 22, "height_range": [15, 25]},
            "l": {"target_h": 30, "height_range": [25, 35]},
        },
    },

    # ----- Columnar / spur shoots -----
    "ginkgo": {
        "name": "Ginkgo (Ginkgo biloba)",
        "crown_shape": "Conical",
        "trunk_frac": 0.30,
        "trunk_shape": 0.8,
        "up_attraction": 0.8,         # Strong central leader
        "trunk_randomness": 0.3,
        "branch_start": 0.28,
        "branch_end": 0.95,
        "branch_density": 0.8,         # Reduced from 1.2 (crashes mesher at large scale)
        "branch_length_ratio": 0.28,
        "branch_angle": 42,
        "branch_gravity": 5.0,
        "branch_stiffness": 0.3,
        "branch_up_attraction": 0.5,
        "branch_split_prob": 0.4,
        "branch_split_angle": 30.0,
        "branch_flatness": 0.15,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.5,      # Reduced from 0.7
        "sub_density": 1.3,
        "sub_length_ratio": 0.08,      # Short spur shoots
        "sub_angle": 55,
        "sub_gravity": 6.0,
        "sub_stiffness": 0.2,
        "sub_up_attraction": 0.1,
        "sub_split_prob": 0.15,
        "sub_split_angle": 25.0,
        "sub_flatness": 0.2,
        "sub_resolution": 0.4,
        "bark_color": (0.38, 0.34, 0.28),
        "bark_roughness": 0.90,
        "leaf_shape": "fan",
        "leaf_n": 12,
        "leaf_tex_size": 1024,
        "leaf_seed": 557,
        "leaf_cluster_size_range": (0.18, 0.40),
        "leaf_flatten_range": (0.50, 0.70),
        "sub_min_height": 999,          # Spur shoots crash mesher; use primary-only
        "base_seed": 50,
        "seed_step": 31,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14]},
            "m": {"target_h": 18, "height_range": [14, 22]},
            "l": {"target_h": 22, "height_range": [20, 25]},
        },
    },

    # ----- Large-leaved ornamental -----
    "magnolia": {
        "name": "Saucer Magnolia",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.20,
        "trunk_shape": 0.5,
        "up_attraction": 0.5,
        "trunk_randomness": 0.6,
        "branch_start": 0.18,
        "branch_end": 0.90,
        "branch_density": 1.2,
        "branch_length_ratio": 0.38,
        "branch_angle": 48,
        "branch_gravity": 7.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.7,
        "sub_density": 1.3,
        "sub_length_ratio": 0.13,
        "sub_angle": 48,
        "sub_gravity": 9.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.25,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.4,
        "bark_color": (0.42, 0.38, 0.32),
        "bark_roughness": 0.78,
        "leaf_shape": "ovate",
        "leaf_n": 12,
        "leaf_tex_size": 1024,
        "leaf_seed": 663,
        "leaf_cluster_size_range": (0.25, 0.55),
        "leaf_flatten_range": (0.45, 0.65),
        "base_seed": 500,
        "seed_step": 29,
        "tiers": {
            "s": {"target_h": 7, "height_range": [5, 9]},
            "m": {"target_h": 12, "height_range": [9, 16]},
            "l": {"target_h": 18, "height_range": [16, 22]},
        },
    },

    # ----- Generic fallback -----
    "deciduous": {
        "name": "Generic Deciduous",
        "crown_shape": "Spherical",
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.55,
        "trunk_randomness": 0.6,
        "branch_start": 0.22,
        "branch_end": 0.95,
        "branch_density": 1.2,
        "branch_length_ratio": 0.38,
        "branch_angle": 50,
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.5,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 0.8,
        "sub_density": 1.4,
        "sub_length_ratio": 0.14,
        "sub_angle": 48,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.3,
        "sub_split_angle": 32.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.5,
        "bark_color": (0.32, 0.27, 0.20),
        "bark_roughness": 0.85,
        "leaf_shape": "elliptic",
        "leaf_n": 14,
        "leaf_tex_size": 1024,
        "leaf_seed": 700,
        "leaf_cluster_size_range": (0.22, 0.50),
        "leaf_flatten_range": (0.45, 0.65),
        "base_seed": 700,
        "seed_step": 31,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14]},
            "m": {"target_h": 18, "height_range": [14, 22]},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },
}

# Crown shape name -> Mtree CrownShape enum
CROWN_MAP = {
    "Spherical": "Spherical",
    "Conical": "Conical",
    "Hemispherical": "Hemispherical",
    "Cylindrical": "Cylindrical",
    "Flame": "Flame",
    "TaperedCylindrical": "TaperedCylindrical",
    "InverseConical": "InverseConical",
    "TendFlame": "TendFlame",
}


# ===========================================================================
# TREE GENERATION
# ===========================================================================

def generate_tree_skeleton(sp, height, seed):
    """Generate trunk + branches mesh using Mtree. Returns C++ mesh."""
    tree = m_tree.Tree()

    # --- Trunk ---
    trunk = m_tree.TrunkFunction()
    trunk.seed = seed
    trunk.length = height
    trunk.start_radius = height * 0.018
    trunk.end_radius = height * 0.005
    trunk.shape = sp["trunk_shape"]
    trunk.up_attraction = sp["up_attraction"]
    trunk.resolution = sp["branch_resolution"]
    trunk.randomness = sp["trunk_randomness"]

    # --- Primary branches ---
    br = m_tree.BranchFunction()
    br.seed = seed + 1
    br.distribution.start = sp["branch_start"]
    br.distribution.end = sp["branch_end"]
    br.distribution.density = sp["branch_density"]
    br.distribution.phillotaxis = 137.5
    br.gravity.strength = sp["branch_gravity"]
    br.gravity.stiffness = sp["branch_stiffness"]
    br.gravity.up_attraction = sp["branch_up_attraction"]
    br.split.probability = sp["branch_split_prob"]
    br.split.angle = sp["branch_split_angle"]
    br.split.radius = 0.8
    br.flatness = sp["branch_flatness"]
    br.break_chance = sp["branch_break_chance"]
    br.resolution = sp["branch_resolution"]
    br.length = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(height * sp["branch_length_ratio"])
    )
    br.start_radius = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.4))
    br.randomness = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.5))
    br.start_angle = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(float(sp["branch_angle"]))
    )
    # Crown shape
    crown_name = CROWN_MAP.get(sp["crown_shape"], "Spherical")
    br.crown.shape = getattr(m_tree.CrownShape, crown_name)

    # --- Sub-branches ---
    sub_min_h = sp.get("sub_min_height", 0)
    if sp["sub_density"] > 0 and height >= sub_min_h:
        sub = m_tree.BranchFunction()
        sub.seed = seed + 2
        sub.distribution.start = 0.2
        sub.distribution.end = 0.95
        sub.distribution.density = sp["sub_density"]
        sub.gravity.strength = sp["sub_gravity"]
        sub.gravity.stiffness = sp["sub_stiffness"]
        sub.gravity.up_attraction = sp["sub_up_attraction"]
        sub.split.probability = sp["sub_split_prob"]
        sub.split.angle = sp["sub_split_angle"]
        sub.flatness = sp["sub_flatness"]
        sub.resolution = sp["sub_resolution"]
        sub.length = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(height * sp["sub_length_ratio"])
        )
        sub.start_radius = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.25))
        sub.randomness = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.6))
        sub.start_angle = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(float(sp["sub_angle"]))
        )
        br.add_child(sub)

    trunk.add_child(br)
    tree.set_trunk_function(trunk)
    tree.execute_functions()

    mesher = m_tree.ManifoldMesher()
    mesher.radial_n_points = RADIAL_PTS
    mesher.smooth_iterations = SMOOTH_ITER
    return mesher.mesh_tree(tree)


def extract_leaf_positions(mesh_obj, sp, target_height, rng):
    """Extract branch tip positions for leaf card placement.

    Uses the 'radius' vertex attribute: small radius = branch tip.
    Clusters nearby tips and returns placement positions + sizes.
    """
    mesh = mesh_obj.data
    verts = mesh.vertices
    n = len(verts)
    if n == 0:
        return []

    # Read radius attribute
    radius_attr = mesh.attributes.get("radius")
    if not radius_attr:
        return []

    radii = [radius_attr.data[i].value for i in range(n)]

    # Threshold: branch tips have small radius
    # Scale threshold with tree size (larger trees have slightly thicker tips)
    tip_threshold = 0.015 + target_height * 0.0005
    tip_positions = []
    for i in range(n):
        if radii[i] < tip_threshold:
            v = verts[i].co
            # Skip NaN/inf vertices (degenerate geometry)
            if math.isnan(v.x) or math.isnan(v.y) or math.isnan(v.z):
                continue
            if math.isinf(v.x) or math.isinf(v.y) or math.isinf(v.z):
                continue
            tip_positions.append(Vector((v.x, v.y, v.z)))

    if not tip_positions:
        return []

    # Cluster nearby tips (grid-based spatial hash)
    cell_size = target_height * 0.042  # ~1.05m cells for 25m tree (was 0.06 = 1.5m)
    clusters = {}
    for pos in tip_positions:
        key = (
            int(pos.x / cell_size),
            int(pos.y / cell_size),
            int(pos.z / cell_size),
        )
        if key not in clusters:
            clusters[key] = []
        clusters[key].append(pos)

    # Compute cluster centroids
    placements = []
    lo, hi = sp["leaf_cluster_size_range"]
    flo, fhi = sp["leaf_flatten_range"]
    for cell_tips in clusters.values():
        cx = sum(p.x for p in cell_tips) / len(cell_tips)
        cy = sum(p.y for p in cell_tips) / len(cell_tips)
        cz = sum(p.z for p in cell_tips) / len(cell_tips)
        size = rng.uniform(lo, hi) * (target_height / 25.0)  # Scale with tree
        flatten = rng.uniform(flo, fhi)
        placements.append((Vector((cx, cy, cz)), size, flatten))

    return placements


def create_leaf_cards_at_positions(placements, leaf_mat, rng):
    """Create crossed-quad leaf card clusters at the given positions.

    Returns a list of bmesh objects to be joined into the tree mesh.
    """
    all_objects = []
    for pos, size, flatten in placements:
        n_quads = 3
        card_w = size * 2.0 * rng.uniform(0.85, 1.15)
        card_h = card_w * flatten * rng.uniform(0.8, 1.2)
        base_angle = rng.uniform(0, math.pi)

        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")

        for q in range(n_quads):
            angle = base_angle + q * math.pi / n_quads
            # Random tilt for organic look
            tilt_x = rng.uniform(-0.15, 0.15)
            tilt_z = rng.uniform(-0.15, 0.15)

            dx = math.cos(angle) * card_w * 0.5
            dy = math.sin(angle) * card_w * 0.5
            half_h = card_h * 0.5

            corners = [
                Vector((-dx + tilt_x * half_h, -dy + tilt_z * half_h, -half_h)) + pos,
                Vector((dx + tilt_x * half_h, dy + tilt_z * half_h, -half_h)) + pos,
                Vector((dx - tilt_x * half_h, dy - tilt_z * half_h, half_h)) + pos,
                Vector((-dx - tilt_x * half_h, -dy - tilt_z * half_h, half_h)) + pos,
            ]
            bm_verts = [bm.verts.new(c) for c in corners]
            face = bm.faces.new(bm_verts)

            # UV: full 0-1 space
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv

        mesh = bpy.data.meshes.new("leaf_cards")
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new("leaf_cards", mesh)
        obj.data.materials.append(leaf_mat)
        bpy.context.collection.objects.link(obj)
        all_objects.append(obj)

    return all_objects


def generate_species_tier(species_name, tier_name, sp, tier_cfg):
    """Generate all variants for one species at one size tier.

    Creates a GLB with N_VARIANTS variants, each containing trunk+branches
    from Mtree plus leaf cards at branch tips, normalized to MODEL_H.
    """
    target_h = tier_cfg["target_h"]
    out_path = os.path.join(MODEL_DIR, f"{species_name}_{tier_name}.glb")

    print(f"\n{'='*60}")
    print(f"  {sp['name']} — tier {tier_name} ({target_h}m)")
    print(f"  Output: {out_path}")
    print(f"{'='*60}")

    # Create leaf material (shared across variants)
    leaf_mat = create_leaf_material(
        f"{species_name}_leaf",
        leaf_shape=sp["leaf_shape"],
        n_leaves=sp["leaf_n"],
        tex_size=sp["leaf_tex_size"],
        seed=sp["leaf_seed"],
    )

    # Create bark material
    bark_mat = bpy.data.materials.new(f"{species_name}_bark")
    bark_mat.use_nodes = True
    bsdf = bark_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*sp["bark_color"], 1.0)
    bsdf.inputs["Roughness"].default_value = sp["bark_roughness"]

    variant_objects = []

    for vi in range(N_VARIANTS):
        seed = sp["base_seed"] + vi * sp["seed_step"]
        rng = random.Random(seed)
        t0 = time.time()

        # --- Generate skeleton ---
        cpp_mesh = generate_tree_skeleton(sp, target_h, seed)

        mesh = bpy.data.meshes.new(f"{species_name}_{tier_name}_v{vi}")
        trunk_obj = bpy.data.objects.new(f"{species_name}_{tier_name}_v{vi}", mesh)
        bpy.context.collection.objects.link(trunk_obj)
        create_mesh_from_cpp(mesh, cpp_mesh)
        trunk_obj.data.materials.append(bark_mat)

        # --- Clean NaN vertices and get bbox ---
        actual_h, actual_w = clean_nan_vertices(trunk_obj)

        # --- Place leaf cards ---
        placements = extract_leaf_positions(trunk_obj, sp, target_h, rng)
        leaf_objs = create_leaf_cards_at_positions(placements, leaf_mat, rng)

        # --- Join all objects ---
        bpy.ops.object.select_all(action='DESELECT')
        trunk_obj.select_set(True)
        for lo in leaf_objs:
            lo.select_set(True)
        bpy.context.view_layer.objects.active = trunk_obj
        if leaf_objs:
            bpy.ops.object.join()

        # --- Normalize to MODEL_H ---
        if actual_h > 0.1:
            scale = MODEL_H / actual_h
            for v in trunk_obj.data.vertices:
                v.co *= scale
            trunk_obj.data.update()
            actual_w *= scale

        # --- Center at origin (base at z=0) ---
        min_z = min(
            (v.co.z for v in trunk_obj.data.vertices), default=0.0
        )
        if abs(min_z) > 0.001:
            for v in trunk_obj.data.vertices:
                v.co.z -= min_z
            trunk_obj.data.update()

        dt = time.time() - t0
        n_leaves = len(placements)
        n_verts = len(trunk_obj.data.vertices)
        n_faces = len(trunk_obj.data.polygons)
        print(f"  v{vi} seed={seed}: {n_verts:,} verts, {n_faces:,} faces, "
              f"{n_leaves} leaf clusters, h={actual_h:.1f}m w={actual_w:.1f}m ({dt:.1f}s)")

        variant_objects.append(trunk_obj)

    # --- Export all variants in one GLB ---
    bpy.ops.object.select_all(action='DESELECT')
    for obj in variant_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = variant_objects[0]

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
    )

    sz = os.path.getsize(out_path) / 1024
    print(f"  → {out_path} ({sz:.0f} KB)")

    # --- Cleanup for next tier ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


# ===========================================================================
# DEAD TREE (no leaves, special handling)
# ===========================================================================

def generate_dead_tree():
    """Generate dead tree snags — broken tops, no foliage."""
    out_path = os.path.join(MODEL_DIR, "dead.glb")
    print(f"\n{'='*60}")
    print(f"  Dead Tree (snag)")
    print(f"  Output: {out_path}")
    print(f"{'='*60}")

    bark_mat = bpy.data.materials.new("dead_bark")
    bark_mat.use_nodes = True
    bsdf = bark_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.42, 0.38, 0.34, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92

    variant_objects = []
    for vi in range(N_VARIANTS):
        seed = 600 + vi * 37
        rng = random.Random(seed)

        tree = m_tree.Tree()
        trunk = m_tree.TrunkFunction()
        trunk.seed = seed
        trunk.length = rng.uniform(8, 14)
        trunk.start_radius = rng.uniform(0.15, 0.28)
        trunk.end_radius = rng.uniform(0.05, 0.10)
        trunk.shape = 0.45                  # Natural taper
        trunk.up_attraction = 0.7           # Mostly vertical (dead wood doesn't bend further)
        trunk.resolution = 0.6
        trunk.randomness = 0.4              # Subtle irregularity, not chaos

        # Short broken stubs — dead branches are stiff and short
        br = m_tree.BranchFunction()
        br.seed = seed + 1
        br.distribution.start = 0.2
        br.distribution.end = rng.uniform(0.6, 0.85)   # Broken top
        br.distribution.density = rng.uniform(0.25, 0.5)  # Sparse — most branches have fallen
        br.gravity.strength = 2.0           # Dead wood is stiff, minimal droop
        br.gravity.stiffness = 0.6          # Rigid branches
        br.gravity.up_attraction = 0.1      # Slight upward tendency (grew up when alive)
        br.split.probability = 0.05         # Almost no splitting (broken off)
        br.flatness = 0.15                  # Slight planar tendency
        br.break_chance = 0.25              # Many branches snap off
        br.resolution = 0.5
        br.length = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(rng.uniform(0.8, 2.5))  # Short stubs
        )
        br.start_radius = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.3))
        br.randomness = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.3))
        br.start_angle = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(rng.uniform(50, 80))    # Angled up (natural growth direction)
        )

        trunk.add_child(br)
        tree.set_trunk_function(trunk)
        tree.execute_functions()

        mesher = m_tree.ManifoldMesher()
        mesher.radial_n_points = 6
        mesher.smooth_iterations = 1
        cpp_mesh = mesher.mesh_tree(tree)

        mesh = bpy.data.meshes.new(f"dead_v{vi}")
        obj = bpy.data.objects.new(f"dead_v{vi}", mesh)
        bpy.context.collection.objects.link(obj)
        create_mesh_from_cpp(mesh, cpp_mesh)
        obj.data.materials.append(bark_mat)

        # Clean NaN and normalize to MODEL_H
        actual_h, _ = clean_nan_vertices(obj)
        if actual_h > 0.1:
            scale = MODEL_H / actual_h
            for v in obj.data.vertices:
                v.co *= scale
            obj.data.update()
        min_z = min((v.co.z for v in obj.data.vertices), default=0.0)
        if abs(min_z) > 0.001:
            for v in obj.data.vertices:
                v.co.z -= min_z
            obj.data.update()

        print(f"  v{vi}: {len(obj.data.vertices):,} verts, h={actual_h:.1f}m")
        variant_objects.append(obj)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in variant_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = variant_objects[0]
    bpy.ops.export_scene.gltf(
        filepath=out_path, use_selection=True,
        export_format='GLB', export_apply=True,
    )
    sz = os.path.getsize(out_path) / 1024
    print(f"  → {out_path} ({sz:.0f} KB)")

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    # Parse CLI args (after --)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    filter_species = None
    filter_tier = None
    for i, arg in enumerate(argv):
        if arg == "--species" and i + 1 < len(argv):
            filter_species = argv[i + 1]
        if arg == "--tier" and i + 1 < len(argv):
            filter_tier = argv[i + 1]

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    os.makedirs(MODEL_DIR, exist_ok=True)

    t_start = time.time()
    total_species = 0
    total_tiers = 0

    # Generate living trees
    for sp_name, sp in SPECIES.items():
        if filter_species and sp_name != filter_species:
            continue

        for tier_name, tier_cfg in sp["tiers"].items():
            if filter_tier and tier_name != filter_tier:
                continue

            generate_species_tier(sp_name, tier_name, sp, tier_cfg)
            total_tiers += 1

        total_species += 1

    # Generate dead trees
    if not filter_species or filter_species == "dead":
        if not filter_tier:
            generate_dead_tree()

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  COMPLETE: {total_species} species, {total_tiers} tiers")
    print(f"  Total time: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
