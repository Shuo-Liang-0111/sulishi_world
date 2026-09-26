"""Independently revisit diagnosed r12 pixels in the saved repaired native."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path

s = bpy.context.scene
assert s['version'] in ['G1_027r13','G1_027r14','G1_027r15']
d = json.loads(read_path('derived/bellevue/bank_tram_shelter/residual_repair_r13.json').read_text())
probe = json.loads(read_path('derived/bellevue/bank_tram_shelter/native_probe_G1_027r12_platform_full.json').read_text())
names = [r['name'] for r in probe['objects'] if r['kind']=='retained_photo']
vertices,faces,owners = [],[],[]
for name in names:
    ob = bpy.data.objects[name]
    assert not ob.modifiers and not ob.hide_render
    base = len(vertices)
    vertices.extend(ob.matrix_world@v.co for v in ob.data.vertices)
    for face in ob.data.polygons:
        assert len(face.vertices)==3
        faces.append([base+i for i in face.vertices])
        owners.append(name)
tree = BVHTree.FromPolygons(vertices,faces,all_triangles=True)
results = []
saved_resolution = (s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage)
try:
    for category in ['diagnosed_target_hits','protected_hits']:
        for old in d[category]:
            camera = bpy.data.objects[old['camera']]
            width,height = (1400,960) if camera.name.startswith('BST_') else (1280,840)
            s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage = width,height,100
            frame = camera.data.view_frame(scene=s)
            xmin,xmax = min(p.x for p in frame),max(p.x for p in frame)
            ymin,ymax = min(p.y for p in frame),max(p.y for p in frame)
            x,y = old['pixel']
            point = Vector((xmin+(x+.5)/width*(xmax-xmin),ymax-(y+.5)/height*(ymax-ymin),frame[0].z))
            direction = (camera.matrix_world.to_3x3()@point).normalized()
            p,n,i,distance = tree.ray_cast(camera.matrix_world.translation,direction,70.)
            row = dict(camera=camera.name,pixel=old['pixel'],previous_object=old['object'],
                       previous_distance=old['distance'],category=category,hit=p is not None)
            if p is not None:
                row.update(object=owners[i],distance=distance,xyz=list(p))
            if category == 'diagnosed_target_hits':
                assert p is None or distance > old['distance']+.03,('Unrepaired diagnosed foreground scan',row)
            else:
                assert p is not None and owners[i]==old['object'] and (p-Vector(old['xyz'])).length<.0005,('Protected context changed',row)
            results.append(row)
finally:
    s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage = saved_resolution

fixtures = json.loads(read_path('derived/bellevue/bank_tram_shelter/fixtures_input.json').read_text())
wood = []
for index,bench in enumerate(fixtures['benches']):
    axis = np.asarray(bench['axis'])
    for part in ['SEAT','BACK']:
        ob = bpy.data.objects[f'BST_BENCH_{index}_{part}']
        uv = ob.data.uv_layers.active
        longitudinal_edges = []
        for face in ob.data.polygons:
            if abs(np.asarray(face.normal)[:2]@axis)>.9:continue
            for j,li in enumerate(face.loop_indices):
                lj = face.loop_indices[(j+1)%len(face.loop_indices)]
                a = np.asarray(ob.data.vertices[ob.data.loops[li].vertex_index].co)
                b = np.asarray(ob.data.vertices[ob.data.loops[lj].vertex_index].co)
                delta = b-a
                if abs(delta[:2]@axis)<1.:continue
                duv = np.asarray(uv.data[lj].uv)-np.asarray(uv.data[li].uv)
                assert abs(duv[0])<1e-5 and abs(abs(duv[1])*2.-np.linalg.norm(delta))<1e-5
                longitudinal_edges.append(float(np.linalg.norm(delta)))
        assert longitudinal_edges
        wood.append(dict(object=ob.name,actual_longitudinal_edges_checked=len(longitudinal_edges),texture_grain='V'))

with Path(bpy.data.filepath).open('rb') as stream:
    digest = hashlib.file_digest(stream,'sha256').hexdigest()
out = dict(version=s['version'],native_sha256=digest,process_id=os.getpid(),passed=True,
           actual_camera_rays=results,wood_longitudinal_uv=wood,
           diagnosed_near_scan_pixels_cleared=sum(r['category']=='diagnosed_target_hits' for r in results),
           protected_context_pixels_preserved=sum(r['category']=='protected_hits' for r in results),
           visual_acceptance=False,natural_use_verified=False,
           limit='Finite diagnosed pixels and geometry checks do not replace full multi-view visual review or actual navigation.')
write_path(f"evidence/{s['version']}/residual_fresh_checks.json").write_text(json.dumps(out,indent=2),encoding='utf-8')
print('BANK_RESIDUAL_CHECKED',json.dumps(dict(cleared=out['diagnosed_near_scan_pixels_cleared'],protected=out['protected_context_pixels_preserved'],wood=len(wood))),flush=True)
