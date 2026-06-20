"""Generate leaf-aware LOD variants of tree models (SpeedTree approach).

Instead of generic mesh decimation (which destroys leaf card UVs and creates
canopy holes), this script:
  1. Separates leaf geometry from bark by material name ("leaf")
  2. Randomly removes entire leaf card quads (not edge-collapse)
  3. Scales surviving cards UP to maintain constant canopy coverage density
  4. (lod2 only) Decimates bark to a triangle budget — bark is opaque tube
     geometry and collapses cleanly, and it dominates the heavy species
     (cathedral_elm_l: 84% bark, 203k tris; see docs/trees.md §4b)

The card scale factor is 1/sqrt(keep_ratio), preserving total leaf area.

Tier spec (docs/trees.md §4c lever 3, near tier revised Jun 11):
  near (0–60m):         the FULL base model — rendered directly by the
                        runtime, nothing generated here. A card-pruned
                        _lod1 tier visibly thinned crowns at the closest
                        viewing distances (Jun 11 walk-around defect #1).
  lod2 (mid, 60–250m):  40% cards × 1.58, bark ≤ 8k tris (budget ≤ ~12k total)

For bark-only models (e.g., dead trees), falls back to Blender Decimate.

Run: blender4 --background --python scripts/generate_tree_lods.py
     blender4 --background --python scripts/generate_tree_lods.py -- --only=oak_l
"""

import bpy
import bmesh
import math
import os
import random
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(PROJECT_DIR, "models", "trees")

# Per-tier recipe. card_keep = fraction of leaf cards kept (survivors scale
# by 1/sqrt(card_keep)); bark_target = bark triangle budget for collapse
# decimation (None = bark untouched). lod2 is adaptive: measured base models
# (2026-06-10) range 12k–245k tris per variant, so flat ratios can't hit the
# ~12k budget — leaf and bark trade against each other per variant instead.
LOD_SPECS = {
    # "lod1" = the single mid mesh between lod0 (base) and the impostor. Renamed
    # from the legacy "lod2" 2026-06-19 (the old 4-tier lod1 was retired; this
    # surviving mid tier kept the lod2 name). Convention now: lod0 (base) /
    # lod1 (this) / impostor.
    "lod1": {"adaptive": True},
}

LOD2_TOTAL_BUDGET = 12000   # docs/trees.md §4d: lod2 ≤ ~12k incl. cards
LOD2_LEAF_BUDGET = 9000     # leaf tris before card_keep floors/caps apply
LOD2_KEEP_MIN = 0.15        # below this, card scale (2.6×+) turns crowns to blobs
LOD2_KEEP_MAX = 0.40
LOD2_BARK_MIN = 3000        # trunk silhouette floor
LOD2_BARK_MAX = 8000
# Collapse decimation has a per-island floor: Mtree bark is tens of
# thousands of separate micro-islands (measured cathedral_elm_l: 31,069
# islands, ~3 tris each — terminal twig stubs, sub-pixel beyond 60m).
# Islands smaller than this bbox diagonal may be deleted outright at lod2,
# smallest first, until the remainder is within collapse range of target.
BARK_TWIG_PRUNE_DIAG = 0.5  # metres
BARK_PRUNE_HEADROOM = 3.0   # prune until remaining <= target × headroom


def lod2_recipe(leaf_tris, bark_tris):
    """Per-variant (card_keep, bark_target) hitting LOD2_TOTAL_BUDGET.

    Leaf gets first claim up to LOD2_LEAF_BUDGET (cards carry the canopy
    look that the 60m handoff DoD compares); bark absorbs the remainder —
    it's mostly hidden behind canopy at mid range. Willow (64.8k strand
    cards) rides the KEEP_MIN floor and lands ~12.7k.
    """
    keep = max(LOD2_KEEP_MIN,
               min(LOD2_KEEP_MAX, LOD2_LEAF_BUDGET / max(leaf_tris, 1)))
    leaf_after = leaf_tris * keep
    bark_target = int(min(max(LOD2_TOTAL_BUDGET - leaf_after, LOD2_BARK_MIN),
                          LOD2_BARK_MAX))
    return keep, bark_target

SPECIES_TIERS = []
for f in sorted(os.listdir(MODEL_DIR)):
    if f.endswith(".glb") and "_lod" not in f:
        name = f.replace(".glb", "")
        if any(name.endswith(s) for s in ("_s", "_m", "_l")):
            SPECIES_TIERS.append(name)
        elif name == "dead":
            SPECIES_TIERS.append(name)


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.armatures]:
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def find_leaf_material_index(mesh):
    """Return the material index for the leaf material, or -1 if none."""
    for i, mat in enumerate(mesh.materials):
        if mat and "leaf" in mat.name.lower():
            return i
    return -1


def find_leaf_islands(bm, leaf_mat_idx):
    """Find connected components among faces with the leaf material.

    Returns a list of islands, each island being a list of face indices.
    Uses Union-Find for efficiency on large meshes.
    """
    # Build mapping: vertex -> set of leaf face indices that use it
    vert_to_faces = {}
    for f in bm.faces:
        if f.material_index == leaf_mat_idx:
            for v in f.verts:
                vert_to_faces.setdefault(v.index, []).append(f.index)

    # Union-Find
    parent = {}
    rank = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    leaf_face_indices = set()
    for f in bm.faces:
        if f.material_index == leaf_mat_idx:
            fi = f.index
            leaf_face_indices.add(fi)
            parent[fi] = fi
            rank[fi] = 0

    # Union faces that share a vertex (both must be leaf faces)
    for vert_idx, face_list in vert_to_faces.items():
        if len(face_list) < 2:
            continue
        first = face_list[0]
        for other in face_list[1:]:
            union(first, other)

    # Group by root
    groups = {}
    for fi in leaf_face_indices:
        root = find(fi)
        groups.setdefault(root, []).append(fi)

    return list(groups.values())


def leaf_aware_lod(obj, keep_ratio, seed):
    """SpeedTree-style leaf card reduction.

    Leaf cards are individually scattered quads (AAA scatter placement),
    each an independent mesh island. We randomly remove whole quads and
    scale survivors up by 1/sqrt(keep_ratio) to maintain coverage density.

    - Bark geometry: untouched here (lod2 decimates it separately)
    - Leaf geometry: random quad removal + survivor scaling
    """
    mesh = obj.data
    leaf_mat_idx = find_leaf_material_index(mesh)

    if leaf_mat_idx == -1:
        # Bark-only model (e.g., dead tree) — caller decimates instead
        return

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    islands = find_leaf_islands(bm, leaf_mat_idx)
    n_total = len(islands)

    if n_total == 0:
        bm.free()
        return

    # Deterministic shuffle so LOD variants are reproducible
    rng = random.Random(seed)
    rng.shuffle(islands)

    n_keep = max(1, round(n_total * keep_ratio))
    keep_islands = islands[:n_keep]
    remove_islands = islands[n_keep:]

    # Scale surviving cards around each card's centroid
    scale_factor = 1.0 / math.sqrt(keep_ratio)
    for island_faces in keep_islands:
        # Collect unique vertices in this island
        island_verts = set()
        for fi in island_faces:
            for v in bm.faces[fi].verts:
                island_verts.add(v)

        # Compute centroid
        cx = sum(v.co.x for v in island_verts) / len(island_verts)
        cy = sum(v.co.y for v in island_verts) / len(island_verts)
        cz = sum(v.co.z for v in island_verts) / len(island_verts)

        # Scale each vertex away from centroid
        for v in island_verts:
            v.co.x = cx + (v.co.x - cx) * scale_factor
            v.co.y = cy + (v.co.y - cy) * scale_factor
            v.co.z = cz + (v.co.z - cz) * scale_factor

    # Delete removed leaf cards
    faces_to_delete = []
    for island_faces in remove_islands:
        for fi in island_faces:
            faces_to_delete.append(bm.faces[fi])
    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

    # Clean up orphaned vertices
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    kept_faces = sum(len(isl) for isl in keep_islands)
    removed_faces = sum(len(isl) for isl in remove_islands)
    print(f"    {obj.name}: {n_total} cards → kept {n_keep} "
          f"({n_keep/n_total*100:.0f}%), scaled {scale_factor:.2f}×, "
          f"removed {removed_faces} faces, kept {kept_faces} faces")


def decimate_bark_only(obj, ratio):
    """Fallback: Blender Decimate for bark-only models (e.g., dead trees)."""
    if obj.type != 'MESH':
        return

    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError:
            pass

    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = ratio
    mod.use_collapse_triangulate = False

    orig_faces = len(obj.data.polygons)
    try:
        bpy.ops.object.modifier_apply(modifier="Decimate")
    except RuntimeError as e:
        print(f"    WARNING: Decimate failed on {obj.name}: {e}")
        if "Decimate" in obj.modifiers:
            obj.modifiers.remove(obj.modifiers["Decimate"])
        return

    new_faces = len(obj.data.polygons)
    print(f"    {obj.name}: {orig_faces} -> {new_faces} faces "
          f"({new_faces/max(orig_faces,1)*100:.0f}%) [bark decimate]")


def count_tris(mesh, leaf_mat_idx):
    """Return (leaf_tris, bark_tris) for a mesh."""
    mesh.calc_loop_triangles()
    leaf = bark = 0
    for t in mesh.loop_triangles:
        if t.material_index == leaf_mat_idx:
            leaf += 1
        else:
            bark += 1
    return leaf, bark


def prune_small_islands(obj, max_keep_tris):
    """Delete the smallest mesh islands (by bbox diagonal, ascending) until
    the object is within collapse range of the target — never touching
    islands ≥ BARK_TWIG_PRUNE_DIAG. Light-bark species skip this entirely
    (already under max_keep_tris); only the micro-island heavies get pruned.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    total = len(mesh.loop_triangles)
    if total <= max_keep_tris:
        return

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    # All faces in a separated bark part share one material — reuse the
    # island finder with that index.
    mat_idx = bm.faces[0].material_index if len(bm.faces) else 0
    islands = find_leaf_islands(bm, mat_idx)

    sized = []
    for faces in islands:
        xs, ys, zs = [], [], []
        for fi in faces:
            for v in bm.faces[fi].verts:
                xs.append(v.co.x)
                ys.append(v.co.y)
                zs.append(v.co.z)
        diag = math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
                         + (max(zs) - min(zs)) ** 2)
        sized.append((diag, faces))
    sized.sort(key=lambda s: s[0])

    doomed = []
    remaining = total
    for diag, faces in sized:
        if remaining <= max_keep_tris or diag >= BARK_TWIG_PRUNE_DIAG:
            break
        doomed.extend(bm.faces[fi] for fi in faces)
        remaining -= len(faces)
    if doomed:
        n_doomed = len(doomed)
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(mesh)
        mesh.update()
        print(f"    {obj.name}: pruned {n_doomed} twig-island faces "
              f"(<{BARK_TWIG_PRUNE_DIAG}m), {total} -> {remaining}")
    bm.free()


def decimate_bark_to_target(obj, target_tris):
    """Reduce the bark portion of a mixed leaf+bark mesh to a tri budget.

    Leaf cards must not pass through Decimate (it destroys card UVs), so:
    separate by material, prune sub-pixel twig islands, collapse-decimate
    the non-leaf parts, rejoin. The original object stays the join target so
    its name and material-slot order — which the runtime's variant-index
    pairing across tiers depends on — survive.

    Returns the joined object.
    """
    mesh = obj.data
    leaf_mat_idx = find_leaf_material_index(mesh)
    _, bark_tris = count_tris(mesh, leaf_mat_idx)
    if bark_tris <= target_tris:
        return obj

    orig_name = obj.name
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')

    parts = list(bpy.context.selected_objects)
    bark_parts = []
    for p in parts:
        pm = p.data
        if len(pm.polygons) == 0:
            continue
        midx = pm.polygons[0].material_index
        mat = pm.materials[midx] if midx < len(pm.materials) else None
        if mat and "leaf" in mat.name.lower():
            continue
        bark_parts.append(p)

    for p in bark_parts:
        prune_small_islands(p, target_tris * BARK_PRUNE_HEADROOM)
    remaining = 0
    for p in bark_parts:
        p.data.calc_loop_triangles()
        remaining += len(p.data.loop_triangles)
    if remaining > target_tris:
        ratio = target_tris / remaining
        for p in bark_parts:
            decimate_bark_only(p, ratio)

    bpy.ops.object.select_all(action='DESELECT')
    join_target = obj if obj.name in {p.name for p in parts} else parts[0]
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = join_target
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = orig_name
    return joined


def process_model(model_name, lod_name, spec):
    """Load a GLB, apply leaf-aware LOD reduction, and export."""
    src_path = os.path.join(MODEL_DIR, f"{model_name}.glb")
    dst_path = os.path.join(MODEL_DIR, f"{model_name}_{lod_name}.glb")

    if not os.path.exists(src_path):
        print(f"  SKIP: {src_path} not found")
        return False

    clear_scene()

    bpy.ops.import_scene.gltf(filepath=src_path)
    imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    if not imported:
        print(f"  SKIP: no mesh objects in {model_name}.glb")
        return False

    total_orig = sum(len(o.data.polygons) for o in imported)

    # Use model name + lod name as seed for reproducibility
    seed = hash(f"{model_name}_{lod_name}")
    adaptive = spec.get("adaptive", False)

    final_objs = []
    for obj in imported:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        leaf_mat_idx = find_leaf_material_index(obj.data)
        leaf, bark = count_tris(obj.data, leaf_mat_idx)
        if adaptive:
            ratio, bark_target = lod2_recipe(leaf, bark)
        else:
            ratio, bark_target = spec["card_keep"], spec["bark_target"]
        if leaf_mat_idx == -1:
            # Bark-only model (dead snags): plain collapse decimation
            if bark_target is not None:
                decimate_bark_only(obj, min(1.0, bark_target / max(bark, 1)))
            else:
                decimate_bark_only(obj, ratio)
        else:
            leaf_aware_lod(obj, ratio, seed)
            if bark_target is not None:
                obj = decimate_bark_to_target(obj, bark_target)
        obj.select_set(False)
        final_objs.append(obj)

    # Per-variant budget report (docs/trees.md §4d: lod2 ≤ ~12k incl. cards;
    # +1000 slack covers the KEEP_MIN floor on extreme-card species)
    for obj in final_objs:
        leaf, bark = count_tris(obj.data, find_leaf_material_index(obj.data))
        flag = ""
        if adaptive and leaf + bark > LOD2_TOTAL_BUDGET + 1000:
            flag = "  ** OVER 12k BUDGET **"
        print(f"    [{lod_name}] {obj.name}: {leaf} leaf + {bark} bark "
              f"= {leaf + bark} tris{flag}")

    total_new = sum(len(o.data.polygons) for o in final_objs)

    # Export
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=dst_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_materials='EXPORT',
        export_yup=True,
    )

    fsize = os.path.getsize(dst_path) / 1024
    print(f"  -> {dst_path} ({fsize:.0f} KB, "
          f"{total_orig} -> {total_new} faces, "
          f"{total_new/max(total_orig,1)*100:.0f}%)")
    return True


def main():
    print("\n" + "=" * 60)
    print("Tree LOD — Leaf-Aware Card Reduction (SpeedTree approach)")
    print(f"Models: {MODEL_DIR}")
    print(f"LOD levels: {list(LOD_SPECS.keys())}")
    print("=" * 60)

    # Parse --only filter
    filter_model = ""
    for arg in sys.argv:
        if arg.startswith("--only="):
            filter_model = arg.split("=", 1)[1]

    success = 0
    total = 0

    for model_name in SPECIES_TIERS:
        if filter_model and model_name != filter_model:
            continue

        # LOD policy (user 2026-06-19): m-class and up get lod0 + lod1 + impostor;
        # anything smaller than m (the _s sapling tier) gets lod0 + impostor only —
        # no lod1/_lod2. tree_builder.gd already renders the _s lod0 straight to the
        # impostor handoff when no _s_lod2 mesh exists (mid_mesh == null path).
        if model_name.endswith("_s"):
            print(f"  (skip {model_name}: sapling tier — lod0 + impostor only, no lod1)")
            continue

        print(f"\n{'─'*40}")
        print(f"  {model_name}")
        print(f"{'─'*40}")

        for lod_name, spec in LOD_SPECS.items():
            total += 1
            t0 = time.time()
            if process_model(model_name, lod_name, spec):
                success += 1
                dt = time.time() - t0
                print(f"  {lod_name} done in {dt:.1f}s")

    print(f"\n{'='*60}")
    print(f"Done: {success}/{total} LOD models generated")
    print("=" * 60)
    # Blender 4.5 --background hangs in process teardown after the script
    # completes (observed 2026-06-10, ~25min stuck on a futex; same family
    # as the impostor-baker hang in memory lessons_impostor_bake). All
    # exports are flushed and closed by here — skip teardown entirely.
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
