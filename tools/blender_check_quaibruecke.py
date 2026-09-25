"""Independent mesh rays/contact checks for the actual023 connection."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R=WORKSPACE;s=bpy.context.scene
assert s['version'].startswith(('G1_023','G1_024','G1_025','G1_026','G1_027'))
P=json.loads((read_path(R/'derived/bellevue/quaibruecke_connection/build_input.json')).read_text())
C=bpy.data.collections['37_QUAIBRUECKE_CONNECTION'];O=np.array(P['origin'])
assert len(C.objects)>=815
floors=[ob for ob in C.objects if ob.get('surface_role')=='paving']
expected=sum(p['area_m2'] for p in P['parts'] if p['role']=='paving')
area=0.;invalid=[]
for ob in C.objects:
    assert ob.type=='MESH' and ob.get('source_id'),ob.name
    v=np.array([(ob.matrix_world@q.co)[:] for q in ob.data.vertices])
    assert np.isfinite(v).all()
    if ob in floors:
        for face in ob.data.polygons:
            if face.normal.z<.5:continue
            q=v[list(face.vertices)]
            area+=sum(abs(np.cross(q[i,:2]-q[0,:2],q[i+1,:2]-q[0,:2]))/2 for i in range(1,len(q)-1))
    for face in ob.data.polygons:
        if face.area<1e-11:invalid.append([ob.name,face.index])
assert not invalid,invalid[:15]
assert abs(area-expected)<.003,(area,expected)


def bvh(objects):
    vertices=[];faces=[]
    for ob in objects:
        start=len(vertices);vertices.extend([ob.matrix_world@q.co for q in ob.data.vertices])
        faces.extend([[i+start for i in face.vertices] for face in ob.data.polygons])
    return BVHTree.FromPolygons(vertices,faces,all_triangles=False)


floor_bvh=bvh(floors)
old_walls=[ob for ob in bpy.data.collections['36_RIVIERA_LOWER_APPROACH'].objects if ob.name.startswith('RL_RETAINING_WALL_')]
check_old_walls=s['version']!='G1_023'
bridge_bvh=bvh([ob for ob in C.objects if ob.name.startswith(('QB_GIRDER_','QB_BRIDGE_SLAB_','QB_CROSS_DIAPHRAGM_'))]+(old_walls if check_old_walls else []))
solid_bvh=bvh([ob for ob in C.objects if ob.get('surface_role')!='paving']+(old_walls if check_old_walls else []))
route=np.array(P['route'])
length=np.linalg.norm(np.diff(route,axis=0),axis=1);accum=np.r_[0,np.cumsum(length)]
samples=[];missing=[];headroom=[];side=[]
for st in np.arange(.12,accum[-1]-.12,.25):
    i=min(int(np.searchsorted(accum,st,side='right')-1),len(length)-1)
    u=(st-accum[i])/length[i];xy=route[i]*(1-u)+route[i+1]*u-O[:2]
    hit,_,_,_=floor_bvh.ray_cast(Vector((*xy,25)),Vector((0,0,-1)))
    if hit is None:missing.append(float(st));continue
    p,_,_,_=bridge_bvh.ray_cast(Vector((*xy,hit.z+.04)),Vector((0,0,1)))
    clearance=float(p.z-hit.z) if p is not None else None
    if clearance is not None:headroom.append(clearance)
    samples.append({'station_m':float(st),'xy_local':xy.tolist(),'floor_ln02_m':float(hit.z+400),'bridge_clearance_m':clearance})
    n=route[i+1]-route[i];n=np.array([-n[1],n[0]])/length[i]
    for sign in [-1,1]:
        p,_,_,dist=solid_bvh.ray_cast(Vector((*xy,hit.z+.9)),Vector((*n*sign,0)),2.)
        if p is not None:side.append(float(dist))
assert not missing,('Missing floor along source-informed centreline',missing[:15])
assert min(headroom)>2.1,('Low overhead',min(headroom))
assert min(side)>.28,('Narrow/broken path',min(side))

old_floor=bvh([o for o in bpy.data.collections['36_RIVIERA_LOWER_APPROACH'].objects if o.get('surface_role')=='paving'])
a=np.array([2683488.212,1246848.608]);b=np.array([2683490.079,1246847.164])
t=(b-a)/np.linalg.norm(b-a);n=np.array([-t[1],t[0]])
joins=[]
for u in np.linspace(.2,.8,7):
    q=a*(1-u)+b*u-O[:2]
    # Identify which side is the existing low promenade instead of relying on
    #ring orientation. Compare the actual two saved mesh surfaces.
    for sign in [-1,1]:
        pa,_,_,_=old_floor.ray_cast(Vector((*(q+n*.025*sign),25)),Vector((0,0,-1)))
        pb,_,_,_=floor_bvh.ray_cast(Vector((*(q-n*.025*sign),25)),Vector((0,0,-1)))
        if pa is not None and pb is not None:
            joins.append(float(abs(pa.z-pb.z)));break
assert len(joins)>=5 and max(joins)<.025,joins

treads=[]
for i in range(13):
    ob=bpy.data.objects[f'QB_STAIR_{i:02}_NOSE'];v=np.array([(ob.matrix_world@q.co)[:] for q in ob.data.vertices])
    treads.append(float(v[:,2].max()+400))
rises=np.diff(treads)
assert max(abs(rises-P['report']['south_stair_rise_m']))<.00002
assert .14<min(rises)<=max(rises)<.20

missing_images=[]
for image in bpy.data.images:
    if image.source!='FILE' or image.packed_file or not image.filepath:continue
    if not Path(bpy.path.abspath(image.filepath,library=image.library)).is_file():missing_images.append(image.name)
assert not missing_images,missing_images
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
record=dict(version=s['version'],objects=len(C.objects),actual_floor_plan_area_m2=area,
            source_floor_area_error_m2=area-expected,route_probe_count=len(samples),
            actual_minimum_bridge_headroom_m=min(headroom),minimum_side_ray_distance_m=min(side),
            north_seam_samples=len(joins),north_seam_max_delta_m=max(joins),
            south_stair_rise_range_m=[float(min(rises)),float(max(rises))],
            missing_images=missing_images,photo_originals=2039,
            old_retaining_walls_included_in_clearance=check_old_walls,
            hidden_floor_profile_inferred=True,geometry_checks_passed=True,
            photo_context_collision_not_included=True,actual_walking_not_verified=True,
            visual_acceptance=False,route_samples=samples)
(write_path(R/'evidence'/s['version']/'connection_geometry_checks.json')).write_text(json.dumps(record,indent=2))
print('UNDERPASS_CHECKS',json.dumps({k:v for k,v in record.items() if k!='route_samples'}),flush=True)
