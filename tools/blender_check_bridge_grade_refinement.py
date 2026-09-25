"""Independent surface rays across tile boundaries and through painted lines."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
from pathlib import Path
from collections import Counter
import hashlib,json,sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R=WORKSPACE;D=R/'derived/bellevue/bridge_grade'
s=bpy.context.scene;assert s['version'] in ['G1_027r1','G1_027r2','G1_027r3']
prospective=s['version']=='G1_027r1'
meta=json.loads((read_path(D/'027r2_refined_objects.json')).read_text());report=json.loads((read_path(D/'027r2_refinement.json')).read_text())
for name,digest in report['inputs'].items():assert hashlib.sha256((read_path(D/name)).read_bytes()).hexdigest()==digest,name
assert not report['unresolved']
assert hashlib.sha256((read_path(D/'027r2_refined_patch.npz')).read_bytes()).hexdigest()==report['payload_sha256']
patch=np.load(read_path(D/'027r2_refined_patch.npz'));ref=np.load(read_path(D/'027r2_refined_reference.npz'))
byname={r['name']:r for r in meta['objects']}
if not prospective:
    sys.path.insert(0,str(R/'tools'))
    from blender_geometry_fingerprint import mesh_digest
    built=json.loads((read_path(R/'evidence/G1_027r2/construction.json')).read_text())
    for row in built['after_fingerprints']:
        assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['name']].data)))==row['mesh_fingerprint'],row['name']

def actual_geometry(ob):
    ob.data.calc_loop_triangles()
    return np.array([ob.matrix_world@v.co for v in ob.data.vertices]),np.array([t.vertices[:] for t in ob.data.loop_triangles])

def geometry(ob):
    if prospective and ob.name in byname:
        key=byname[ob.name]['key'];return patch[key].astype(float),ref[key+'_faces']
    return actual_geometry(ob)

def near(v):return v[:,0].min()<-254 and v[:,0].max()>-297 and v[:,1].min()<155 and v[:,1].max()>110

surfaces=[];verts=[];faces=[];owners=[];boundaries=[]
roles={'asphalt_walk','asphalt_road','asphalt_track','road_asphalt','road_concrete','road_joint'}
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
    if ob.type!='MESH' or ob.hide_render or not (ob.get('surface_role') in roles or ob.name.startswith('UB_GROUND_')):continue
    corners=np.array([ob.matrix_world@Vector(v) for v in ob.bound_box])
    if not near(corners):continue
    v,f=geometry(ob);t=v[f];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
    upper=(n[:,2]>.85*np.linalg.norm(n,axis=1))&(n[:,2]>1e-7)
    start=len(verts);verts.extend(Vector(p) for p in v);faces.extend((f+start).tolist())
    kind='walk' if ob.get('surface_role')=='asphalt_walk' or ob.name.startswith('UB_GROUND_') else 'road'
    owners.extend([(ob.name,kind)]*len(f));surfaces.append(ob.name)
    edge_count=Counter(tuple(sorted((int(a),int(b)))) for tri in f[upper] for a,b in zip(tri,np.roll(tri,-1)))
    for (a,b),count in edge_count.items():
        if count!=1:continue
        p,q=v[a,:2],v[b,:2];length=np.linalg.norm(q-p)
        if length<.02:continue
        mid=(p+q)/2
        if not (-297<mid[0]<-254 and 110<mid[1]<155):continue
        norm=np.array([-(q-p)[1],(q-p)[0]])/length
        boundaries.append((mid,norm,ob.name))
tree=BVHTree.FromPolygons(verts,faces,all_triangles=True)
def ray(xy):
    point,normal,index,_=tree.ray_cast(Vector((*xy,25)),Vector((0,0,-1)),25)
    return None if point is None else (float(point.z),owners[index],list(normal))

seams=[]
for mid,norm,name in boundaries:
    a=ray(mid-norm*.015);b=ray(mid+norm*.015)
    if a is None or b is None or a[1][0]==b[1][0] or a[1][1]!=b[1][1]:continue
    seams.append(dict(xy=mid.tolist(),a=a[1][0],b=b[1][0],difference_m=abs(a[0]-b[0])))
paint=[]
for row in meta['objects']:
    if row['role'] not in ['paint','crossing_paint']:continue
    ob=bpy.data.objects[row['name']];v,f=geometry(ob);t=v[f]
    normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);centres=t.mean(1)
    good=(normal[:,2]>.85*np.linalg.norm(normal,axis=1))&(normal[:,2]>1e-7)
    for face in np.flatnonzero(good):
        p=centres[face]
        if not (-297<p[0]<-254 and 110<p[1]<155):continue
        hit=ray(p[:2])
        if hit is not None:paint.append(dict(object=ob.name,face=int(face),xy=p[:2].tolist(),clearance_m=float(p[2]-hit[0]),surface=hit[1][0]))
assert seams and paint
result=dict(version=s['version'],surface_geometry_version='G1_027r2',prospective=prospective,surface_objects=len(surfaces),
    payload_sha256=report['payload_sha256'],
    same_kind_seam_probes=len(seams),seam_quantiles_m=np.quantile([q['difference_m'] for q in seams],[.5,.95,.99,1]).tolist(),
    seam_worst=sorted(seams,key=lambda x:x['difference_m'],reverse=True)[:16],
    painted_face_probes=len(paint),paint_clearance_quantiles_m=np.quantile([q['clearance_m'] for q in paint],[0,.01,.5,.99,1]).tolist(),
    buried_paint=[q for q in paint if q['clearance_m']<0],floating_paint=[q for q in paint if q['clearance_m']>.012],
    camera_or_lighting_changed=False,visual_acceptance=False,natural_use_verified=False)
path=D/('027r2_prospective_checks.json' if prospective else s['version'].removeprefix('G1_')+'_actual_checks.json')
write_path(path).write_text(json.dumps(result,indent=2),encoding='utf-8')
print('REFINEMENT_RAYS',json.dumps({k:v for k,v in result.items() if k not in ['seam_worst','buried_paint','floating_paint']}),flush=True)
if not globals().get('DIAGNOSTIC_ONLY',False):
    assert result['seam_quantiles_m'][-1]<.025,result['seam_worst'][:3]
    assert not result['buried_paint'],result['buried_paint'][:3]
    assert not result['floating_paint'],result['floating_paint'][:3]
