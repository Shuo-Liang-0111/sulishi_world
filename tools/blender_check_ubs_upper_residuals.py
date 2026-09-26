"""Independent saved-native ray, preservation and eave-remnant checks."""
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
assert s['version'] == 'G1_027r15'
version = s['version']
cp = json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == cp['native_sha256']
d = json.loads(read_path('derived/ubs_theaterstrasse20/upper_residual_repair_r15.json').read_text())
p = json.loads(read_path('derived/ubs_theaterstrasse20/r14_upper_residual_probe_with_eave.json').read_text())
r = json.loads(read_path(f'evidence/{version}/upper_residual_build_report.json').read_text())
for row in d['actual_upper_objects']:
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['object']].data))) == row['mesh_digest']
for row in r['photo_cuts']:
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['object']].data))) == row['after']
assert sum(row['changed_faces'] for row in r['photo_cuts']) == 136
names = {row['object'] for row in p['diagnosed_current_photo_geometry']}
selected = [o for o in s.objects if o.type == 'MESH' and (o.name in names or o.name.startswith(('UF_','BST_','SG_')))]
deps = bpy.context.evaluated_depsgraph_get()
vertices, faces, owners = [], [], []
for ob in selected:
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    base = len(vertices)
    vertices.extend(ev.matrix_world @ v.co for v in me.vertices)
    for tri in me.loop_triangles:
        faces.append([base+i for i in tri.vertices])
        owners.append(ob.name)
    ev.to_mesh_clear()
tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
camera = bpy.data.objects['UF_QA_FRONT']
old_resolution = s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage
rows = []
try:
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1280, 840, 100
    frame = camera.data.view_frame(scene=s)
    xmin, xmax = min(v.x for v in frame), max(v.x for v in frame)
    ymin, ymax = min(v.y for v in frame), max(v.y for v in frame)
    for category in ['diagnosed_target_hits','protected_hits']:
        for old in d[category]:
            x, y = old['pixel']
            local = Vector((xmin+(x+.5)/1280*(xmax-xmin), ymax-(y+.5)/840*(ymax-ymin), frame[0].z))
            direction = (camera.matrix_world.to_3x3() @ local).normalized()
            point, normal, index, distance = tree.ray_cast(camera.matrix_world.translation, direction, 150)
            row = dict(category=category, pixel=old['pixel'], previous_object=old['object'], hit=point is not None)
            if point is not None:
                row.update(object=owners[index], xyz=list(point), distance_m=distance)
            if category == 'protected_hits':
                assert point is not None and owners[index] == old['object'] and (point-Vector(old['xyz'])).length < .0005, row
            else:
                assert point is None or (owners[index] != old['object'] and distance > old['distance_m']+.025), row
            rows.append(row)
finally:
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = old_resolution
out = dict(version=version, native_sha256=cp['native_sha256'], process_id=os.getpid(), passed=True,
           actual_camera_rays=rows, actual_rebuilt_upper_objects_unchanged=len(d['actual_upper_objects']),
           changed_photo_tiles=len(r['photo_cuts']), visual_acceptance=False, natural_use_verified=False,
           limit='Finite diagnosed pixels are followed by original-camera and oblique actual render review; not whole-building or navigation acceptance.')
write_path(f'evidence/{version}/upper_residual_fresh_checks.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('UBS_EAVE_REPAIR_CHECKED', json.dumps(dict(targets=4, protected=6, unchanged_upper_objects=6)), flush=True)
