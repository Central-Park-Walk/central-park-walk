#!/usr/bin/env python3
"""Bake crown-interior depth into tree-model COLOR_0 alpha (trees.md §6).

Per leaf primitive: robust ellipsoid fit of the leaf-vertex cloud (p5/p95
centroid + per-axis radii), per-vertex normalized radius
    rho = |(p - c) / radii|, rescaled so the p95 of rho -> 1.0
written to COLOR_0 alpha. rho ~ 0 = crown core (heavily sky-occluded),
1 = outer shell. The shaders map rho -> AO (canopy_ao global uniform), so
the GLB data stays pure geometry and the look tunes without re-baking.

Implementation is DIRECT GLB SURGERY, not a Blender roundtrip: the Blender
glTF exporter writes COLOR_0 as VEC3 whenever the material node tree does
not consume vertex alpha (verified 2026-06-11 — alpha is dropped on every
export path), and a full import/export cycle risks perturbing untracked
binary assets. Here we append a new VEC4 UNSIGNED_BYTE-normalized COLOR_0
(RGB copied from the existing accessor = wind weights, A = rho for leaf
primitives / 1.0 for bark) to the BIN chunk and repoint the attribute.
Original accessors are left in place (dead data, ~12 B/vertex).

Idempotent: re-running refits rho and appends again (file grows ~4 B/vertex
per run — run once, or restore from backup first for repeated experiments).

Usage:
    scripts/bake_crown_ao.py            # all models/trees/*.glb
    scripts/bake_crown_ao.py oak        # filter by substring
"""

import json
import os
import struct
import sys

import numpy as np

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJ, "models", "trees")

COMP_DTYPE = {5120: np.int8, 5121: np.uint8, 5122: np.int16,
              5123: np.uint16, 5125: np.uint32, 5126: np.float32}
COMP_SIZE = {k: np.dtype(v).itemsize for k, v in COMP_DTYPE.items()}
TYPE_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_accessor(gltf, binchunk, idx):
    acc = gltf["accessors"][idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n = acc["count"]
    ncomp = TYPE_COUNT[acc["type"]]
    dtype = COMP_DTYPE[acc["componentType"]]
    csize = COMP_SIZE[acc["componentType"]]
    stride = bv.get("byteStride") or ncomp * csize
    if stride == ncomp * csize:
        a = np.frombuffer(binchunk, dtype, n * ncomp, base).reshape(n, ncomp)
    else:
        rows = np.frombuffer(binchunk, np.uint8, n * stride, base)
        rows = rows.reshape(n, stride)[:, :ncomp * csize].copy()
        a = rows.view(dtype).reshape(n, ncomp)
    if acc.get("normalized") and dtype != np.float32:
        a = a.astype(np.float32) / np.iinfo(dtype).max
    return np.asarray(a, dtype=np.float32)


def crown_rho(pts):
    lo = np.percentile(pts, 5.0, axis=0)
    hi = np.percentile(pts, 95.0, axis=0)
    c = (lo + hi) * 0.5
    radii = np.maximum((hi - lo) * 0.5, 0.25)
    rho = np.linalg.norm((pts - c) / radii, axis=1)
    p95 = max(np.percentile(rho, 95.0), 1e-3)
    return np.clip(rho / p95, 0.0, 1.0)


def process(path):
    raw = open(path, "rb").read()
    magic, _ver, total = struct.unpack_from("<III", raw, 0)
    assert magic == 0x46546C67, f"not a GLB: {path}"
    jlen, jtype = struct.unpack_from("<II", raw, 12)
    assert jtype == 0x4E4F534A
    gltf = json.loads(raw[20:20 + jlen])
    bofs = 20 + jlen
    blen, btype = struct.unpack_from("<II", raw, bofs)
    assert btype == 0x004E4942
    binchunk = bytearray(raw[bofs + 8:bofs + 8 + blen])

    mats = gltf.get("materials", [])
    appended = bytearray()
    baked = skipped = 0

    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim["attributes"]
            if "COLOR_0" not in attrs or "POSITION" not in attrs:
                skipped += 1
                continue
            mat_name = ""
            if "material" in prim:
                mat_name = mats[prim["material"]].get("name", "").lower()
            is_leaf = "leaf" in mat_name or "foliage" in mat_name

            rgb = read_accessor(gltf, binchunk, attrs["COLOR_0"])[:, :3]
            n = rgb.shape[0]
            if is_leaf and n >= 16:
                pos = read_accessor(gltf, binchunk, attrs["POSITION"])
                alpha = crown_rho(pos)
                baked += 1
            else:
                alpha = np.ones(n, dtype=np.float32)

            rgba = np.empty((n, 4), dtype=np.float32)
            rgba[:, :3] = np.clip(rgb, 0.0, 1.0)
            rgba[:, 3] = alpha
            data = np.round(rgba * 255.0).astype(np.uint8).tobytes()

            new_bv = len(gltf["bufferViews"])
            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": blen + len(appended),
                "byteLength": len(data),
                # byteStride required when two accessors could share the
                # view; single-accessor tightly-packed is fine without.
            })
            new_acc = len(gltf["accessors"])
            gltf["accessors"].append({
                "bufferView": new_bv,
                "componentType": 5121,
                "normalized": True,
                "count": n,
                "type": "VEC4",
            })
            attrs["COLOR_0"] = new_acc
            appended += data
            if len(appended) % 4:
                appended += b"\x00" * (4 - len(appended) % 4)

    new_blen = blen + len(appended)
    gltf["buffers"][0]["byteLength"] = new_blen
    jout = json.dumps(gltf, separators=(",", ":")).encode()
    if len(jout) % 4:
        jout += b" " * (4 - len(jout) % 4)
    out = bytearray()
    out += struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(jout) + 8 + new_blen)
    out += struct.pack("<II", len(jout), 0x4E4F534A) + jout
    out += struct.pack("<II", new_blen, 0x004E4942) + binchunk + appended
    open(path, "wb").write(out)
    print(f"  {os.path.basename(path)}: {baked} leaf prim(s) baked"
          f"{', ' + str(skipped) + ' prims without COLOR_0' if skipped else ''}")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    files = sorted(f for f in os.listdir(MODEL_DIR) if f.endswith(".glb"))
    if only:
        files = [f for f in files if only in f]
    print(f"crown AO bake: {len(files)} models")
    for f in files:
        process(os.path.join(MODEL_DIR, f))
    print("DONE")


if __name__ == "__main__":
    main()
