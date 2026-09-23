"""Repair022 from inspected views: projected beam UVs, tree remnants and rails."""
from pathlib import Path
import ast,json,hashlib,math,runpy,shutil
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/riviera_lower'
s=bpy.context.scene;assert s['version']=='G1_022'
native=R/'native/G1_022r1_riviera_lower_refined.blend'
assert not native.exists() and shutil.disk_usage(R).free>400_000_000
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
C=bpy.data.collections['36_RIVIERA_LOWER_APPROACH'];E=R/'evidence/G1_022r1';E.mkdir(exist_ok=True)
fixed=[];uv_degenerate=0
for ob in C.objects:
    if len(ob.data.vertices)!=8 or 'source_plan_area_m2' in ob:continue
    v=np.array([q.co[:] for q in ob.data.vertices]);t=v[4:].mean(0)-v[:4].mean(0);t/=np.linalg.norm(t)
    cross=v[1]-v[0];cross/=np.linalg.norm(cross);up=v[3]-v[0];up/=np.linalg.norm(up)
    basis=[t,cross,up];uv=ob.data.uv_layers.active
    for face in ob.data.polygons:
        axis=int(np.argmax([abs(a@np.array(face.normal)) for a in basis]));frame=[a for k,a in enumerate(basis) if k!=axis]
        coords=[]
        for li in face.loop_indices:
            point=v[ob.data.loops[li].vertex_index];q=(float(frame[0]@point),float(frame[1]@point));coords.append(q);uv.data[li].uv=q
        q=np.array(coords);area=abs(sum(q[j,0]*q[(j+1)%len(q),1]-q[(j+1)%len(q),0]*q[j,1] for j in range(len(q))))/2
        if area<1e-10:uv_degenerate+=1
    fixed.append(ob.name)
assert uv_degenerate==0

# One continuous swept tube removes per-segment cap bands. Two extra returns
# guard the actual top landing while leaving its exit into the upper walk open.
mats={'steel':bpy.data.materials['RL | weathered zinc steel']}
tree=ast.parse((R/'tools/blender_build_riviera_lower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','tube'}],type_ignores=[]),'lower_rail_helpers','exec'))
old=[o for o in C.objects if o.name.startswith(('RL_STAIR_HAND_','RL_STAIR_MID_'))]
assert len(old)==52
old_meshes=[o.data for o in old];bpy.data.batch_remove(ids=old)
bpy.data.batch_remove(ids=[m for m in old_meshes if m.users==0])

def sweep(name,points,radius):
    points=np.asarray(points);v=[];sides=16
    for i,p in enumerate(points):
        t=points[min(i+1,len(points)-1)]-points[max(0,i-1)];t/=np.linalg.norm(t)
        cross=np.cross(t,[0,0,1]);cross/=np.linalg.norm(cross);up=np.cross(cross,t)
        v.extend([p+radius*(math.cos(k*2*math.pi/sides)*cross+math.sin(k*2*math.pi/sides)*up)-O for k in range(sides)])
    faces=[list(range(sides-1,-1,-1)),list(range((len(points)-1)*sides,len(points)*sides))]
    for i in range(len(points)-1):
        for k in range(sides):
            a=i*sides+k;b=i*sides+(k+1)%sides;faces.append([a,b,b+sides,a+sides])
    ob=mesh(name,v,faces,'steel','av_ei_flaechenelement_a.47309')
    for face in list(ob.data.polygons)[2:]:face.use_smooth=True
    return ob

bounds=np.array(P['stairs_boundaries']);base=P['floor_ln02_m'];rise=P['stair_rise_m'];top=P['stair_top_ln02_m']
tails={0:[[2683498.93,1246859.00]],1:[[2683497.15,1246861.05],[2683499.48,1246860.71]]}
for side in [0,1]:
    for h,label,r in [(1.,'HAND',.022),(.5,'MID',.014)]:
        points=[[*p,base+i*rise+h] for i,p in enumerate(bounds[:,side])]
        points.extend([[*q,top+h] for q in tails[side]])
        sweep(f'STAIR_CONTINUOUS_{label}_{side}',points,r)
    for i,q in enumerate(tails[side]):
        tube(f'LANDING_POST_{side}_{i}',[*q,top-.07],[*q,top+1.],.022,'av_ei_flaechenelement_a.47309')

path=R/'derived/bellevue/west_context/riviera_lower_canopy_cut.json';cut=json.loads(path.read_text())
oldpath=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(oldpath.read_bytes()).hexdigest()
old={str(q['node']):q for q in json.loads(oldpath.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if old.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.asarray(rec['vertices']).reshape(-1,3);tex=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);tex[:,1]=1-tex[:,1]
    me=bpy.data.meshes.new('RL_CLEAR_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    uv=me.uv_layers.new(name='source_photo_uv');uv.data.foreach_set('uv',tex.astype(np.float32).ravel());ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['lower_approach_changed_nodes'])
s['version']='G1_022r1';s['photo_cut_file']=str(path.relative_to(R));bpy.context.view_layer.update()
for script in ['blender_check_riviera_lower.py','blender_check_riviera_trees.py','blender_check_riviera_quay.py',
               'blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/script))
libraries={name:digest for name,digest in json.loads((R/'evidence/G1_022/checkpoint.json').read_text())['required_immutable_libraries'].items()}
for name,digest in libraries.items():assert hashlib.file_digest((R/'native'/name).open('rb'),'sha256').hexdigest()==digest
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
record={'version':s['version'],'native':str(native.relative_to(R)),'native_bytes':native.stat().st_size,
        'native_sha256':hashlib.file_digest(native.open('rb'),'sha256').hexdigest(),'required_immutable_libraries':libraries,
        'objects':len(s.objects),'beam_uv_objects_fixed':len(fixed),'degenerate_beam_uv_faces_after':uv_degenerate,
        'continuous_stair_rails':4,'added_landing_posts':3,'changed_photo_nodes':changed,
        'visual_acceptance':False,'natural_use_verified':False,'runtime_exported':False,
        'camera_and_lighting_unchanged':True,'previous_checkpoints_retained':True}
(E/'checkpoint.json').write_text(json.dumps(record,indent=2))
pointer=R/'runtime/station_road_working.json';work=json.loads(pointer.read_text())
work.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],
            source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),accepted=False,not_published=True,
            next='Review022r1 from same five saved-file views. Underpass, river/boats, matching runtime and natural use remain unfinished.')
pointer.write_text(json.dumps(work,ensure_ascii=False,indent=2))
print('LOWER_REFINEMENT_SAVED',json.dumps(record),flush=True)
