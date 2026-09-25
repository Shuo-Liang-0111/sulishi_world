"""Inspect actual024 water solids, source pier positions and support joints."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
from pathlib import Path
import json
import bpy,bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R=WORKSPACE;s=bpy.context.scene
assert s['version'].startswith(('G1_024','G1_025','G1_026','G1_027'))
P=json.loads((read_path(R/'derived/bellevue/quaibruecke_water/build_input.json')).read_text(encoding='utf-8'))
C=bpy.data.collections['39_BRIDGE_WATER_CONTEXT'];assert len(C.objects)==802
invalid=[]
for ob in C.objects:
    assert ob.type=='MESH' and ob.get('source_id'),ob.name
    assert np.isfinite(np.array([v.co[:] for v in ob.data.vertices])).all(),ob.name
    invalid.extend([ob.name,p.index] for p in ob.data.polygons if p.area<1e-11)
assert not invalid,invalid[:12]

water=bpy.data.objects['QB_WATER_CONTINUOUS'];bm=bmesh.new();bm.from_mesh(water.data)
boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold for e in bm.edges)
volume=bm.calc_volume(signed=True);bm.free()
assert boundary==nonmanifold==0 and volume>1_000_000
v=np.array([water.matrix_world@q.co for q in water.data.vertices]);area=0.
for face in water.data.polygons:
    if face.normal.z<.9:continue
    pts=v[list(face.vertices)]
    area+=sum(abs(np.cross(pts[i,:2]-pts[0,:2],pts[i+1,:2]-pts[0,:2]))/2 for i in range(1,len(pts)-1))
assert abs(area-P['report']['water_surface_plan_m2'])<.02,(area,P['report']['water_surface_plan_m2'])
top=v[v[:,2]>0,2]+400
assert top.min()>=405.9899 and top.max()<=406.0101

piers=[];O=np.array(P['origin'])
for entry in P['piers']:
    ident=entry['id'];ob=bpy.data.objects['QB_PIER_'+ident.split('.')[-1]]
    actual=np.array([ob.matrix_world@q.co for q in ob.data.vertices])[:,:2]+O[:2]
    expected=np.array(entry['geometry']['coordinates'][0])[:,:2]
    error=max(float(np.min(np.linalg.norm(actual-p,axis=1))) for p in expected)
    assert error<.0002,(ident,error)
    piers.append(dict(id=ident,max_source_vertex_error_m=error))

seams=[]
for k in range(4):
    for part in ['WEB','TOP_FLANGE','LOWER_FLANGE']:
        old=bpy.data.objects[f'QB_GIRDER_{k}_{part}'];new=bpy.data.objects[f'QB_CONTINUOUS_GIRDER_{k}_{part}']
        a=np.array([v.co[:] for v in old.data.vertices]);b=np.array([v.co[:] for v in new.data.vertices])
        # The first ring is the exact saved east-span endpoint; compare actual
        #vertices rather than the generation parameters.
        delta=max(float(np.min(np.linalg.norm(a-q,axis=1))) for q in b[:4])
        assert delta<.0001,(k,part,delta);seams.append(delta)

bearings=[]
for j in range(4):
    for k in range(4):
        solids=[bpy.data.objects[f'QB_BEARING_{j}_{k}_{part}'] for part in ['PLINTH','PAD','PLATE']]
        ranges=[(min(v.co.z for v in ob.data.vertices),max(v.co.z for v in ob.data.vertices)) for ob in solids]
        gaps=[ranges[i+1][0]-ranges[i][1] for i in range(2)]
        assert max(abs(g) for g in gaps)<.00001
        bearings.append(dict(pier_index=j,girder=k,interface_gap_m=gaps))

water_bvh=BVHTree.FromPolygons([Vector(q) for q in v],[list(f.vertices) for f in water.data.polygons],all_triangles=False)
route=json.loads((read_path(R/'evidence'/s['version']/'connection_geometry_checks.json')).read_text(encoding='utf-8'))['route_samples']
flooded=[]
for p in route:
    xy=p['xy_local'];floor=p['floor_ln02_m']-400
    hit,_,_,_=water_bvh.ray_cast(Vector((*xy,15)),Vector((0,0,-1)),30)
    if hit is not None and hit.z>floor+.015:flooded.append(p['station_m'])
assert not flooded,('Water intersects public passage',flooded[:10])
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not Path(bpy.path.abspath(i.filepath,library=i.library)).is_file()]
assert not missing,missing
record=dict(version=s['version'],objects=len(C.objects),water_vertices=len(water.data.vertices),water_faces=len(water.data.polygons),
    water_boundary_edges=boundary,water_nonmanifold_edges=nonmanifold,water_volume_m3=volume,water_plan_area_m2=area,
    water_plan_area_error_m2=area-P['report']['water_surface_plan_m2'],water_height_range_ln02_m=[float(top.min()),float(top.max())],
    source_piers=piers,girder_endpoint_max_delta_m=max(seams),bearing_interfaces=bearings,
    public_passage_water_intersections=flooded,source_photo_objects_retained=2039,missing_images=missing,
    geometry_checks_passed=True,visual_acceptance=False,natural_use_verified=False,
    water_depth_and_steel_fabrication_inferred=True,g1_walking_scope_expanded=False)
(write_path(R/'evidence'/s['version']/'water_structure_checks.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
print('BRIDGE_WATER_CHECKS',json.dumps({k:v for k,v in record.items() if k!='bearing_interfaces'}),flush=True)
