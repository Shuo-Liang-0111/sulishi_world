"""Apply the inspected grade patch to027 without moving any source XY or masts."""
from pathlib import Path
import hashlib,json,runpy,sys
import bpy
import numpy as np
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade';E=R/'evidence/G1_027r1'
sys.path.insert(0,str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest
s=bpy.context.scene
assert s['version']=='G1_027' and Path(bpy.data.filepath).name=='G1_027_bridge_deck_working.blend'
p=json.loads((D/'027r1_patch.json').read_text());arrays=np.load(D/'027r1_vertex_patch.npz')
assert hashlib.sha256((D/'027r1_vertex_patch.npz').read_bytes()).hexdigest()==p['patch_sha256']
for name,digest in p['inputs'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest,name
runpy.run_path(str(R/'tools/blender_check_bridge_grade_patch.py'))
for row in p['objects']:
    ob=bpy.data.objects[row['name']]
    assert ob.data.users==1 and not ob.data.library and json.loads(json.dumps(mesh_digest(ob.data)))==row['before_fingerprint'],ob.name
before={o.name:(o.data.as_pointer() if o.data else None,tuple(o.matrix_basis),o.hide_render,
    tuple(slot.material.as_pointer() if slot.material else None for slot in o.material_slots)) for o in s.objects}
E.mkdir(exist_ok=True);after=[]
for row in p['objects']:
    ob=bpy.data.objects[row['name']];v=arrays[row['key']]
    old=np.array([q.co[:] for q in ob.data.vertices],dtype=np.float32)
    assert np.array_equal(v[:,:2],old[:,:2]) and v.shape==old.shape
    ob.data.vertices.foreach_set('co',v.ravel());ob.data.update()
    ob['grade_revision']='G1_027r1';ob['grade_basis']='Cached road photo support; local smoothed fit and retained bank tie, inferred.'
    after.append(dict(name=ob.name,mesh_fingerprint=mesh_digest(ob.data),max_shift_m=row['max_shift_m']))
assert len(s.objects)==16453
for name,state in before.items():
    o=bpy.data.objects[name]
    assert (o.data.as_pointer() if o.data else None,tuple(o.matrix_basis),o.hide_render,
        tuple(slot.material.as_pointer() if slot.material else None for slot in o.material_slots))==state,name
s['version']='G1_027r1';s['grade_patch_file']='derived/bellevue/bridge_grade/027r1_patch.json'
bpy.context.view_layer.update()
(E/'construction.json').write_text(json.dumps(dict(version=s['version'],objects=16453,changed_meshes=len(after),
    after_fingerprints=after,patch_sha256=p['patch_sha256'],source_masts_untouched=True,xy_topology_uv_materials_preserved=True,
    visual_acceptance=False,natural_use_verified=False),indent=2),encoding='utf-8')
runpy.run_path(str(R/'tools/blender_check_bridge_grade_patch.py'))
runpy.run_path(str(R/'tools/blender_check_bridge_deck.py'))
print('GRADE_PATCH_APPLIED',len(after),flush=True)
