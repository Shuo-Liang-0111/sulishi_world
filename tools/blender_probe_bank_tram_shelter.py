"""Read current retained shelter geometry and all local support-ray layers.

No native mutations. GroundSurface in the official LOD model is the roof
underside, so walking levels must be diagnosed from other actual geometry.
"""
from pathlib import Path
import hashlib,json,os,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

s=bpy.context.scene;assert s['version'] in ['G1_027r10','G1_027r12']
native=Path(bpy.data.filepath)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
cp=json.loads(read_path(f'evidence/{s["version"]}/checkpoint.json').read_text());assert digest==cp['native_sha256']
specpath=read_path('derived/bellevue/bank_tram_shelter/build_input.json')
d=json.loads(specpath.read_text())
full_platform=bool(globals().get('FULL_PLATFORM',False))
ring=np.array(d['roof_plan_local']['coordinates'][0]);lo=ring.min(0)-2.;hi=ring.max(0)+2.
if full_platform:
    # The two AV end noses are continuous with the platform, not road. Include
    # both them and the real adjacent road/rail meshes in this separate probe.
    av=json.loads(read_path('sources/features/av_bo_boflaeche_a.geojson').read_text())
    selected=[f for f in av['features'] if f['id'] in {'av_bo_boflaeche_a.355','av_bo_boflaeche_a.456','av_bo_boflaeche_a.457'}]
    coords=np.concatenate([np.asarray(f['geometry']['coordinates'][0])[:,:2]-np.asarray(d['origin_lv95_ln02'][:2]) for f in selected])
    lo=coords.min(0)-3.;hi=coords.max(0)+3.
def intersects(ob):
    if not len(ob.data.polygons):return False
    v=np.array([ob.matrix_world@Vector(x) for x in ob.bound_box])
    return ((v[:,:2].max(0)>=lo)&(v[:,:2].min(0)<=hi)).all() and v[:,2].max()>7 and v[:,2].min()<15
context=[o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects if o.type=='MESH' and intersects(o)]
surface_tags=['PAVING','SURVEY_TERRAIN','STREET_APPROACH']
if full_platform:surface_tags+=['BE_ROAD_','BE_CROSSING_','CURB','PLATFORM']
surface_roles={'road_asphalt','road_concrete','road_joint','rail_steel','groove_floor','groove_wall',
               'crossing_paint','asphalt_road','asphalt_track','asphalt_walk','rail','drain','curb','paint'}
pavements=[o for o in s.objects if o.type=='MESH' and not o.name.startswith(('CTX_','I3S_'))
           and (any(t in o.name for t in surface_tags) or
                (full_platform and o.get('surface_role') in surface_roles)) and intersects(o)]
assert context
rows=[];trees=[]
for ob in context+pavements:
    xyz=np.empty(len(ob.data.vertices)*3,dtype=np.float32);ob.data.vertices.foreach_get('co',xyz)
    matrix=np.array(ob.matrix_world);world=xyz.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
    faces=[list(p.vertices) for p in ob.data.polygons]
    indices=np.empty(len(ob.data.loops),dtype=np.int32);ob.data.loops.foreach_get('vertex_index',indices)
    uv=np.empty(0,dtype=np.float32)
    if ob.data.uv_layers.active:
        uv=np.empty(len(ob.data.loops)*2,dtype=np.float32);ob.data.uv_layers.active.data.foreach_get('uv',uv)
    tree=BVHTree.FromPolygons([Vector(x) for x in world],faces,all_triangles=False)
    trees.append((ob.name,tree))
    rows.append(dict(name=ob.name,kind='retained_photo' if ob in context else 'authored_or_survey_pavement',
                     matrix_world=matrix.tolist(),vertices_world=world.tolist(),faces=faces,
                     vertex_loop_uv_sha256=hashlib.sha256(xyz.tobytes()+indices.tobytes()+uv.tobytes()).hexdigest(),
                     mesh_digest=mesh_digest(ob.data),
                     materials=[m.name if m else None for m in ob.data.materials],source_id=ob.get('source_id'),
                     surface_role=ob.get('surface_role'),
                     modifiers=[dict(name=m.name,type=m.type) for m in ob.modifiers]))
start=np.array(d['axis_start_local_xy']);end=np.array(d['axis_end_local_xy'])
side=np.array(d['side_unit_xy']);points=[]
for t in np.linspace(0,1,13):
    radius=d['rounded_end_fits'][0]['fitted_radius_m']*(1-t)+d['rounded_end_fits'][1]['fitted_radius_m']*t
    for fraction in [-.85,-.4,0,.4,.85]:
        points.append(dict(label=f'roof_under_{t:.3f}_{fraction}',xy=(start+(end-start)*t+side*radius*fraction).tolist()))
for j,xy in enumerate(d['inferred_support_centres_local_xy']):points.append(dict(label=f'column_{j}',xy=xy))
bank=json.loads(read_path('derived/ubs_theaterstrasse20/build_input.json').read_text())
A,U,N=(np.array(bank[k]) for k in ['A','U','N'])
for row in d['nearby_facilities']:
    points.append(dict(label=row['id'],xy=(A+U*row['u']+N*row['v']).tolist()))
if full_platform:
    prepared=json.loads(read_path('derived/bellevue/bank_tram_shelter/platform_input.json').read_text())
    for i,row in enumerate(prepared['report']['perimeter_road_comparison']):
        points.append(dict(label=f'full_platform_edge_{i}',xy=row['xy']))
rays=[]
for sample in points:
    hits=[]
    for name,tree in trees:
        z=16.
        for iteration in range(24):
            hit,n,face,distance=tree.ray_cast(Vector((*sample['xy'],z)),Vector((0,0,-1)),z-6.8)
            if hit is None:break
            hits.append(dict(object=name,z=float(hit.z),normal=list(n),face=int(face)))
            z=float(hit.z)-.003
            if z<=6.8:break
    hits.sort(key=lambda x:-x['z']);rays.append(dict(**sample,hits=hits))
out=dict(version=s['version'],native=str(native),native_sha256=digest,process_id=os.getpid(),
         probe_scope='full_platform_end_noses_and_roads' if full_platform else 'roof_near_context',
         spec_sha256=hashlib.sha256(specpath.read_bytes()).hexdigest(),objects=rows,rays=rays,
         limits=['Raw evaluated transforms and base meshes only; modifiers are listed and must be evaluated if any affect the selected ground.',
                 'All vertical hits are retained. No topmost surface is automatically accepted as pedestrian ground.',
                 'No scene geometry, camera, source block or native file changed.'],native_changed=False)
suffix='_platform_full' if full_platform else ''
p=write_path(f'derived/bellevue/bank_tram_shelter/native_probe_{s["version"]}{suffix}.json')
p.write_text(json.dumps(out,indent=2),encoding='utf-8')
print('BANK_SHELTER_PROBE',json.dumps(dict(file=str(p),objects=len(rows),rays=len(rays))),flush=True)
