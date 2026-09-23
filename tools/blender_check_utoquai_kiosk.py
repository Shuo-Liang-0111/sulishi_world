"""Read the authored kiosk geometry; these checks do not accept runtime use."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version'].startswith(('G1_020','G1_021','G1_022','G1_023'))
plan=json.loads((ROOT/'derived/bellevue/utoquai_kiosk/build_input.json').read_text())
collection=bpy.data.collections['32_UTOQUAI_RIVIERA_KIOSK']
floor=plan['floor_local_inferred'];roof=plan['roof_local'];origin=np.array(plan['source']['origin'])
ring=np.array(plan['source']['footprint_ccw_lv95']['coordinates'][0])[:-1]-origin[:2]

def world_vertices(ob):
    return np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices])

def ground_level(xy):
    levels=[]
    for key in ['LM_ASPHALT','LM_CURB_TOP','LM_SOIL']:
        hit,p,_,_=bpy.data.objects[key].ray_cast(Vector((*xy,30)),Vector((0,0,-1)))
        if hit:levels.append(p.z)
    return max(levels) if levels else None

ro=world_vertices(bpy.data.objects['UR_ROOF'])
fo=world_vertices(bpy.data.objects['UR_FLOOR'])
assert abs(ro[:,2].max()-roof)<.00001
assert abs(fo[:,2].max()-floor)<.00001
roof_top=ro[ro[:,2]>roof-.0001]
assert max(min(np.linalg.norm(q[:2]-p,axis=0) for p in ring) for q in roof_top)<.00005
area=abs(np.dot(roof_top[:,0],np.roll(roof_top[:,1],-1))-np.dot(roof_top[:,1],np.roll(roof_top[:,0],-1)))/2
assert abs(area-plan['source']['area_m2'])<.0001
base=world_vertices(bpy.data.objects['UR_FOUNDATION'])
assert base[:,2].min()<min(plan['source']['perimeter_grade_ln02_m'])-400
assert abs(base[:,2].max()-fo[:,2].min())<.00001

counter_support=[]
for i in [2,3,4,6,7]:
    table=bpy.data.objects[f'UR_COUNTER_{i}_WORKTOP' if i in [2,3,4] else f'UR_BACK_WORKTOP_{i}']
    table_bottom=world_vertices(table)[:,2].min()
    supports=[o for o in collection.objects if o.name.startswith(f'UR_CABINET_{i}_SIDE_')]
    assert len(supports)==2
    gap=[table_bottom-world_vertices(o)[:,2].max() for o in supports]
    assert max(abs(x) for x in gap)<.0001
    plinth=world_vertices(bpy.data.objects[f'UR_CABINET_{i}_PLINTH'])
    assert abs(plinth[:,2].min()-floor)<.00001
    counter_support.append({'edge':i,'support_gap_m':gap,'plinth_floor_gap_m':float(plinth[:,2].min()-floor)})

clearance=[]
for i in plan['service_edges_inferred']:
    hatch=bpy.data.objects[f'UR_HATCH_{i}_PIVOT']
    assert abs(hatch.rotation_euler.x-np.radians(plan['hatch_open_degrees']))<.00001
    skin=world_vertices(bpy.data.objects[f'UR_HATCH_{i}_SKIN'])
    samples=[]
    for q in skin[np.argsort(skin[:,2])[:4]]:
        level=ground_level(q[:2])
        if level is not None:samples.append(float(q[2]-level))
    assert len(samples)>=2 and min(samples)>2.03,(i,samples)
    clearance.append({'edge':i,'lowest_hatch_above_authored_ground_m':min(samples),'runtime_enabled':False})

edge=plan['source']['edges'][7]
a=np.array(edge['a_lv95'])-origin[:2];b=np.array(edge['b_lv95'])-origin[:2]
t=(b-a)/edge['length_m'];n=np.array(edge['outward_xy'])
sink_xy=(a+b)/2-n*.35
ray_origin=Vector((*sink_xy,floor+1.3));direction=Vector((0,0,-1))
hit_counter,_,_,_=bpy.data.objects['UR_BACK_WORKTOP_7'].ray_cast(ray_origin,direction)
hit_bowl,bowl_point,_,_=bpy.data.objects['UR_WASH_BOWL'].ray_cast(ray_origin,direction)
assert not hit_counter and hit_bowl,'Sink is obstructed by an uncut countertop'
assert abs(bowl_point.z-floor-.695)<.0001

staff_edge=plan['source']['edges'][plan['staff_door_edge_inferred']]
staff_xy=(np.array(staff_edge['a_lv95'])+np.array(staff_edge['b_lv95']))/2-origin[:2]+np.array(staff_edge['outward_xy'])*.12
staff_ground=ground_level(staff_xy);assert staff_ground is not None
threshold_rise=floor+.018-staff_ground
assert 0<=threshold_rise<.07,threshold_rise
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
for name in ['UR_QA_COUNTER','UR_QA_NORTH','UR_QA_STAFF']:
    camera=bpy.data.objects[name];level=ground_level(camera.location[:2]);assert level is not None and abs(camera.location.z-level-1.65)<.0001

missing=[]
for ob in collection.objects:
    if ob.type!='MESH':continue
    assert ob.data.vertices and ob.data.polygons
    for mat in ob.data.materials:
        if not mat or not mat.use_nodes:continue
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image and not node.image.packed_file and not Path(bpy.path.abspath(node.image.filepath)).is_file():missing.append(node.image.name)
assert not missing,missing
rec={'version':scene['version'],'objects':len(collection.objects),'footprint_area_m2':float(area),'roof_ln02_m':float(ro[:,2].max()+400),'floor_ln02_m_inferred':float(fo[:,2].max()+400),'counter_support':counter_support,'hatch_clearance':clearance,'sink_aperture_clear':True,'staff_threshold_rise_m':float(threshold_rise),'cameras_on_rebuilt_ground':True,'original_photo_nodes_retained':2039,'missing_images':missing,'geometry_checks_passed':True,'natural_use_verified':False,'runtime_enabled':False,'visual_acceptance':False}
if scene['version'] in ['G1_020r1','G1_020r2','G1_020r3','G1_020r4'] or scene['version'].startswith(('G1_021','G1_022','G1_023')):
    seams=[]
    for a,b in [(2,3),(3,4),(6,7)]:
        def top(idx):
            name=f'UR_COUNTER_{idx}_WORKTOP' if idx in [2,3,4] else f'UR_BACK_WORKTOP_{idx}'
            return world_vertices(bpy.data.objects[name])[:4]
        aa,bb=top(a),top(b)
        gaps=[float(np.linalg.norm(aa[x]-bb[y])) for x,y in [(1,0),(2,3)]]
        assert all(.0015<g<.0022 for g in gaps),(a,b,gaps)
        seams.append({'edges':[a,b],'end_gap_m':gaps})
    stays=[]
    for idx in [2,3,4]:
        pivot=bpy.data.objects[f'UR_HATCH_{idx}_PIVOT']
        for side in [0,1]:
            data=json.loads(pivot[f'stay_{side}'])
            barrel=world_vertices(bpy.data.objects[f'UR_STAY_{idx}_{side}_BARREL'])
            rod=world_vertices(bpy.data.objects[f'UR_STAY_{idx}_{side}_ROD'])
            error=max(np.linalg.norm(barrel[:20].mean(0)-data['wall_anchor_local']),np.linalg.norm(rod[20:40].mean(0)-data['hatch_anchor_open_local']))
            assert error<.0001,error
            stays.append({'hatch':idx,'side':side,'anchor_error_m':float(error)})
    cowl=bpy.data.objects['UR_ROOF_EXHAUST_COWL']
    assert min(p.normal.z for p in list(cowl.data.polygons)[:64])>.99
    cowl_support=[]
    for idx in range(3):
        ob=bpy.data.objects[f'UR_ROOF_COWL_STAY_{idx}'];vv=world_vertices(ob);xy=vv[:1,:2].mean(0)
        hit,point,_,_=cowl.ray_cast(Vector((*xy,roof+1)),Vector((0,0,-1)))
        assert hit
        delta=float(vv[:,2].max()-point.z)
        assert -.004<delta<.001,delta
        assert all(p.area>1e-12 for p in ob.data.polygons)
        cowl_support.append({'stay':idx,'top_relative_to_cowl_outer_surface_m':delta})
    assert bpy.data.objects['UR_FRIDGE_BODY'].data.materials[0].name=='UR | aged warm pale enamel'
    rec['refinement_checks']={'counter_seams':seams,'six_stay_anchor_checks':stays,'cowl_support':cowl_support,'cowl_top_faces_outward':True,'fridge_coating_not_weathered':True}
out=ROOT/'evidence'/scene['version'];out.mkdir(exist_ok=True)
(out/'kiosk_geometry_check.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
print(json.dumps(rec))
