"""Apply only the prepared eight photographic-node replacements after tree build."""
from pathlib import Path
import json,hashlib
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_021'
trees=bpy.data.collections['34_RIVIERA_TREES'];assert len(trees.objects)==27
assert sum(k.startswith('complete_') and bool(trees[k]) for k in trees.keys())==9
path=R/'derived/bellevue/west_context/riviera_tree_photo_cut.json';cut=json.loads(path.read_text())
basepath=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(basepath.read_bytes()).hexdigest()
before={str(q['node']):q for q in json.loads(basepath.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if before.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    vertices=np.asarray(rec['vertices']).reshape(-1,3);uvs=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);uvs[:,1]=1-uvs[:,1]
    me=bpy.data.meshes.new('RQ_TREES_CONTEXT_'+key);me.from_pydata(vertices.tolist(),[],np.arange(len(vertices)).reshape(-1,3).tolist());me.update()
    for material in materials:me.materials.append(material)
    uv=me.uv_layers.new(name='source_photo_uv');uv.data.foreach_set('uv',uvs.astype(np.float32).ravel())
    ob.data=me
    for i,material in enumerate(materials):ob.material_slots[i].material=material
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['riviera_tree_changed_nodes'])
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
# Add a real1.65m eye-level root view without changing the four comparison views.
p=json.loads((R/'derived/bellevue/riviera_quay/tree_build_input.json').read_text())
entry=next(e for e in p['trees'] if e['source']['properties']['objectid']==101985)
target=np.array([*entry['xy_local'],entry['ground_ln02_m']-400+.22])
pos=target[:2]+np.array([-2.3,-1.4]);heights=[]
for ob in bpy.data.collections['33_RIVIERA_QUAY'].objects:
    if ob.get('surface_role')!='asphalt':continue
    hit,point,_,_=ob.ray_cast(Vector((*pos,30)),Vector((0,0,-1)))
    if hit:heights.append(point.z)
assert heights
name='RQ_QA_TREE_BASE';assert name not in bpy.data.objects
cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co)
co.location=(*pos,max(heights)+1.65);co.rotation_euler=(Vector(target)-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=48
co['eye_height_m']=1.65;co['floor_height_local']=max(heights)
s['version']='G1_021r1';s['photo_cut_file']=str(path.relative_to(R));bpy.context.view_layer.update()
(R/'evidence/G1_021r1/photo_replacement.json').write_text(json.dumps({'version':s['version'],'changed_photo_nodes':changed,
   'base_cut_sha256':cut['base_cut_sha256'],'original_photo_nodes':2039,'trees_authored_before_replacement':9,'new_camera':name},indent=2))
print(json.dumps({'version':s['version'],'changed_photo_nodes':changed,'objects':len(s.objects)}),flush=True)
