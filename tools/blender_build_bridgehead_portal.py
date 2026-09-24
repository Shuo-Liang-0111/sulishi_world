"""Restore both physical bridgehead levels without moving existing geometry."""
from pathlib import Path
import ast,hashlib,json
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridgehead_portal';s=bpy.context.scene
assert s['version']=='G1_025r1' and Path(bpy.data.filepath).name=='G1_025r1_bank_tree_replacement_working.blend'
assert '42_BRIDGEHEAD_PORTAL' not in bpy.data.collections
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
E=R/'evidence/G1_026';E.mkdir(exist_ok=True)
old_count=len(s.objects);working=bpy.data.objects['CTX_I3S_34256']
def signatures():
    return {o.name:(o.data.as_pointer() if o.data else None,tuple(o.matrix_basis),o.hide_render,
            tuple(slot.material.as_pointer() if slot.material else None for slot in o.material_slots))
            for o in s.objects if not o.name.startswith('BP_') and o!=working}
before=signatures()
C=bpy.data.collections.new('42_BRIDGEHEAD_PORTAL');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
mats={'paving':bpy.data.materials['asphalt_03'],'concrete':bpy.data.materials['QB | aged mineral structure'],
      'coping':bpy.data.materials['QB | dark dressed coping']}
src=ast.parse((R/'tools/blender_build_quaibruecke.py').read_text())
helper=ast.unparse(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='mesh'],type_ignores=[])).replace("'QB_'","'BP_'")
exec(compile(helper,'portal_mesh','exec'))
for part in P['parts']:
    ob=mesh(part['name'],part['vertices'],part['faces'],part['role'],part['source'],.002 if part['role']=='coping' else 0)
    ob['construction_batch']='G1_026';ob['source_plan_area_m2']=part['area_m2']
C['input_sha256']=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
cutpath=R/'derived/bellevue/west_context/bridgehead_portal_cut.json';cut=json.loads(cutpath.read_text())
oldpath=R/s['photo_cut_file'];old=json.loads(oldpath.read_text())
assert hashlib.sha256(oldpath.read_bytes()).hexdigest()==cut['base_cut_sha256']
assert cut['portal_changed_nodes']==['34256']
prior=next(q for q in old['overrides'] if str(q['node'])=='34256');new=next(q for q in cut['overrides'] if str(q['node'])=='34256')
data=np.empty(len(working.data.vertices)*3,np.float32);working.data.vertices.foreach_get('co',data)
assert np.array_equal(data.reshape(-1,3),np.array(prior['vertices'],dtype=np.float32))
vertices=np.array(new['vertices']);uv=np.array(new['uv_source_v_unflipped']);uv[:,1]=1-uv[:,1]
materials=[q.material for q in working.material_slots];old_mesh=working.data
meshdata=bpy.data.meshes.new('BP_RETAINED_PHOTO_34256');meshdata.from_pydata(vertices.tolist(),[],np.arange(len(vertices)).reshape(-1,3).tolist());meshdata.update()
for material in materials:meshdata.materials.append(material)
layer=meshdata.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
working.data=meshdata
for slot,material in zip(working.material_slots,materials):slot.material=material
if old_mesh.users==0 and old_mesh.library is None:bpy.data.meshes.remove(old_mesh)
working['construction_mask']=cut['mask_basis']
assert signatures()==before and len(s.objects)==old_count+len(P['parts'])
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
s['version']='G1_026';s['photo_cut_file']=cutpath.relative_to(R).as_posix();bpy.context.view_layer.update()
C['geometry_complete']=True
(E/'construction.json').write_text(json.dumps(dict(version=s['version'],new_objects=len(C.objects),
    total_objects=len(s.objects),unchanged_object_signatures=len(before),changed_photo_nodes=['34256'],
    original_photo_sources=2039,cameras_lighting_existing_meshes_preserved=True,
    input_sha256=C['input_sha256'],visual_acceptance=False,natural_use_verified=False),indent=2),encoding='utf-8')
print('PORTAL_AUTHORED',len(C.objects),len(s.objects),flush=True)
