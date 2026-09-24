"""Inspect actual low deck coverage, steel rises, joins and bench bearing."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version'].startswith(('G1_022','G1_023','G1_024','G1_025','G1_026'))
P=json.loads((R/'derived/bellevue/riviera_lower/build_input.json').read_text())
C=bpy.data.collections['36_RIVIERA_LOWER_APPROACH'];O=np.array(P['origin'])
assert C['construction_complete']
missing=[];area=0
for ob in C.objects:
    assert ob.type=='MESH' and ob.get('source_id')
    points=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);assert np.isfinite(points).all()
    if ob.get('surface_role')=='paving':
        for face in ob.data.polygons:
            if face.normal.z<.5:continue
            q=points[list(face.vertices)]
            for j in range(1,len(q)-1):area+=abs(np.cross(q[j]-q[0],q[j+1]-q[0])[2])/2
    for slot in ob.material_slots:
        mat=slot.material
        if not mat or not mat.use_nodes:continue
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image and not node.image.packed_file:
                if not Path(bpy.path.abspath(node.image.filepath,library=node.image.library)).is_file():missing.append(node.image.name)
assert abs(area-P['report']['ground_m2'])<.003,(area,P['report']['ground_m2'])
assert not missing

def ray(ob,xy):
    inv=ob.matrix_world.inverted();hit,q,_,_=ob.ray_cast(inv@Vector((*xy,30)),inv.to_3x3()@Vector((0,0,-1)))
    return (ob.matrix_world@q).z if hit else None
floors=[o for o in C.objects if o.get('surface_role')=='paving']
def floor_at(xy):
    heights=[ray(o,xy) for o in floors];heights=[z for z in heights if z is not None]
    assert heights,('Missing deck',xy)
    return max(heights)

tread_heights=[]
for i in range(13):
    ob=bpy.data.objects[f'RL_TREAD_{i:02}_nose']
    xy=np.mean([(ob.matrix_world@v.co)[:2] for v in ob.data.vertices],axis=0)
    z=ray(ob,xy);assert z is not None
    tread_heights.append(z+400)
risers=np.diff(tread_heights)
assert .145<risers.min()<risers.max()<.185
assert max(abs(risers-P['stair_rise_m']))<.0001
landing=bpy.data.objects['RL_STEEL_TOP_LANDING']
landing_xy=np.array([2683497.86,1246860.0])-O[:2]
top=ray(landing,landing_xy);assert top is not None
assert .14<top+400-tread_heights[-1]<.19

# Independent edge probes compare the reconstructed spur with the old pavement.
start=np.array([2683500.174,1246895.608]);end=np.array([2683501.248,1246892.65])
normal=np.array([end[1]-start[1],start[0]-end[0]]);normal/=np.linalg.norm(normal)
joins=[]
old=bpy.data.objects['LM_ASPHALT']
for t in np.linspace(.25,.9,9):
    q=start*(1-t)+end*t-O[:2]
    za=ray(old,q-normal*.025);zb=None
    if za is None:
        za=ray(old,q+normal*.025);q=q-normal*.025
    else:q=q+normal*.025
    values=[ray(ob,q) for ob in floors];values=[z for z in values if z is not None]
    if za is not None and values:joins.append(abs(max(values)-za))
assert len(joins)>=5,len(joins)
assert max(joins)<.025,joins

bearings=[]
for i in range(len(P['benches'])-1):
    for j in range(6):
        ob=bpy.data.objects[f'RL_BANK_SEAT_{i:02}_{j}']
        # Each solid slat must physically enter/support against both adjacent
        # concrete piers; ray projections alone would miss a horizontal gap.
        v=np.array([(ob.matrix_world@q.co)[:] for q in ob.data.vertices])
        hits=[]
        for k in [i,i+1]:
            pier=bpy.data.objects[f'RL_BANK_PIER_{k:02}'];inv=pier.matrix_world.inverted()
            xy=np.mean(v[:4,:2],axis=0) if k==i else np.mean(v[4:,:2],axis=0)
            hit,z,_,_=pier.ray_cast(inv@Vector((*xy,30)),inv.to_3x3()@Vector((0,0,-1)))
            hits.append(hit)
        assert all(hits),('Slat misses pier',ob.name,hits)
        bearings.append(ob.name)
    rec=P['benches'][i];xy=np.array(rec['edge_xy'])+np.array(rec['inward'])*.36-O[:2]
    assert abs(floor_at(xy)-(rec['z_ln02_m']-400))<.004
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
result={'version':s['version'],'objects_in_batch':len(C.objects),'measured_deck_area_m2':area,
        'deck_area_error_m2':area-P['report']['ground_m2'],'steel_tread_heights_ln02_m':tread_heights,
        'min_measured_rise_m':float(risers.min()),'max_measured_rise_m':float(risers.max()),
        'upper_spur_join_samples':len(joins),'maximum_upper_spur_join_delta_m':max(joins),
        'seat_slats_with_two_pier_bearings':len(bearings),'missing_images':[],
        'geometry_checks_passed':True,'bridge_underpass_complete':False,
        'actual_walking_collision_verified':False,'visual_acceptance':False}
(R/'evidence'/s['version']/'lower_geometry_checks.json').write_text(json.dumps(result,indent=2))
print('LOWER_APPROACH_CHECKS',json.dumps(result),flush=True)
