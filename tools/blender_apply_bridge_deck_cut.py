"""Apply bounded photo counterpart replacement only after bridge authoring."""
from pathlib import Path
import hashlib,json
import bpy
import numpy as np
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_027' and bpy.data.collections['43_BRIDGE_DECK']['geometry_complete']
prior=R/s['photo_cut_file'];path=R/'derived/bellevue/west_context/bridge_deck_cut.json';cut=json.loads(path.read_text())
assert hashlib.sha256(prior.read_bytes()).hexdigest()==cut['base_cut_sha256']
old={str(q['node']):q for q in json.loads(prior.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if key not in cut['bridge_deck_changed_nodes']:continue
    ob=working[key];oldmesh=ob.data
    if key in old:
        actual=np.empty(len(oldmesh.vertices)*3,np.float32);oldmesh.vertices.foreach_get('co',actual)
        assert np.array_equal(actual.reshape(-1,3),np.array(old[key]['vertices'],dtype=np.float32)),key
    materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('BD_RETAINED_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for material in materials:me.materials.append(material)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    ob.data=me
    for slot,material in zip(ob.material_slots,materials):slot.material=material
    if oldmesh.users==0 and oldmesh.library is None:bpy.data.meshes.remove(oldmesh)
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['bridge_deck_changed_nodes'])
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
s['photo_cut_file']=path.relative_to(R).as_posix();bpy.context.view_layer.update()
report=json.loads((R/'evidence/G1_027/construction.json').read_text());report.update(photo_cut_applied=True,changed_photo_nodes=changed)
(R/'evidence/G1_027/construction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BRIDGE_DECK_PHOTO_APPLIED',len(changed),flush=True)
