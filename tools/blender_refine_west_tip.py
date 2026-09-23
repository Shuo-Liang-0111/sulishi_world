"""Apply only the bounded platform-tip context delta, retaining original sources."""
import bpy,json,numpy as np,hashlib
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_008r4'
path=ROOT/'derived/bellevue/west_context/platform_tip_photo_cut.json';cut=json.loads(path.read_text())
base=json.loads((ROOT/'derived/bellevue/west_context/fixtures_photo_cut.json').read_text());old={str(p['node']):p for p in base['overrides']}
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for p in cut['overrides']:
 key=str(p['node'])
 if p==old.get(key):continue
 ob=context[key];origin=originals[key];assert ob.matrix_basis==origin.matrix_basis
 vv=np.array(p['vertices'],dtype=np.float32);uvv=np.array(p['uv_source_v_unflipped'],dtype=np.float32)
 me=bpy.data.meshes.new('BE_WEST_TIP_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in origin.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.flatten());ob.data=me;ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert len(changed)==cut['tip_stats']['nodes_changed']
scene['version']='G1_008r5';scene['photo_cut_file']=str(path.relative_to(ROOT));scene.camera=bpy.data.objects['BE_QA_WEST_PLATFORM_REVERSE'];bpy.context.view_layer.update()
native=ROOT/'native/G1_008r5_west_facilities_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((ROOT/'runtime/station_road_working.json').read_text());rec.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),accepted=False,not_published=True,published_as=None)
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));out=ROOT/'evidence/G1_008r5';out.mkdir(exist_ok=True)
(out/'tip_build.json').write_text(json.dumps({'version':scene['version'],'nodes':changed,'cut_stats':cut['tip_stats'],'accepted':False},indent=2));print(json.dumps({'version':scene['version'],'native':str(native),'nodes':changed}))
