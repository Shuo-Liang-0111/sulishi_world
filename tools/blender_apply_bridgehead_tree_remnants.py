"""Apply025r1 tree-remnant replacement; all authored construction stays fixed."""
from pathlib import Path
import hashlib,json,runpy,shutil
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_025' and Path(bpy.data.filepath).name=='G1_025_bridgehead_bank_working.blend'
target=R/'native/G1_025r1_bank_tree_replacement_working.blend'
assert not target.exists() and shutil.disk_usage(R).free>600_000_000
path=R/'derived/bellevue/west_context/bridgehead_bank_tree_remnants_cut.json'
new=json.loads(path.read_text());prior=R/s['photo_cut_file']
assert hashlib.sha256(prior.read_bytes()).hexdigest()==new['base_cut_sha256']
old={str(q['node']):q for q in json.loads(prior.read_text())['overrides']}
changed_set=set(new['bank_remnant_changed_nodes'])
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
protected=[o for o in s.objects if o not in [working[key] for key in changed_set]]
def signatures():
    return [(o.name,o.data.as_pointer() if o.data else None,tuple(o.matrix_basis),o.hide_render,
             tuple(slot.material.as_pointer() if slot.material else None for slot in o.material_slots)) for o in protected]
before=signatures();count=len(s.objects);changed=[]
for rec in new['overrides']:
    key=str(rec['node'])
    if rec==old.get(key):continue
    assert key in changed_set
    ob=working[key];raw=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',raw)
    assert np.array_equal(raw.reshape(-1,3),np.array(old[key]['vertices'],dtype=np.float32)),key
    materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('UB_REPLACED_TREE_PHOTO_'+key)
    me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    previous=ob.data;ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    if previous.users==0 and previous.library is None:bpy.data.meshes.remove(previous)
    ob['construction_mask']=new['mask_basis'];changed.append(key)
assert set(changed)==changed_set and len(s.objects)==count and signatures()==before
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
s['version']='G1_025r1';s['photo_cut_file']=path.relative_to(R).as_posix()
E=R/'evidence/G1_025r1';E.mkdir(exist_ok=True)
for name in ['blender_check_quaibruecke.py','blender_check_quaibruecke_water.py','blender_check_bridgehead_bank.py']:
    runpy.run_path(str(R/'tools'/name))
s.camera=bpy.data.objects['UB_QA_NORTH'];bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
previous=json.loads((R/'evidence/G1_025/checkpoint.json').read_text())
record=dict(version=s['version'],native=target.relative_to(R).as_posix(),native_bytes=target.stat().st_size,
    native_sha256=digest,objects=len(s.objects),changed_photo_nodes=changed,
    untouched_object_signatures_preserved=len(protected),original_photo_nodes=2039,
    required_immutable_libraries=previous['required_immutable_libraries'],
    authored_geometry_material_camera_transform_lighting_changes=False,visual_acceptance=False,natural_use_verified=False,runtime_exported=False,
    source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    source_scripts={name:hashlib.sha256((R/'tools'/name).read_bytes()).hexdigest() for name in
        ['prepare_bridgehead_bank_tree_remnants.py','blender_apply_bridgehead_tree_remnants.py']})
(E/'checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
p=R/'runtime/station_road_working.json';w=json.loads(p.read_text());w.update(version=s['version'],native=str(target),
    source_cut_file=s['photo_cut_file'],source_cut_sha256=record['source_cut_sha256'],accepted=False,not_published=True,
    next='Inspect original025 cameras from saved025r1; local tree-remnant heuristic, wall16002 and remaining unbuilt context unresolved.')
p.write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
print('BANK_TREE_REPLACEMENT_SAVED',json.dumps(record),flush=True)
