"""Visible Blender bridge for semantic tree-sculpt commands.

Launch:
  blender4 models/tree_sources/london_plane.blend \
    --python scripts/tree_sculpt/live_bridge.py

The bridge watches tmp/tree_sculpt/inbox.  It never evaluates arbitrary code.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import sculpt_core as core

ROOT = PROJ / "tmp/tree_sculpt"
INBOX = ROOT / "inbox"
ACKS = ROOT / "acks"
CHECKPOINTS = ROOT / "checkpoints"
REVISION_FILE = ROOT / "revision"
for directory in (INBOX, ACKS, CHECKPOINTS):
    directory.mkdir(parents=True, exist_ok=True)

ALLOWED = {
    "create_strand",
    "delete_strand",
    "move_point",
    "set_radius",
    "transform_system",
    "duplicate_system",
    "set_emitter",
    "set_stage",
    "checkpoint",
    "undo",
    "save",
    "compile",
    "render_review",
}
def revision():
    if REVISION_FILE.exists():
        return int(REVISION_FILE.read_text().strip())
    return int(bpy.context.scene.get("tree_sculpt_revision", 0))


def advance_revision():
    current = revision() + 1
    temp = REVISION_FILE.with_suffix(".tmp")
    temp.write_text(f"{current}\n")
    temp.replace(REVISION_FILE)
    bpy.context.scene["tree_sculpt_revision"] = current


def _checkpoint(label):
    source = Path(bpy.data.filepath)
    if not source:
        raise RuntimeError("save the source .blend before checkpointing")
    safe = "".join(c for c in label if c.isalnum() or c in "-_")[:48] or "checkpoint"
    target = CHECKPOINTS / f"r{revision():04d}_{safe}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source), copy=True)
    shutil.copy2(source, target)
    return str(target)


def _dispatch(command):
    op = command["op"]
    args = command.get("args", {})
    if op not in ALLOWED:
        raise ValueError(f"operation is not allowed: {op}")
    if op == "create_strand":
        obj = core.create_strand(**args)
        return {"object": obj.name}
    if op == "delete_strand":
        core.delete_strand(**args)
    elif op == "move_point":
        core.move_point(**args)
    elif op == "set_radius":
        core.set_point_radius(**args)
    elif op == "transform_system":
        core.transform_system(**args)
    elif op == "duplicate_system":
        created = core.duplicate_system(**args)
        return {"objects": [obj.name for obj in created]}
    elif op == "set_emitter":
        core.set_emitter(**args)
    elif op == "set_stage":
        core.set_stage_visible(args["stage"])
    elif op == "checkpoint":
        return {"checkpoint": _checkpoint(args.get("label", "checkpoint"))}
    elif op == "undo":
        bpy.ops.ed.undo()
    elif op == "save":
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    elif op == "compile":
        stage = args.get("stage", bpy.context.scene.get("tree_sculpt_stage", "mature"))
        obj = core.compile_stage(stage, export_path=args.get("export_path"), foliage=args.get("foliage", True))
        manifest_path = args.get("manifest_path", str(ROOT / f"{stage}_manifest.json"))
        return {"manifest": core.save_manifest(manifest_path, stage, obj)}
    elif op == "render_review":
        from review_rig import render_contact_sheet
        return render_contact_sheet(**args)
    bpy.ops.ed.undo_push(message=f"Tree sculpt: {op}")
    return {}


def process(path: Path):
    command = json.loads(path.read_text())
    command_id = command.get("id", path.stem)
    expected = int(command.get("expected_revision", revision()))
    response = {"id": command_id, "ok": False, "revision": revision()}
    try:
        if expected != revision():
            raise RuntimeError(f"stale revision: expected {expected}, current {revision()}")
        result = _dispatch(command)
        if command["op"] not in {"render_review", "compile", "checkpoint"}:
            advance_revision()
        response.update(ok=True, revision=revision(), result=result or {})
    except Exception as exc:
        response.update(error=str(exc), traceback=traceback.format_exc())
    (ACKS / f"{command_id}.json").write_text(json.dumps(response, indent=2) + "\n")
    path.unlink(missing_ok=True)


def poll():
    try:
        for path in sorted(INBOX.glob("*.json")):
            process(path)
    except Exception:
        traceback.print_exc()
    return 0.20


def install():
    if "tree_sculpt_revision" not in bpy.context.scene:
        bpy.context.scene["tree_sculpt_revision"] = 0
    if "tree_sculpt_stage" not in bpy.context.scene:
        bpy.context.scene["tree_sculpt_stage"] = "mature"
    if not REVISION_FILE.exists():
        REVISION_FILE.write_text(f"{int(bpy.context.scene['tree_sculpt_revision'])}\n")
    if not bpy.app.timers.is_registered(poll):
        bpy.app.timers.register(poll, first_interval=0.20, persistent=True)
    print(f"TREE_SCULPT_READY revision={revision()} inbox={INBOX}", flush=True)


install()

