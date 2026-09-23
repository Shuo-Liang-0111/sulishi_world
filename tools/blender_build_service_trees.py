"""Continue G1_014 with three individual tree replacements and camera grounding."""
import bpy,bmesh,json,math,ast,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_014';td=json.loads((R/'derived/bellevue/south_service/trees_input.json').read_text(encoding='utf-8'));rootcol=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'];assert '25_BELLEVUE_SERVICE_TREES' not in bpy.data.collections
collection=bpy.data.collections.new('25_BELLEVUE_SERVICE_TREES');rootcol.children.link(collection)
src=ast.parse((R/'tools/blender_build_south_public_space.py').read_text(encoding='utf-8'));start=next(i for i,n in enumerate(src.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='old' for t in n.targets));end=next(i for i,n in enumerate(src.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cutpath' for t in n.targets));exec(compile(ast.Module(body=src.body[start:end],type_ignores=[]),'individual_tree_geometry','exec'))
cutpath=R/td['source_cut_file'];cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for item in cut['overrides']:
 ob=ctx[str(item['node'])];src=orig[str(item['node'])];v=np.array(item['vertices']).reshape(-1,3);uvs=np.array(item['uv_source_v_unflipped']).reshape(-1,2);me=bpy.data.meshes.new('SV_TREE_CONTEXT_'+str(item['node']));me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 layer=me.uv_layers.new(name='source_photo_uv');uvs[:,1]=1-uvs[:,1];layer.data.foreach_set('uv',uvs.astype(np.float32).ravel());ob.data=me;ob['construction_mask']=cut['mask_basis']
# Ground review cameras against actually reconstructed ground; retain original XY.
bpy.context.view_layer.update();ground=[bpy.data.objects[n] for n in ['BS_ASPHALT','SV_LANDING_ASPHALT','BS_SOIL','SV_FLOOR_TILES','BE_PAVING_ASPHALT','BE_PUBLIC_PLATFORM','BE_WEST_PLATFORM'] if n in bpy.data.objects];ground += [o for o in rootcol.all_objects if o.get('surface_role')=='road_concrete'];camchecks=[]
for name in ['BE_QA_SERVICE_FRONT','BE_QA_SERVICE_NORTH','BE_QA_SERVICE_ENTRY','BE_QA_SERVICE_INTERIOR']:
 ob=bpy.data.objects[name];levels=[]
 for surface in ground:
  hit,p,_,_=surface.ray_cast(Vector((ob.location.x,ob.location.y,30)),Vector((0,0,-1)))
  if hit:levels.append(p.z)
 if levels:ob.location.z=max(levels)+1.65;ob['floor_height_local']=max(levels);ob['grade_check_pending']=False
 camchecks.append({'name':name,'supported':bool(levels),'ground':max(levels) if levels else None})
s['version']='G1_014r1';s['photo_cut_file']=td['source_cut_file'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_014r1_service_trees_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=td['source_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));E=R/'evidence'/s['version'];E.mkdir(exist_ok=True);(E/'construction.json').write_text(json.dumps({'version':s['version'],'native':str(native),'trees':reports,'camera_grounding':camchecks,'accepted':False},indent=2));print(json.dumps({'version':s['version'],'native':str(native),'trees':reports,'camera_grounding':camchecks}))
