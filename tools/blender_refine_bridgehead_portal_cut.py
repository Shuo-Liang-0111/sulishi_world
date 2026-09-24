"""Apply diagnosed whole lake-edge remnants within this unsaved026 author."""
from pathlib import Path
import json
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_026' and Path(bpy.data.filepath).name=='G1_025r1_bank_tree_replacement_working.blend'
old=json.loads((R/'derived/bellevue/bridgehead_portal/photo_cut_before_edge_refinement.json').read_text())
new=json.loads((R/'derived/bellevue/west_context/bridgehead_portal_cut.json').read_text())
assert old['portal_changed_nodes']==new['portal_changed_nodes']==['34256']
ob=bpy.data.objects['CTX_I3S_34256']
a=next(q for q in old['overrides'] if str(q['node'])=='34256');b=next(q for q in new['overrides'] if str(q['node'])=='34256')
v=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',v)
assert np.array_equal(v.reshape(-1,3),np.array(a['vertices'],dtype=np.float32))
materials=[slot.material for slot in ob.material_slots];prior=ob.data
mesh=bpy.data.meshes.new('BP_RETAINED_PHOTO_34256_EDGE');mesh.from_pydata(b['vertices'],[],np.arange(len(b['vertices'])).reshape(-1,3).tolist());mesh.update()
for material in materials:mesh.materials.append(material)
uv=np.array(b['uv_source_v_unflipped']);uv[:,1]=1-uv[:,1]
mesh.uv_layers.new(name='source_photo_uv').data.foreach_set('uv',uv.astype(np.float32).ravel());ob.data=mesh
for slot,material in zip(ob.material_slots,materials):slot.material=material
if prior.users==0 and prior.library is None:bpy.data.meshes.remove(prior)
ob['construction_mask']=new['mask_basis'];bpy.context.view_layer.update()
print('PORTAL_PHOTO_EDGE_REFINED',len(a['vertices'])//3,len(b['vertices'])//3,flush=True)
