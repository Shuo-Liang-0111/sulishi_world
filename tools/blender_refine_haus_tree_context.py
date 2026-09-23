import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_011'
cutpath=R/'derived/bellevue/west_context/haus_trees_approach_refined_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HB_TREE_APPROACH_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
s['version']='G1_011r1';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=bpy.data.objects['HB_QA_TREE']
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.use_local_camera=False;area.spaces.active.camera=s.camera;area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.context.view_layer.update();native=R/'native/G1_011r1_haus_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_nodes=len(cut['overrides']),source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_011r1';e.mkdir(exist_ok=True);(e/'context_refinement.json').write_text(json.dumps({'version':s['version'],'basis':json.loads((R/'derived/haus_bellevue/tree_approach_review.json').read_text()),'native':str(native),'accepted':False},indent=2));print(json.dumps({'version':s['version'],'native':str(native),'accepted':False}))
