"""Apply ray-grounded lower photo repair and replace rejected synthetic bark."""
import bpy,json,hashlib,shutil,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_019r1';E=R/'evidence/G1_019r2';E.mkdir(exist_ok=True)
path=R/'derived/bellevue/west_context/limmat_sidewalk_low_canopy_cut.json';cut=json.loads(path.read_text());base=json.loads((R/s['photo_cut_file']).read_text());before={str(x['node']):x for x in base['overrides']};assert cut['base_cut_sha256']==hashlib.sha256((R/s['photo_cut_file']).read_bytes()).hexdigest()
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for q in cut['overrides']:
 key=str(q['node'])
 if before.get(key)==q:continue
 ob,src=working[key],originals[key];assert ob.matrix_basis==src.matrix_basis;v=np.asarray(q['vertices']).reshape(-1,3);tex=np.asarray(q['uv_source_v_unflipped']).reshape(-1,2);me=bpy.data.meshes.new('LM_LOW_REPAIR_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
 for mat in src.data.materials:me.materials.append(mat)
 uv=me.uv_layers.new(name='source_photo_uv');tex[:,1]=1-tex[:,1];uv.data.foreach_set('uv',tex.astype(np.float32).ravel());old=ob.data;ob.data=me
 if old.users==0:bpy.data.meshes.remove(old)
 ob['construction_mask']=cut['mask_basis'];changed.append(key)

material=bpy.data.materials['bark_brown_02'];material.use_fake_user=True;folder=R/'sources/textures/polyhaven/bark_brown_02';folder.mkdir(parents=True,exist_ok=True);files=[]
for n in material.node_tree.nodes:
 if n.type=='MAPPING':n.inputs['Scale'].default_value=(1,1,1)
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.38
 if n.type=='OUTPUT_MATERIAL':
  for link in list(n.inputs['Displacement'].links):material.node_tree.links.remove(link)
 if n.type=='TEX_IMAGE' and n.image:
  original=Path(bpy.path.abspath(n.image.filepath));dest=folder/original.name
  if original.resolve()!=dest.resolve():
   if original.exists():shutil.copy2(original,dest)
   elif n.image.packed_file:dest.write_bytes(bytes(n.image.packed_file.data))
   else:raise FileNotFoundError(f'Neither source file nor packed image exists: {original}')
  n.image.filepath=str(dest);files.append({'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
material['source_url']='https://polyhaven.com/a/bark_brown_02';material['license']='CC0';material['author']='Rob Tuytel';material['world_texture_size_m']=.999999;material['basis']='Generic scanned furrowed bark proxy chosen after synthetic parallel grooves were rejected in actual near render. Not a local Sophora trunk scan.'
receipt={'source_url':material['source_url'],'license':'CC0','author':'Rob Tuytel','download_via':'Blender MCP Poly Haven integration','real_world_extent_m':[.999999,.999999],'files':files,'use':'Material proxy; individual species and local tree identity still from official inventory, no claim of exact bark scan.'};(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
records=[]
for ob in bpy.data.collections['31_LIMMAT_SIDEWALK_TREES'].objects:
 if not ob.name.endswith('_WOOD') or not ob.data.materials or ob.data.materials[0].name!='LM | Sophora gray-brown furrowed bark':continue
 vertices=np.asarray([v.co[:] for v in ob.data.vertices]);h=hashlib.sha256(vertices.tobytes()).hexdigest();uv=ob.data.uv_layers.active;data=np.asarray([u.uv[:] for u in uv.data]);data*=np.array([1.2,4.0]);ident=int(ob['source_id'].split('.')[-1]);phase=(ident%997)/997*2*np.pi
 # Slow circumferential phase drift avoids aligned repeating knots while keeping
 # the metre-scale grain and height. This is a material inference, not geometry.
 data[:,0]+=.028*np.sin(data[:,1]*.78+phase)+(ident%107)/107
 data[:,1]+=(ident%89)/89;uv.data.foreach_set('uv',data.astype(np.float32).ravel());ob.data.materials[0]=material
 assert hashlib.sha256(np.asarray([v.co[:] for v in ob.data.vertices]).tobytes()).hexdigest()==h
 records.append({'object':ob.name,'geometry_sha256_unchanged':h,'material_source':material['source_url']})
assert len(records)==8
s['version']='G1_019r2';s['photo_cut_file']=str(path.relative_to(R));bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_019r2_limmat_clearance_working.blend';assert not native.exists();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
(E/'repair.json').write_text(json.dumps({'version':s['version'],'native':str(native),'changed_photo_nodes':changed,'material_replacements':records,'basis':'Observed019r1 image defects attributed by camera rays. Retained kiosk/eaves and cadastral wall/stair guards; clear only already-rebuilt tree/sidewalk volumes. Replaced procedural bark that appeared as regular parallel lines.','original_photo_nodes':len(originals),'new_runtime_export':False,'accepted':False},indent=2))
print('G1_019r2_NATIVE_SAVED',native,flush=True)
