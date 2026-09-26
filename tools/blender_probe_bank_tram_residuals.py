"""Inspect visible scan remnants against the saved r12 cameras and geometry.

No expanded removal mask is assumed. Export current local context and ray hits
before deciding which scan fragments can be replaced by existing construction.
"""
from pathlib import Path
import hashlib
import json
import os
import runpy
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path

s = bpy.context.scene
assert s['version'] == 'G1_027r12'
native = Path(bpy.data.filepath)
before = native.stat()
digest = hashlib.sha256(native.read_bytes()).hexdigest()
assert digest == 'aa40c5cb2834120b6a98c6b1311d65c0c1eb2e4aca9174aafc0c61d76bbedea2'
probe_path = write_path('derived/bellevue/bank_tram_shelter/native_probe_G1_027r12_platform_full.json')
assert not probe_path.exists(), 'Retain the previous actual native probe.'
runpy.run_path(str(ROOT/'tools/blender_probe_bank_tram_shelter.py'),
               init_globals={'FULL_PLATFORM': True}, run_name='__main__')
probe = json.loads(probe_path.read_text())
names = [r['name'] for r in probe['objects'] if r['kind'] == 'retained_photo']
objects = [bpy.data.objects[n] for n in names]
objects += [o for o in bpy.data.collections['47_BELLEVUE_BANK_TRAM_SHELTER'].objects if o.type == 'MESH']
deps = bpy.context.evaluated_depsgraph_get()
vertices, faces, meta = [], [], []
for ob in objects:
    assert not ob.hide_render
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    for tri in me.loop_triangles:
        points = [ev.matrix_world @ me.vertices[i].co for i in tri.vertices]
        at = len(vertices)
        vertices.extend(points)
        faces.append([at, at+1, at+2])
        meta.append(dict(object=ob.name, polygon=tri.polygon_index,
                         triangle=[list(p) for p in points],
                         material=ob.material_slots[tri.material_index].material.name if ob.material_slots else None))
    ev.to_mesh_clear()
tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
spec = json.loads(read_path('derived/bellevue/bank_tram_shelter/build_input.json').read_text())
A, U, N = [np.asarray(spec[k]) for k in ['axis_start_local_xy','axis_unit_xy','side_unit_xy']]
# Pixel coordinates are selected from the actual full-size r12 NORTH render.
selections = {'BST_QA_NORTH': [(790,140),(995,181),(871,411),(984,613),(1052,756),
                             (482,632),(456,716),(529,558),(570,91),(702,64),(712,440)]}
optional = ROOT/'derived/bellevue/bank_tram_shelter/r12_residual_pixel_selection.json'
if optional.is_file():
    selections.update(json.loads(optional.read_text()))
rows = []
for camera, pixels in selections.items():
    cam = bpy.data.objects[camera]
    size = (1400,960) if camera.startswith('BST_') else (1280,840)
    s.render.resolution_x, s.render.resolution_y = size
    s.render.resolution_percentage = 100
    frame = cam.data.view_frame(scene=s)
    xmin,xmax = min(p.x for p in frame),max(p.x for p in frame)
    ymin,ymax = min(p.y for p in frame),max(p.y for p in frame)
    for x,y in pixels:
        point = Vector((xmin+(x+.5)/size[0]*(xmax-xmin),
                        ymax-(y+.5)/size[1]*(ymax-ymin),frame[0].z))
        ray = (cam.matrix_world.to_3x3()@point).normalized()
        p,n,i,distance = tree.ray_cast(cam.matrix_world.translation,ray,70)
        row = dict(camera=camera,pixel=[x,y],hit=p is not None)
        if p is not None:
            local = np.asarray(p)[:2]-A
            row.update(**meta[i],xyz=list(p),normal=list(n),distance=distance,
                       shelter_uvz=[float(local@U),float(local@N),float(p.z)])
        rows.append(row)
out = dict(version=s['version'],native_sha256=digest,process_id=os.getpid(),
           source_images={name:str(read_path(f'evidence/G1_027r12/{name}.png')) for name in selections},
           scope='Current local photographic meshes plus evaluated BST author meshes; other buildings/roads are not occlusion candidates.',
           native_changed=False,actual_local_probe=str(probe_path),rays=rows)
write_path('evidence/G1_027r12/visible_scan_residual_probe.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
assert native.stat().st_size == before.st_size and native.stat().st_mtime_ns == before.st_mtime_ns
print('BANK_SHELTER_RESIDUAL_PROBE',json.dumps(out),flush=True)
