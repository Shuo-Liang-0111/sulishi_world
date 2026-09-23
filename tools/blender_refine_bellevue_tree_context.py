import bpy,json,hashlib
import numpy as np
from mathutils import Vector
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_008r6'
cutpath=ROOT/'derived/bellevue/west_context/tree_69773_refined_photo_cut.json';cut=json.loads(cutpath.read_text());old=json.loads((ROOT/'derived/bellevue/west_context/tree_69773_photo_cut.json').read_text());before={str(p['node']):p for p in old['overrides']}
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for p in cut['overrides']:
 key=str(p['node'])
 if p==before.get(key):continue
 ob=context[key];src=originals[key];assert ob.matrix_basis==src.matrix_basis
 vv=np.array(p['vertices'],dtype=np.float32);uvv=np.array(p['uv_source_v_unflipped'],dtype=np.float32)
 me=bpy.data.meshes.new('BE_TREE_69773_REFINED_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis'];changed.append(key)
cam=bpy.data.objects['BE_QA_WEST_TREE'];review=json.loads((ROOT/'derived/bellevue/west_context/tree_69773_volume_review.json').read_text());cam.location=review['camera_position_local'];cam.data.lens=22.5
tree=json.loads((ROOT/'derived/bellevue/west_context/tree_69773_input.json').read_text(encoding='utf-8'));root=Vector([*tree['source']['geometry']['coordinates'],tree['ground_ln02_m']])-Vector(tree['origin']);target=root+Vector((0,0,5.9))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam['ground_note']='Verified on constructed road triangle;1.65m above actual support.'
for col in list(cam.users_collection):col.objects.unlink(cam)
bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(cam)
scene.camera=cam
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.use_local_camera=False;area.spaces.active.camera=cam
scene['version']='G1_008r7';scene['photo_cut_file']=str(cutpath.relative_to(ROOT));bpy.context.view_layer.update()
native=ROOT/'native/G1_008r7_west_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True,published_as=None,next='Inspect full tree after bounded photo-wall replacement; native morphology and near-ground connections remain under review')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2))
out=ROOT/'evidence/G1_008r7';out.mkdir(exist_ok=True);(out/'tree_context_repair.json').write_text(json.dumps({'version':scene['version'],'source_nodes_changed':changed,'reference':review,'accepted':False},indent=2))
print(json.dumps({'version':scene['version'],'source_nodes_changed':changed,'accepted':False}))
