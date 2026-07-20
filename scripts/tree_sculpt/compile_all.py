"""Compile every authored stage/variant from an existing source .blend."""
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
sys.path.insert(0, str(HERE))

import sculpt_core as core

stages = os.environ.get(
    "TREE_SCULPT_COMPILE_STAGES",
    "young,mature,veteran,mature_open,mature_upright",
).split(",")
for stage in [value.strip() for value in stages if value.strip()]:
    glb = PROJ / f"models/trees/london_plane_sculpt_{stage}.glb"
    manifest = PROJ / f"tmp/tree_sculpt/review_{stage}/manifest.json"
    obj = core.compile_stage(stage, export_path=glb)
    core.save_manifest(str(manifest), stage, obj)
    print(f"TREE_SCULPT_COMPILED {stage} -> {glb}", flush=True)
os._exit(0)

