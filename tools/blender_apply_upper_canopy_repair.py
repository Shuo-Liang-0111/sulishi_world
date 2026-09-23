"""Apply only the evidence-bounded context difference; preserve authored objects."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version'] in ['G1_016r1','G1_017']
target='G1_017' if s['version']=='G1_016r1' else 'G1_017r1'
input=json.loads((R/('derived/bellevue/canopy_continuity/input.json' if target=='G1_017' else 'derived/bellevue/canopy_continuity/G1_017r1/input.json')).read_text())
previous=json.loads((R/s['photo_cut_file']).read_text());old={str(x['node']):x for x in previous['overrides']}
path=R/input['source_cut_file'];cut=json.loads(path.read_text())
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
source={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
authored=sorted(o.name for o in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects)
changes=[]
for item in cut['overrides']:
    key=str(item['node'])
    if item==old.get(key):continue
    ob=working[key];assert ob.matrix_basis==source[key].matrix_basis
    data=np.asarray(item['vertices']).reshape(-1,3);uv=np.asarray(item['uv_source_v_unflipped']).reshape(-1,2)
    mesh=bpy.data.meshes.new('G1_017_CONTEXT_'+key)
    mesh.from_pydata(data.tolist(),[],np.arange(len(data)).reshape(-1,3).tolist());mesh.update()
    for material in source[key].data.materials:mesh.materials.append(material)
    if len(data):
        layer=mesh.uv_layers.new(name='source_photo_uv');uv[:,1]=1-uv[:,1];layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    changes.append({'node':key,'previous_faces':len(ob.data.polygons),'new_faces':len(mesh.polygons)})
    ob.data=mesh;ob['construction_mask']=cut['mask_basis']
assert changes and len(source)==2039
assert authored==sorted(o.name for o in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects)
s['version']=target;s['photo_cut_file']=input['source_cut_file'];s.camera=bpy.data.objects['BE_QA_SOUTH_EAST_INFO_WIDE']
bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native'/f'{target}_canopy_continuity_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=input['source_cut_file'],source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True,next='Inspect canopy cleanup in the same east and north views; refresh all illumination and export before runtime review.')
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
E=R/'evidence'/target;E.mkdir(exist_ok=True)
record={'version':s['version'],'native':str(native),'changes':changes,'authored_identity_list_unchanged':True,'original_source_count':len(source),'kept_below_ln02_m':input['kept_below_ln02_m'],'accepted':False,'runtime_exported':False}
(E/'canopy_repair.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
