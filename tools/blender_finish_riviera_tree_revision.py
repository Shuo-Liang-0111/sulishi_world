"""Apply the diagnosed cross-parcel photo repair and save the full021r2 scene."""
from pathlib import Path
import json,hashlib,runpy,shutil
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_021r1'
trees=bpy.data.collections['34_RIVIERA_TREES']
assert sum(k.startswith('dense_') and bool(trees[k]) for k in trees.keys())==9
native=R/'native/G1_021r2_riviera_continuous_working.blend'
assert not native.exists() and shutil.disk_usage(R).free>800_000_000
path=R/'derived/bellevue/west_context/riviera_tree_continuous_photo_cut.json';cut=json.loads(path.read_text())
basepath=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(basepath.read_bytes()).hexdigest()
before={str(q['node']):q for q in json.loads(basepath.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if before.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.asarray(rec['vertices']).reshape(-1,3);tex=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);tex[:,1]=1-tex[:,1]
    me=bpy.data.meshes.new('RQ_CONTINUOUS_CONTEXT_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for material in materials:me.materials.append(material)
    uv=me.uv_layers.new(name='source_photo_uv');uv.data.foreach_set('uv',tex.astype(np.float32).ravel());ob.data=me
    for i,material in enumerate(materials):ob.material_slots[i].material=material
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['riviera_tree_changed_nodes'])
s['version']='G1_021r2';s['photo_cut_file']=str(path.relative_to(R));bpy.context.view_layer.update()
for name in ['blender_check_riviera_trees.py','blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/name))
library=R/'native/G1_020r2_utoquai_coating_working.blend'
assert hashlib.file_digest(library.open('rb'),'sha256').hexdigest()=='9de0f5d2d50cb599fb140e9837ade183fe6bd538e06f879889299a858d19ca13'
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
record={'version':s['version'],'native':str(native.relative_to(R)),'native_bytes':native.stat().st_size,
        'native_sha256':hashlib.file_digest(native.open('rb'),'sha256').hexdigest(),'previous_checkpoint_retained':True,
        'changed_photo_nodes':changed,'source_trees':9,'objects':len(s.objects),'immutable_shared_library_unchanged':True,
        'new_camera_or_lighting_changes':False,'visual_acceptance':False,'natural_use_verified':False,
        'script_sha256':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (R/'tools').glob('*riviera*.py')}}
(R/'evidence/G1_021r2/checkpoint.json').write_text(json.dumps(record,indent=2))
pointer=R/'runtime/station_road_working.json';w=json.loads(pointer.read_text())
w.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
         source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True,
         next='Review021r2 from the same five saved-file cameras; preserve unresolved unbuilt river/boat and protected stair context. Export and natural use remain pending.')
pointer.write_text(json.dumps(w,ensure_ascii=False,indent=2))
print(json.dumps(record),flush=True)
