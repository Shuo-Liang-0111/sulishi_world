"""Inspect actual source coverage, shared walking seam and physical stair rises."""
from pathlib import Path
import json
import numpy as np
import bpy
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/riviera_quay';s=bpy.context.scene
assert str(s['version']).startswith(('G1_021','G1_022','G1_023','G1_024','G1_025'))
p=json.loads((D/'build_input.json').read_text());C=bpy.data.collections['33_RIVIERA_QUAY']
O=np.array(p['origin']);A=np.array(p['anchor']);T=np.array(p['along']);N=np.array(p['across'])
assert len(C.objects)==len(p['parts'])
areas={};missing=[]
for ob in C.objects:
    assert ob.type=='MESH' and ob.get('source_id')
    v=np.array([(ob.matrix_world@a.co)[:] for a in ob.data.vertices]);assert np.isfinite(v).all()
    top_area=0.
    for face in ob.data.polygons:
        if face.normal.z<.5:continue
        q=v[list(face.vertices)]
        for i in range(1,len(q)-1):top_area+=abs(np.cross(q[i]-q[0],q[i+1]-q[0])[2])/2
    assert abs(top_area-ob['source_plan_area_m2'])<.007,(ob.name,top_area,ob['source_plan_area_m2'])
    areas[ob.name]=top_area
    for slot in ob.material_slots:
        m=slot.material
        if not m or not m.use_nodes:continue
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image and not n.image.packed_file:
                path=Path(bpy.path.abspath(n.image.filepath,library=n.image.library))
                if not path.is_file():missing.append(str(path))
assert not missing,missing

def ray(ob,worldxy):
    inv=ob.matrix_world.inverted();o=inv@Vector((*worldxy,30));d=(inv.to_3x3()@Vector((0,0,-1))).normalized()
    hit,q,_,_=ob.ray_cast(o,d)
    return (ob.matrix_world@q).z if hit else None
def walk_height(sd):
    q=A+T*sd[0]+N*sd[1]-O[:2]
    h=[ray(o,q) for o in C.objects if o.get('surface_role') in ['asphalt','stair']]
    h=[z for z in h if z is not None]
    return max(h) if h else None
join=[]
for sta in np.arange(3,77,1.25):
    before=A+T*sta-N*.025-O[:2]
    z0=ray(bpy.data.objects['LM_ASPHALT'],before);z1=walk_height((sta,.025))
    if z0 is not None and z1 is not None:join.append({'station_m':float(sta),'delta_m':float(z1-z0)})
assert len(join)>45,len(join)
assert max(abs(x['delta_m']) for x in join)<.012,sorted(join,key=lambda x:abs(x['delta_m']),reverse=True)[:3]

rises=[]
for sta in [19.5,40,58,79]:
    h=[]
    for cross in np.arange(7.56,10.55,.299):
        z=walk_height((sta,cross))
        if z is not None:h.append(z)
    diffs=-np.diff(h)
    assert len(h)>=9,(sta,h)
    assert diffs.min()>.12 and diffs.max()<.21,(sta,h)
    rises.append({'station_m':sta,'samples':len(h),'min_rise_m':float(diffs.min()),'max_rise_m':float(diffs.max())})
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
rec={'version':s['version'],'source_pavement_m2':p['report']['footprint_m2'],'authored_objects':len(C.objects),
     'sum_top_projected_area_including_wall_surfaces_m2':sum(areas.values()),'source_scope_note':'Overlapping official wall/step/pavement footprints are distinct records, not additive land area.',
     'join_samples':join,'max_shared_seam_delta_m':max(abs(x['delta_m']) for x in join),'sampled_stair_rises':rises,
     'missing_images':missing,'original_photo_nodes':2039,'geometry_checks_passed':True,'visual_acceptance':False,'actual_walk_use_verified':False}
out=R/'evidence'/s['version'];out.mkdir(exist_ok=True)
(out/'quay_geometry_check.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in rec.items() if k not in ['join_samples']}),flush=True)
