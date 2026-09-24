"""Apply the diagnosed unsaved025 grade and complete-wall replacement repair.

Receipts identify the exact input already applied in the author. Tree geometry,
rail supports, retained stair, lighting and all camera transforms stay fixed.
"""
from pathlib import Path
import ast,hashlib,json
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridgehead_bank'
s=bpy.context.scene;assert s['version']=='G1_025'
assert Path(bpy.data.filepath).name=='G1_024_bridge_water_context_working.blend'
C=bpy.data.collections['40_BRIDGEHEAD_BANK']
old_path=D/globals().get('PREVIOUS_INPUT','build_input_before_grade_fix.json');new_path=D/'build_input.json'
old=json.loads(old_path.read_text(encoding='utf-8'));new=json.loads(new_path.read_text(encoding='utf-8'))
assert C['input_sha256']==hashlib.sha256(old_path.read_bytes()).hexdigest()
assert old['rails']==new['rails'] and old['trees']==new['trees']
old_parts={p['name']:p for p in old['parts']}
assert set(old_parts)=={p['name'] for p in new['parts']}
mats={'paving':bpy.data.materials['asphalt_03'],
      'concrete':bpy.data.materials['QB | aged mineral structure'],
      'coping':bpy.data.materials['QB | dark dressed coping']}
src=ast.parse((R/'tools/blender_build_quaibruecke.py').read_text(encoding='utf-8'))
helper=ast.unparse(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='mesh'],type_ignores=[])).replace("'QB_'","'UB_'")
exec(compile(helper,'bank_repair_mesh_helper','exec'))
changed=[]
for p in new['parts']:
    if p==old_parts[p['name']]:continue
    assert p['role'] in mats and abs(p['area_m2']-old_parts[p['name']]['area_m2'])<1e-6
    ob=bpy.data.objects['UB_'+p['name']]
    temp=mesh('REPAIR_'+p['name'],p['vertices'],p['faces'],p['role'],p['source'])
    previous=ob.data;ob.data=temp.data
    bpy.data.objects.remove(temp,do_unlink=True)
    if previous.users==0 and previous.library is None:bpy.data.meshes.remove(previous)
    changed.append(ob.name)
C['input_sha256']=hashlib.sha256(new_path.read_bytes()).hexdigest()

old_cut=D/globals().get('PREVIOUS_CUT','applied_photo_cut_before_grade_fix.json')
new_cut=R/'derived/bellevue/west_context/bridgehead_bank_cut.json'
a=json.loads(old_cut.read_text(encoding='utf-8'));b=json.loads(new_cut.read_text(encoding='utf-8'))
assert a['base_cut_sha256']==b['base_cut_sha256']
before={str(q['node']):q for q in a['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
photo_changed=[]
for rec in b['overrides']:
    key=str(rec['node'])
    if rec==before.get(key):continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3)
    uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('UB_PHOTO_REPAIRED_'+key)
    me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    previous=ob.data;ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    if previous.users==0 and previous.library is None:bpy.data.meshes.remove(previous)
    ob['construction_mask']=b['mask_basis'];photo_changed.append(key)
bpy.context.view_layer.update()
record=dict(grade_parts=changed,photo_nodes=photo_changed,
            old_input_sha256=hashlib.sha256(old_path.read_bytes()).hexdigest(),
            input_sha256=C['input_sha256'],old_cut_sha256=hashlib.sha256(old_cut.read_bytes()).hexdigest(),
            cut_sha256=hashlib.sha256(new_cut.read_bytes()).hexdigest(),
            tree_rail_camera_lighting_changes=False,native_saved=False)
(R/'evidence/G1_025'/globals().get('REPAIR_REPORT','grade_wall_repair.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
print('UPPER_BANK_REPAIR',json.dumps(record),flush=True)
