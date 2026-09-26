"""Fresh saved-native supports, boundaries, retained geometry and camera checks."""
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
from workspace_paths import read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def bvh(objects):
    deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[]
    for ob in objects:
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();offset=len(vertices)
        vertices.extend(ev.matrix_world@v.co for v in me.vertices)
        faces.extend([offset+i for i in tri.vertices] for tri in me.loop_triangles)
        ev.to_mesh_clear()
    assert faces
    return BVHTree.FromPolygons(vertices,faces,all_triangles=True)


s=bpy.context.scene;version=s['version'];assert version in ['G1_027r12','G1_027r13','G1_027r14']
bpy.context.view_layer.update()
r=json.loads(read_path(f'evidence/{version}/bank_shelter_build_report.json').read_text())
cp=json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text());assert sha(bpy.data.filepath)==cp['native_sha256']
for row in r['prepared_files']:assert sha(row['path'])==row['sha256']
platform=json.loads(read_path('derived/bellevue/bank_tram_shelter/platform_input.json').read_text())
collection=bpy.data.collections['47_BELLEVUE_BANK_TRAM_SHELTER']
assert set(r['created'])=={o.name for o in collection.objects}
assert not collection['public_runtime_enabled']
for name,value in r['author_states'].items():assert object_state(bpy.data.objects[name])==value,name
for name,value in r['author_meshes'].items():assert json.loads(json.dumps(mesh_digest(bpy.data.objects[name].data)))==value,name
for row in r['bounded_photo_cuts']:assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['object']].data)))==row['after']
for name,value in r['old_cameras'].items():
    ob=bpy.data.objects[name]
    assert dict(matrix=[list(v) for v in ob.matrix_world],lens=ob.data.lens,sensor_width=ob.data.sensor_width)==value
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
ground_objects=[o for o in collection.objects if o.get('bst_role')=='walk_surface']
ground=bvh(ground_objects)
soffit=bvh([bpy.data.objects['BST_CANOPY_SOFFIT']])
road_objects=[]
for row in platform['report']['current_native_road_basis']['current_road_objects']:
    ob=bpy.data.objects[row['name']]
    assert json.loads(json.dumps(mesh_digest(ob.data)))==row['actual_mesh_digest']
    road_objects.append(ob)
roads=bvh(road_objects)
standing=[];minz=8.0
for x in np.linspace(-187,-150,45):
    for y in np.linspace(111,170,61):
        p,n,_,_=ground.ray_cast(Vector((x,y,9.3)),Vector((0,0,-1)),1.5)
        if p is not None:
            assert n.z>0 and np.hypot(n.x,n.y)/n.z<.076
            standing.append(dict(xy=[float(x),float(y)],z=float(p.z),normal_z=float(n.z)))
assert len(standing)>250
edge=platform['report']['perimeter_road_comparison'];seams=[]
for i,row in enumerate(edge):
    prev=np.asarray(edge[(i-1)%len(edge)]['xy']);nxt=np.asarray(edge[(i+1)%len(edge)]['xy'])
    tangent=nxt-prev
    if np.linalg.norm(tangent)<1e-6:continue
    tangent/=np.linalg.norm(tangent);inside=np.array([-tangent[1],tangent[0]])
    xy=np.asarray(row['xy']);pin=xy+inside*.004;pout=xy-inside*.004
    a,an,_,_=ground.ray_cast(Vector((*pin,9.3)),Vector((0,0,-1)),1.5)
    b,bn,_,_=roads.ray_cast(Vector((*pout,9.3)),Vector((0,0,-1)),1.5)
    # At nearly collinear survey micro-segments, offset the sample slightly
    # farther into each physical surface if float32 leaves it on a shared edge.
    if a is None:
        pin=xy+inside*.012;a,an,_,_=ground.ray_cast(Vector((*pin,9.3)),Vector((0,0,-1)),1.5)
    if b is None:
        pout=xy-inside*.012;b,bn,_,_=roads.ray_cast(Vector((*pout,9.3)),Vector((0,0,-1)),1.5)
    assert a is not None and b is not None,('Actual perimeter missing support',i,row['xy'])
    za=a.z-float(np.dot(np.array(an)[:2],xy-pin)/an.z)
    zb=b.z-float(np.dot(np.array(bn)[:2],xy-pout)/bn.z)
    assert abs(za-row['platform_z'])<.003 and abs(zb-row['road_z'])<.003
    assert za-zb>=-.002
    seams.append(dict(xy=row['xy'],platform_z=za,road_z=zb,upstand_m=za-zb))
columns=[]
for row in r['column_checks']:
    ob=bpy.data.objects[row['object']];verts=[ob.matrix_world@v.co for v in ob.data.vertices]
    lower,upper=[],[]
    for p in verts[:64]:
        q,_,_,_=ground.ray_cast(Vector((p.x,p.y,9.3)),Vector((0,0,-1)),1.5)
        assert q is not None and -.008<p.z-q.z<-.004
        lower.append(float(p.z-q.z))
    for p in verts[-64:]:
        q,_,_,_=soffit.ray_cast(Vector((p.x,p.y,13.0)),Vector((0,0,-1)),1.5)
        assert q is not None and .003<p.z-q.z<.007
        upper.append(float(p.z-q.z))
    columns.append(dict(object=ob.name,actual_base_support_deltas_m=lower,actual_head_overlap_m=upper))
footings=[]
for row in r['footings']:
    ob=bpy.data.objects[row['object']];verts=np.array([ob.matrix_world@v.co for v in ob.data.vertices])
    bottom=verts[:,2].min();xy=np.array(row['xy'])
    p,_,_,_=ground.ray_cast(Vector((*xy,9.3)),Vector((0,0,-1)),1.5)
    assert p is not None and bottom-p.z<.002,(ob.name,bottom,None if p is None else p.z)
    footings.append(dict(object=ob.name,bottom_minus_ground_m=float(bottom-p.z)))
cameras=[]
for row in r['review_cameras']:
    cam=bpy.data.objects[row['name']]
    p,_,_,_=ground.ray_cast(Vector((cam.location.x,cam.location.y,9.3)),Vector((0,0,-1)),1.5)
    assert p is not None and abs(cam.location.z-p.z-1.65)<.001
    cameras.append(dict(camera=cam.name,actual_eye_height_m=float(cam.location.z-p.z)))
if version in ['G1_027r13','G1_027r14']:
    runpy.run_path(str(Path(__file__).with_name('blender_check_bank_tram_residuals.py')),run_name='__main__')
    repair_check=json.loads(read_path(f'evidence/{version}/residual_fresh_checks.json').read_text())
    assert repair_check['process_id']==os.getpid() and repair_check['passed']
if version=='G1_027r14':
    runpy.run_path(str(Path(__file__).with_name('blender_check_bank_tram_curvature.py')),run_name='__main__')
    curve_check=json.loads(read_path(f'evidence/{version}/curvature_fresh_checks.json').read_text())
    assert curve_check['process_id']==os.getpid() and curve_check['passed']
report=dict(version=version,native_sha256=cp['native_sha256'],process_id=os.getpid(),passed=True,
    ground_support_samples=standing,actual_perimeter_seams=seams,columns=columns,footings=footings,cameras=cameras,
    source_preserved=2039,old_cameras_preserved=len(r['old_cameras']),
    visual_acceptance=False,natural_use_verified=False,runtime_verified=False,
    limits=['Normals/support rays do not certify accessibility or full swept-body collision.','Fixture geometry has no live ticketing or traffic connection yet.','Unresolved information-board subtype remains inferred, not surveyed.'])
write_path(f'evidence/{version}/bank_shelter_fresh_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BANK_SHELTER_CHECKED',json.dumps(dict(ground=len(standing),seams=len(seams),columns=len(columns),footings=len(footings),cameras=len(cameras))),flush=True)
