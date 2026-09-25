"""Inspect actual027 meshes, source masts, seam rays and underpass clearance."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
from pathlib import Path
import hashlib,json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=WORKSPACE;D=R/'derived/bellevue/bridge_deck';s=bpy.context.scene
assert s['version'] in ['G1_027','G1_027r1','G1_027r2','G1_027r3'];C=bpy.data.collections['43_BRIDGE_DECK']
P=json.loads((read_path(D/'build_input.json')).read_text());O=np.array(P['origin'])
assert C['geometry_complete'] and C['input_sha256']==hashlib.sha256((read_path(D/'build_input.json')).read_bytes()).hexdigest()
areas={};invalid=[]
for ob in C.objects:
    assert ob.type=='MESH' and ob.get('source_id'),ob.name
    v=np.array([q.co[:] for q in ob.data.vertices]);assert np.isfinite(v).all()
    for f in ob.data.polygons:
        if f.area<1e-11:invalid.append((ob.name,f.index))
        if f.normal.z>.6:
            q=v[list(f.vertices)];area=sum(abs(np.cross(q[k,:2]-q[0,:2],q[k+1,:2]-q[0,:2]))/2 for k in range(1,len(q)-1))
            role=ob['surface_role'];areas[role]=areas.get(role,0)+area
assert not invalid,invalid[:15]
assert abs(areas['asphalt_walk']-P['report']['raised_walk_cycle_m2'])<.015,areas
road=sum(areas[role] for role in ['asphalt_road','asphalt_track','rail','drain'])
assert abs(road-P['report']['road_m2'])<.015,road
def bvh(objects):
    v=[];f=[]
    for ob in objects:
        start=len(v);v.extend(ob.matrix_world@q.co for q in ob.data.vertices)
        f.extend([[start+i for i in p.vertices] for p in ob.data.polygons])
    return BVHTree.FromPolygons(v,f,all_triangles=False)
ground=bvh([o for o in C.objects if o.get('surface_role') in ['asphalt_walk','asphalt_road','asphalt_track','rail']])
solid=bvh(list(C.objects))
joins=json.loads((read_path(D/'join_probes.json')).read_text());old=bvh([bpy.data.objects[n] for n in joins['old_objects']])
differences=[];level_transitions=[]
for row in joins['samples']:
    a,_,_,_=ground.ray_cast(Vector((*row['new_xy'],30)),Vector((0,0,-1)),30)
    b,_,_,_=old.ray_cast(Vector((*row['old_xy'],30)),Vector((0,0,-1)),30)
    assert a is not None and b is not None,row
    if row['new_raised']==row['old_raised']:
        differences.append(abs(a.z-b.z))
    else:
        level_transitions.append(dict(**row,new_z_local_m=float(a.z),old_z_local_m=float(b.z),difference_m=float(a.z-b.z)))
assert max(differences)<.025,(max(differences),int(np.argmax(differences)))
walk_samples=0
for guard in P['guards']:
    p=np.array(guard['path']);length=np.linalg.norm(np.diff(p,axis=0),axis=1);st=np.r_[0,np.cumsum(length)]
    n=np.array([-1.,0.])
    # Source bridge across direction; north outer guard is entered southwards.
    frame=json.loads((read_path(R/'derived/bellevue/quaibruecke_connection/build_input.json')).read_text())
    n=np.array(frame['bridge_across'])*(-1 if guard['source'].endswith('.5939') else 1)
    for t in np.arange(1.5,st[-1]-1.5,.5):
        xy=np.array([np.interp(t,st,p[:,i]) for i in range(2)])+n*1.25-O[:2]
        hit,_,_,_=ground.ray_cast(Vector((*xy,30)),Vector((0,0,-1)),30)
        assert hit is not None,('bridge walkway gap',xy.tolist())
        overhead,_,_,_=solid.ray_cast(hit+Vector((0,0,.1)),Vector((0,0,1)),2.02)
        assert overhead is None,('walkway obstacle',xy.tolist())
        walk_samples+=1
blocked=[];oldroute=json.loads((read_path(R/'evidence/G1_026/connection_geometry_checks.json')).read_text())['route_samples']
for row in oldroute:
    p=Vector((*row['xy_local'],row['floor_ln02_m']-400+.08))
    hit,_,_,distance=solid.ray_cast(p,Vector((0,0,1)),2.04)
    if hit is not None:blocked.append(dict(station=row['station_m'],clearance_m=distance+.08))
assert not blocked,blocked
mast_errors=[]
for m in P['masts']:
    ob=bpy.data.objects['BD_MAST_'+m['id'].split('.')[-1]];v=np.array([q.co[:] for q in ob.data.vertices])+O
    error=max(np.linalg.norm((v[:,:2].min(0)+v[:,:2].max(0))/2-m['xy']),abs(v[:,2].min()-m['base_ln02_m']),abs(v[:,2].max()-m['top_ln02_m']))
    assert error<.0001,(m['id'],error);mast_errors.append(float(error))
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
report=dict(version=s['version'],meshes=len(C.objects),actual_raised_plan_m2=areas['asphalt_walk'],actual_road_and_track_m2=road,
    join_probes=len(differences),max_join_difference_m=max(differences),bridge_walkway_probes=walk_samples,
    existing_underpass_probes=len(oldroute),added_underpass_obstructions=blocked,source_masts=12,max_mast_source_error_m=max(mast_errors),
    original_source_nodes=2039,level_transitions=level_transitions,
    unresolved_large_level_transitions=[q for q in level_transitions if abs(q['difference_m'])>.17],
    geometry_globally_accepted=False,all_photo_collisions_checked=False,visual_acceptance=False,natural_use_verified=False)
(write_path(R/'evidence'/s['version']/'deck_checks.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BRIDGE_DECK_CHECKS',json.dumps({k:v for k,v in report.items() if k not in ['level_transitions','unresolved_large_level_transitions']}),
      'UNRESOLVED_LARGE_TRANSITIONS',len(report['unresolved_large_level_transitions']),flush=True)
