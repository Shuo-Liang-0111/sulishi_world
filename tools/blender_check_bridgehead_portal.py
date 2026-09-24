"""Measure both bridgehead levels and actual route clearance in the saved mesh."""
from pathlib import Path
import hashlib,json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version'].startswith('G1_026')
P=json.loads((R/'derived/bellevue/bridgehead_portal/build_input.json').read_text())
C=bpy.data.collections['42_BRIDGEHEAD_PORTAL'];assert len(C.objects)==len(P['parts'])
assert C['input_sha256']==hashlib.sha256((R/'derived/bellevue/bridgehead_portal/build_input.json').read_bytes()).hexdigest()
def bvh(objects):
    vertices=[];faces=[]
    for ob in objects:
        off=len(vertices);vertices.extend(ob.matrix_world@v.co for v in ob.data.vertices)
        faces.extend([[off+i for i in p.vertices] for p in ob.data.polygons])
    return BVHTree.FromPolygons(vertices,faces,all_triangles=False)
areas={};bad=[]
for ob in C.objects:
    area=0.
    for p in ob.data.polygons:
        if p.area<1e-11:bad.append([ob.name,p.index])
        if p.normal.z>.5:
            v=np.array([ob.data.vertices[i].co[:] for i in p.vertices])
            area+=sum(abs(np.cross(v[k,:2]-v[0,:2],v[k+1,:2]-v[0,:2]))/2 for k in range(1,len(v)-1))
    areas[ob.name]=float(area)
assert not bad,bad[:4]
actual=sum(v for k,v in areas.items() if k.startswith('BP_PAVING'))
assert abs(actual-P['report']['restored_upper_paving_m2'])<.002
solid=bvh(list(C.objects))
rows=json.loads((R/'evidence/G1_025r1/connection_geometry_checks.json').read_text())['route_samples']
clearances=[];blocked=[]
for row in rows:
    floor=row['floor_ln02_m']-400;p=Vector((*row['xy_local'],floor+.08))
    hit,normal,face,distance=solid.ray_cast(p,Vector((0,0,1)),6.)
    if hit is not None:
        clearances.append(distance+.08)
        if distance+.08<2.12:blocked.append(dict(station=row['station_m'],clearance_m=distance+.08))
assert not blocked,blocked
upper=bvh([o for o in C.objects if o.name.startswith('BP_PAVING')])
prior=bvh([o for o in bpy.data.collections['40_BRIDGEHEAD_BANK'].objects if o.get('surface_role')=='paving'])
# Boundary coordinates from source input; actual newly written float32 faces
# can sit a few micrometres either side of the mathematical boundary.
seams=[];miss=[]
for part in P['parts']:
    if part['role']!='paving':continue
    for q in part['vertices']:
        p=Vector((q[0],q[1],20.))
        a,_,_,_=upper.ray_cast(p,Vector((0,0,-1)),20.)
        b,_,_,_=prior.ray_cast(p,Vector((0,0,-1)),20.)
        if a is not None and b is not None:seams.append(abs(a.z-b.z))
assert seams and max(seams)<.015,(len(seams),max(seams) if seams else None)
missing=[im.name for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath,library=im.library)).is_file()]
assert not missing
report=dict(version=s['version'],objects=len(C.objects),actual_new_paving_m2=actual,route_probes=len(rows),
    new_upper_structure_route_hits=len(clearances),minimum_new_structure_clearance_m=min(clearances),
    added_route_obstructions=blocked,shared_surface_probe_count=len(seams),shared_surface_max_difference_m=max(seams),
    original_photo_sources=len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects),missing_images=missing,
    geometry_checks_passed=True,all_photo_collision_checked=False,natural_use_verified=False,runtime_equivalent=False)
(R/'evidence'/s['version']/'portal_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PORTAL_GEOMETRY_CHECKS',json.dumps(report),flush=True)
