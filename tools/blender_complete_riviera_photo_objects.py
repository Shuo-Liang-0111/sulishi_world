"""Apply the reviewed022r1 surface diagnosis without changing authored geometry."""
from pathlib import Path
import hashlib,json,runpy,shutil
import bpy
import numpy as np

ROOT=Path('F:/MyWorld/ZurichWorld')
s=bpy.context.scene
assert s['version']=='G1_022r1'
native=ROOT/'native/G1_022r2_riviera_object_continuity.blend'
assert not native.exists() and shutil.disk_usage(ROOT).free>400_000_000
e=ROOT/'evidence/G1_022r2';e.mkdir(exist_ok=True)
oldpath=ROOT/s['photo_cut_file']
path=ROOT/'derived/bellevue/west_context/riviera_lower_object_cut.json'
cut=json.loads(path.read_text())
assert cut['base_cut_sha256']==hashlib.sha256(oldpath.read_bytes()).hexdigest()
previous={str(q['node']):q for q in json.loads(oldpath.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if previous.get(key)==rec:continue
    ob=working[key]
    materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3)
    uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('RL_OBJECT_CONTINUITY_'+key)
    me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['object_completion_changed_nodes'])
s['version']='G1_022r2';s['photo_cut_file']=path.relative_to(ROOT).as_posix()
bpy.context.view_layer.update()
for script in ['blender_check_riviera_lower.py','blender_check_riviera_trees.py','blender_check_riviera_quay.py',
               'blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(ROOT/'tools'/script))
libraries=json.loads((ROOT/'evidence/G1_022r1/checkpoint.json').read_text())['required_immutable_libraries']
for name,digest in libraries.items():
    with (ROOT/'native'/name).open('rb') as handle:
        assert hashlib.file_digest(handle,'sha256').hexdigest()==digest
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
with native.open('rb') as handle:digest=hashlib.file_digest(handle,'sha256').hexdigest()
record={'version':s['version'],'native':native.relative_to(ROOT).as_posix(),'native_bytes':native.stat().st_size,
        'native_sha256':digest,'required_immutable_libraries':libraries,'objects':len(s.objects),
        'changed_photo_nodes':changed,'authored_geometry_materials_cameras_lighting_unchanged':True,
        'visual_acceptance':False,'natural_use_verified':False,'runtime_exported':False}
(e/'checkpoint.json').write_text(json.dumps(record,indent=2))
pointer=ROOT/'runtime/station_road_working.json';work=json.loads(pointer.read_text())
work.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],
            source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),accepted=False,not_published=True,
            next='Inspect022r2 same saved-file views; remaining water/boats/bridge and matching runtime/natural use are not complete.')
pointer.write_text(json.dumps(work,ensure_ascii=False,indent=2))
print('PHOTO_OBJECT_REPAIR_SAVED',json.dumps(record),flush=True)
