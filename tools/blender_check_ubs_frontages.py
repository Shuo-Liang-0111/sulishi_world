"""Fresh saved geometry: real apertures, ground joins and preserved site identity.

Independent rays inspect meshes, rather than trusting the authoring manifest.
Support and headroom are distinct. No public interior/walking acceptance here.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path

s=bpy.context.scene;version=s['version'];assert version in ['G1_027r9','G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14']
native=Path(bpy.data.filepath)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
cp=json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text());assert cp['native_sha256']==digest
d=json.loads(read_path('derived/ubs_theaterstrasse20/build_input.json').read_text())
r=json.loads(read_path(f'evidence/{version}/ubs_build_report.json').read_text())
C=bpy.data.collections['46_UBS_THEATERSTRASSE20']
assert set(r['created_objects'])=={o.name for o in C.objects}
assert all(o.type=='MESH' and len(o.data.polygons)>0 for o in C.objects)
assert C['public_interior_selected']==False
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
for name,count in r['final_photo_counts'].items():assert len(bpy.data.objects[name].data.polygons)==count,name
A,U,N=(np.array(d[k]) for k in ['A','U','N']);SU,SN=(np.array(d[k]) for k in ['side_U','side_N'])
def P(u,v,z):return Vector((*list(A+U*u+N*v),z))
def S(u,v,z):return Vector((*list(A+SU*u+SN*v),z))
ground=bpy.data.objects['UF_CONTINUOUS_STREET_APPROACH']
tree=BVHTree.FromPolygons([ground.matrix_world@v.co for v in ground.data.vertices],[list(p.vertices) for p in ground.data.polygons])
ground_samples=[]
for u in np.linspace(.2,d['street_width_m']-.2,24):
    for v in [.10,.40,1.2,2.3,3.4,4.2]:
        p,n,face,dist=tree.ray_cast(P(u,v,9.5),Vector((0,0,-1)),2)
        assert p is not None and n.z>.99,(u,v)
        ground_samples.append(dict(u=float(u),v=v,z=p.z))
joins=[]
for row in d['pavement']['cafe_edge_anchors']:
    p,n,face,dist=tree.ray_cast(P(row['u']+.001,row['v']+(.0001 if row['v']==0 else -.0001 if row['v']==4.4 else 0),9.5),Vector((0,0,-1)),2)
    assert p is not None and abs(p.z-row['z'])<.0004,(row,p)
    joins.append(dict(v=row['v'],height_error_m=abs(p.z-row['z'])))
outer=[]
for row in d['pavement']['outer_anchors'][8:-2]:
    p,n,face,dist=tree.ray_cast(P(row['u'],row['v']-.0001,9.5),Vector((0,0,-1)),2)
    assert p is not None and abs(p.z-row['z'])<.001,(row,p)
    outer.append(abs(p.z-row['z']))

bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
apertures=[]
for row in r['openings']:
    if row['frame']=='front':frame,outward=P,N
    else:frame,outward=S,SN
    # Off the mullions, sill and transom: the first surface must be real glazing.
    u=row['a']+.5*(row['b']-row['a'])/row['panes'];z=row['z0']+(row['z1']-row['z0'])*.65
    start=frame(u,row['depth']+.14,z)
    hit,p,n,fi,ob,m=s.ray_cast(deps,start,Vector((*list(-outward),0)),distance=.4)
    assert hit and ob.name.startswith(row['name']+'_GLASS'),(row['name'],ob.name if hit else None)
    mat=ob.material_slots[0].material;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    assert bs.inputs['Transmission Weight'].default_value==1
    apertures.append(dict(name=row['name'],first_hit=ob.name))
headroom=[]
for row in ground_samples:
    start=P(row['u'],row['v'],row['z']+.015)
    hit,p,n,fi,ob,m=s.ray_cast(deps,start,Vector((0,0,1)),distance=1.90)
    headroom.append(dict(u=row['u'],v=row['v'],clear=not hit,obstruction=ob.name if hit else None))
cameras=[]
for row in r['cameras']:
    cam=bpy.data.objects[row['name']]
    hit,p,n,fi,ob,m=s.ray_cast(deps,Vector((cam.location.x,cam.location.y,9.5)),Vector((0,0,-1)),distance=3)
    assert hit and abs(cam.location.z-p.z-1.7)<.0001,(cam.name,ob.name if hit else None)
    cameras.append(dict(name=cam.name,ground=ob.name,eye_height_m=cam.location.z-p.z))
report=dict(version=version,native=str(native),native_sha256=digest,process_id=os.getpid(),checked_utc=datetime.now(timezone.utc).isoformat(),
    created_meshes=len(C.objects),transparent_apertures=apertures,ground_support=ground_samples,cafe_edge_joins=joins,
    outer_edge_max_error_m=max(outer),headroom=headroom,clear_headroom_samples=sum(x['clear'] for x in headroom),
    cameras=cameras,public_interior_accepted=False,runtime_collision_verified=False,natural_use_verified=False)
write_path(f'evidence/{version}/ubs_fresh_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('UBS_FRONTAGES_CHECKED',json.dumps(dict(apertures=len(apertures),ground_samples=len(ground_samples),cafe_edge_joins=len(joins),clear_headroom=report['clear_headroom_samples'])),flush=True)
