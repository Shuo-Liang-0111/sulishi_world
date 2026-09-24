"""Check actual G1_025 paving, tree support, rail bases and prior passage."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version'].startswith(('G1_025','G1_026','G1_027'))
P=json.loads((R/'derived/bellevue/bridgehead_bank/build_input.json').read_text(encoding='utf-8'))
C=bpy.data.collections['40_BRIDGEHEAD_BANK'];trees=bpy.data.collections['41_BRIDGEHEAD_TREES']
assert C['geometry_complete'] and len(trees.objects)==36
invalid=[];areas={'paving':0.,'soil':0.};slopes=[]
for ob in C.objects:
    assert ob.type=='MESH' and ob.get('source_id')
    vertices=np.array([v.co[:] for v in ob.data.vertices]);assert np.isfinite(vertices).all()
    for f in ob.data.polygons:
        if f.area<1e-11:invalid.append([ob.name,f.index])
        if ob.get('surface_role') in areas and f.normal.z>.7:
            q=vertices[list(f.vertices)];areas[ob['surface_role']]+=sum(abs(np.cross(q[i,:2]-q[0,:2],q[i+1,:2]-q[0,:2]))/2 for i in range(1,len(q)-1))
        if ob.get('surface_role')=='paving' and f.normal.z>0 and f.area>.01:
            slopes.append((float(np.linalg.norm(f.normal[:2])/f.normal.z),ob.name,f.index))
assert not invalid,invalid[:10]
assert abs(areas['paving']-P['report']['paving_m2'])<.025,areas
assert abs(areas['soil']-P['report']['soil_m2'])<.003,areas

def bvh(objects):
    verts=[];faces=[]
    for ob in objects:
        offset=len(verts);verts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
        faces.extend([offset+i for i in f.vertices] for f in ob.data.polygons)
    return BVHTree.FromPolygons(verts,faces,all_triangles=False)
soil=bvh([o for o in C.objects if o.get('surface_role')=='soil'])
tree_report=[]
for entry in P['trees']:
    ident=entry['source']['properties']['objectid'];root=np.array([*entry['source']['geometry']['coordinates'],entry['ground_ln02_m']])-np.array(P['origin'])
    top=-1e9;bottom=1e9
    for role in ['WOOD','TWIGS','LEAVES']:
        ob=bpy.data.objects[f'UB_TREE_{ident}_{role}'];assert ob['source_id']==entry['source']['id']
        raw=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',raw);v=raw.reshape(-1,3)
        assert np.isfinite(v).all();top=max(top,float(v[:,2].max()));bottom=min(bottom,float(v[:,2].min()))
        if role=='WOOD':center=v[:80,:2].mean(0)
    height=top-root[2];xyerror=float(np.linalg.norm(center-root[:2]))
    assert abs(height-entry['height_m'])<.0001,(ident,height)
    assert xyerror<.08,(ident,xyerror)
    hit,_,_,_=soil.ray_cast(Vector((*root[:2],root[2]+1)),Vector((0,0,-1)),2)
    assert hit is not None and abs(hit.z-root[2])<.001 and bottom<hit.z-.04,(ident,'unsupported tree')
    tree_report.append(dict(id=ident,height_m=height,root_collar_center_offset_m=xyerror,soil_height_local=hit.z,buried_root_m=hit.z-bottom))

cap=bvh([o for o in C.objects if o.name.startswith('UB_WALL_COPING')])
supports=[]
for ob in C.objects:
    if '_FOOT_' not in ob.name:continue
    v=np.array([ob.matrix_world@q.co for q in ob.data.vertices]);bottom=float(v[:,2].min());corners=v[v[:,2]<bottom+.00001]
    for q in corners:
        hit,_,_,_=cap.ray_cast(Vector(q+[0,0,.30]),Vector((0,0,-1)),.60)
        assert hit is not None and -.012<hit.z-bottom<.10,(ob.name,'base corner lacks coping support',q.tolist())
        supports.append(float(hit.z-bottom))

allnew=bvh(C.objects)
route=json.loads((R/'evidence'/s['version']/'connection_geometry_checks.json').read_text(encoding='utf-8'))['route_samples']
blocked=[]
for q in route:
    p=Vector((*q['xy_local'],q['floor_ln02_m']-400+.08))
    hit,_,_,distance=allnew.ray_cast(p,Vector((0,0,1)),2.02)
    if hit is not None:blocked.append(dict(station=q['station_m'],height_above_floor=distance+.08))
assert not blocked,blocked[:12]
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
missing=[i.name for i in bpy.data.images if i.source=='FILE' and i.filepath and not i.packed_file and not Path(bpy.path.abspath(i.filepath,library=i.library)).is_file()]
assert not missing,missing
report=dict(version=s['version'],ground_and_rail_objects=len(C.objects),tree_objects=len(trees.objects),
    actual_area_m2=areas,trees=tree_report,rail_base_corners_supported=len(supports),
    steepest_paving_faces=sorted(slopes,reverse=True)[:10],slope_is_not_accessibility_certification=True,
    rail_base_embed_range_m=[min(supports),max(supports)],old_route_probes=len(route),new_geometry_headroom_obstructions=blocked,
    source_photos_retained=2039,missing_images=missing,geometry_checks_passed=True,
    visual_acceptance=False,natural_use_verified=False,runtime_exported=False)
(R/'evidence'/s['version']/'upper_bank_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('UPPER_BANK_CHECKS',json.dumps({k:v for k,v in report.items() if k!='trees'}),flush=True)
