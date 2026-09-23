"""G1_007 staging: source-located station road surfaces and recessed physical rails."""
import bpy,bmesh,json,math,ast
import numpy as np
from mathutils import Vector
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_006r2'
payload=json.loads((ROOT/'derived/bellevue/transport/road_input.json').read_text())
cut=json.loads((ROOT/'derived/bellevue/transport/photo_cut.json').read_text())
parent=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
building=bpy.data.collections.new('11_BELLEVUE_STREET_SURFACES');parent.children.link(building)
tree=ast.parse((ROOT/'tools/blender_build_bellevue.py').read_text())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','triangles','material']]
exec(compile(ast.Module(body=defs,type_ignores=[]),'verified_mesh_helpers','exec'))
asphalt=bpy.data.materials['asphalt_03'];steel=material('BE | worn tram rail head',(.28,.285,.275),.29,.92)
groove=material('BE | recessed rail groove',(.035,.038,.037),.83,.12)
materials={'road_asphalt':asphalt,'rail_steel':steel,'groove_floor':groove,'groove_wall':groove}
for part in payload['pieces']:
    if not part['triangles']:continue
    ob=triangles('BE_ROAD_'+part['id'],part['triangles'],materials[part['kind']],payload['report']['height_basis']+' '+payload['report']['rail_profile_basis'])
    ob['place']='Bellevue_station_streets';ob['source_id']=part['id'];ob['surface_role']=part['kind'];ob['quality_status']='geometry staging; curbs, crossings, pointwork and collision not accepted'
    if 'egid' in ob:del ob['egid']
    if part['kind']=='road_asphalt':
        uv=ob.data.uv_layers.new(name='real_scale_2.05m')
        for loop in ob.data.loops:
            v=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x/2.05,v.y/2.05)
        ob['collision_role']='potential_walkable_surface_not_runtime_enabled'
# Replace only working copies. Original source collection and every source file remain intact.
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for part in cut['overrides']:
    key=str(part['node']);ob=context[key];origin=originals[key]
    assert ob.matrix_basis==origin.matrix_basis
    vv=np.array(part['vertices'],dtype=np.float32);uvv=np.array(part['uv_source_v_unflipped'],dtype=np.float32)
    me=bpy.data.meshes.new('BE_ROAD_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
    for mat in origin.data.materials:me.materials.append(mat)
    uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.flatten())
    ob.data=me;ob['construction_mask']='Bellevue island + official station road polygons';ob['source_geometry_unchanged_in_reference']=True
assert len(originals)==2039 and len(context)==2039
allground=np.array([v for p in payload['pieces'] if p['kind']=='road_asphalt' for t in p['triangles'] for v in t])
def camera(name,e,n,target,lens=30,eye=1.65):
    xy=np.array([e-2683775,n-1246700]);order=np.argsort(np.linalg.norm(allground[:,:2]-xy,axis=1))[:3];z=float(np.mean(allground[order,2]))+eye
    cd=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=(xy[0],xy[1],z);cd.lens=lens
    aim=Vector((target[0]-2683775,target[1]-1246700,target[2]-400));ob.rotation_euler=(aim-ob.location).to_track_quat('-Z','Y').to_euler();return ob
camera('BE_QA_ROAD_WEST',2683541,1246830,[2683575,1246838,410.2],30)
camera('BE_QA_ROAD_SOUTH',2683577,1246819,[2683578,1246840,410.0],30)
camera('BE_QA_STATION_STREETS',2683496,1246758,[2683575,1246840,408.4],42,45)
scene['version']='G1_007';scene['photo_cut_file']='derived/bellevue/transport/photo_cut.json';scene['quality_status']='Station road/rail geometry staging; not visual or usability acceptance'
scene.camera=bpy.data.objects['BE_QA_ROAD_SOUTH'];bpy.context.view_layer.update()
native=ROOT/'native/G1_007_station_roads_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record={'version':'G1_007','native':str(native),'source_cut_file':scene['photo_cut_file'],'source_cut_nodes':len(cut['overrides']),'road_area_m2':payload['report']['road_area_m2'],'new_road_objects':len(building.objects),'accepted':False,'not_published':True,'next':'Inspect human-height and overview native renders; resolve road grade/curb joins, rail crossings and road markings before integrating as a public working checkpoint.'}
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
