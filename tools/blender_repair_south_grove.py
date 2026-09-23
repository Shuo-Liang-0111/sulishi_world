"""Close pit edge gaps and remove ray-identified remnants above rebuilt crowns."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_015'
d=json.loads((R/'derived/bellevue/south_remaining/repairs_input.json').read_text())
name='BS_TREE_PIT_EXPOSED_ASPHALT_EDGES';assert name not in bpy.data.objects
v=np.asarray(d['pit_edge_triangles']);me=bpy.data.meshes.new(name)
me.from_pydata(v.reshape(-1,3).tolist(),[],np.arange(v.size//3).reshape(-1,3).tolist());me.update()
me.materials.append(bpy.data.materials['asphalt_03']);uv=me.uv_layers.new(name='physical_cut_edge')
uv.data.foreach_set('uv',np.asarray(d['pit_edge_uv'],dtype=np.float32).ravel())
ob=bpy.data.objects.new(name,me);bpy.data.collections['21_BELLEVUE_SOUTH_GROUND'].objects.link(ob)
ob['evidence_basis']=d['basis'];ob['exposed_height_m']=d['exposed_edge_height_m'];ob['collision_role']='solid_pending_runtime'
cutpath=R/d['source_cut_file'];cut=json.loads(cutpath.read_text());previous=json.loads((R/s['photo_cut_file']).read_text());before={str(x['node']):x for x in previous['overrides']}
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};source={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for item in cut['overrides']:
    key=str(item['node'])
    if item==before.get(key):continue
    ob=context[key];original=source[key];v=np.asarray(item['vertices']).reshape(-1,3);tex=np.asarray(item['uv_source_v_unflipped']).reshape(-1,2)
    new=bpy.data.meshes.new('BS_GROVE_REPAIR_CONTEXT_'+key);new.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());new.update()
    for mat in original.data.materials:new.materials.append(mat)
    uv=new.uv_layers.new(name='source_photo_uv');tex[:,1]=1-tex[:,1];uv.data.foreach_set('uv',tex.astype(np.float32).ravel())
    old=ob.data;ob.data=new
    if old.users==0:bpy.data.meshes.remove(old)
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
s['version']='G1_015r1';s['photo_cut_file']=d['source_cut_file']
bpy.context.view_layer.update();native=R/'native/G1_015r1_south_grove_edges_working.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=d['source_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True)
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));E=R/'evidence'/s['version'];E.mkdir(exist_ok=True)
report={'version':s['version'],'native':str(native),'pit_edges_m':d['pit_edge_length_m'],'edge_height_m':d['exposed_edge_height_m'],'photo_nodes_changed':changed,'original_sources_preserved':len(source),'accepted':False}
(E/'repairs.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
