"""Read-only saved-r14 pixel/mesh evidence for the remaining bank roof remnants."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path
from blender_geometry_fingerprint import mesh_digest

s = bpy.context.scene
assert s['version'] == 'G1_027r14'
native = Path(bpy.data.filepath)
before = native.stat()
digest = hashlib.sha256(native.read_bytes()).hexdigest()
cp = json.loads(read_path('evidence/G1_027r14/checkpoint.json').read_text())
assert digest == cp['native_sha256']
target = write_path('derived/ubs_theaterstrasse20/r14_upper_residual_probe.json')
assert not target.exists()
spec = json.loads(read_path('derived/ubs_theaterstrasse20/build_input.json').read_text())
ring = np.asarray(spec['footprint_local'])
lo, hi = ring.min(axis=0)-6., ring.max(axis=0)+6.
photo, selected = [], []
for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
    if ob.type != 'MESH' or not ob.data.polygons:
        continue
    bounds = np.asarray([ob.matrix_world @ Vector(p) for p in ob.bound_box])
    if np.any(bounds[:, :2].max(axis=0) < lo) or np.any(bounds[:, :2].min(axis=0) > hi):
        continue
    assert not ob.hide_render
    photo.append(ob)
selected = photo + [o for o in s.objects if o.type == 'MESH' and o.name.startswith(('UF_', 'BST_', 'SG_'))]
deps = bpy.context.evaluated_depsgraph_get()
vertices, faces, owners = [], [], []
for ob in selected:
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    base = len(vertices)
    vertices.extend(ev.matrix_world @ v.co for v in me.vertices)
    for t in me.loop_triangles:
        faces.append([base+i for i in t.vertices])
        owners.append((ob.name, int(t.polygon_index)))
    ev.to_mesh_clear()
tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
camera = bpy.data.objects['UF_QA_FRONT']
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1280, 840, 100
frame = camera.data.view_frame(scene=s)
xmin, xmax = min(p.x for p in frame), max(p.x for p in frame)
ymin, ymax = min(p.y for p in frame), max(p.y for p in frame)
selections = [(231, 61), (354, 64), (505, 52), (740, 61), (889, 60), (963, 74),
              (367, 578), (573, 597), (730, 586), (1190, 334)]
rays = []
for x, y in selections:
    local = Vector((xmin+(x+.5)/1280*(xmax-xmin), ymax-(y+.5)/840*(ymax-ymin), frame[0].z))
    direction = (camera.matrix_world.to_3x3() @ local).normalized()
    hit, normal, index, distance = tree.ray_cast(camera.matrix_world.translation, direction, 150.)
    row = dict(pixel=[x, y], hit=hit is not None)
    if hit is not None:
        row.update(object=owners[index][0], evaluated_polygon=owners[index][1], xyz=list(hit),
                   normal=list(normal), distance_m=distance)
    rays.append(row)
hits = {r['object'] for r in rays if r.get('object', '').startswith('CTX_')}
geometry = []
for ob in photo:
    if ob.name not in hits:
        continue
    me = ob.data
    assert all(len(p.vertices) == 3 for p in me.polygons) and not ob.modifiers
    geometry.append(dict(object=ob.name, mesh_digest=mesh_digest(me),
                         matrix_world=[list(r) for r in ob.matrix_world],
                         vertices_world=[list(ob.matrix_world @ v.co) for v in me.vertices],
                         faces=[list(p.vertices) for p in me.polygons],
                         loop_uv=[list(v.uv) for v in me.uv_layers.active.data]))
out = dict(version=s['version'], native_sha256=digest, process_id=os.getpid(),
           camera=camera.name, image='evidence/G1_027r14/UF_QA_FRONT.png', rays=rays,
           diagnosed_current_photo_geometry=geometry, candidates_considered=len(photo),
           native_changed=False, replacement_decided=False,
           limit='Pixel evidence only; each fragment still needs association with a real rebuilt envelope before any replacement.')
target.write_text(json.dumps(out, indent=2), encoding='utf-8')
assert native.stat().st_size == before.st_size and native.stat().st_mtime_ns == before.st_mtime_ns
print('UBS_UPPER_RESIDUAL_PROBE', json.dumps(dict(photo_hits=sorted(hits), rays=len(rays))), flush=True)
