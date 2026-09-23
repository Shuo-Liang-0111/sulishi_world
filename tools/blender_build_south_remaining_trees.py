"""Continue from reviewed G1_014r3, replacing the remaining AV3573 tree volumes.

Per-tree progress permits inspection after a transport timeout. A complete native
checkpoint is written only after all geometry, source-preserving cuts and grounded
review cameras are present. Never rerun this on a later checkpoint.
"""
import ast
import bpy
import hashlib
import json
import math
import numpy as np
from mathutils import Vector
from pathlib import Path

R = Path('F:/MyWorld/ZurichWorld')
s = bpy.context.scene
assert s['version'] == 'G1_014r3'
inputs = json.loads((R/'derived/bellevue/south_remaining/trees_input.json').read_text(encoding='utf-8'))
rootcol = bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
name = '26_BELLEVUE_SOUTH_REMAINING_TREES'
collection = bpy.data.collections.get(name)
if collection is None:
    collection = bpy.data.collections.new(name)
    rootcol.children.link(collection)
E = R/'evidence/G1_015'
E.mkdir(exist_ok=True)
src = ast.parse((R/'tools/blender_build_south_public_space.py').read_text(encoding='utf-8'))
start = next(i for i,n in enumerate(src.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='old' for t in n.targets))
end = next(i for i,n in enumerate(src.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cutpath' for t in n.targets))
treecode = compile(ast.Module(body=src.body[start:end],type_ignores=[]),'individual_plane_tree','exec')
all_reports = []
for entry in inputs['trees']:
    ident = entry['source']['properties']['objectid']
    names = [f'BS_TREE_{ident}_{role}' for role in ['WOOD','TWIGS','LEAVES']]
    present = [bpy.data.objects.get(n) for n in names]
    if any(present):
        assert all(present)
        assert all(collection in o.users_collection and len(o.data.vertices)>0 for o in present)
        assert collection.get(f'complete_{ident}',False), 'Incomplete tree requires local inspection before resume'
        all_reports.append(json.loads(collection[f'report_{ident}']))
        continue
    td = {'trees':[entry]}
    exec(treecode)
    assert len(reports)==1
    all_reports.extend(reports)
    collection[f'complete_{ident}'] = True
    collection[f'report_{ident}'] = json.dumps(reports[0])
    (E/'tree_build_progress.json').write_text(json.dumps({'base':'G1_014r3','completed_trees':all_reports,'native_checkpoint_written':False},indent=2))
    print('Tree completed:',ident,flush=True)

cutpath = R/inputs['source_cut_file']
cut = json.loads(cutpath.read_text())
previous = json.loads((R/s['photo_cut_file']).read_text())
before = {str(p['node']):p for p in previous['overrides']}
working = {str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
originals = {str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
changed = []
for item in cut['overrides']:
    key = str(item['node'])
    if item == before.get(key):
        continue
    ob, source = working[key], originals[key]
    assert ob.matrix_basis == source.matrix_basis
    v = np.asarray(item['vertices']).reshape(-1,3)
    tex = np.asarray(item['uv_source_v_unflipped']).reshape(-1,2)
    me = bpy.data.meshes.new('BS_FINISH_CONTEXT_'+key)
    me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist())
    me.update()
    for mat in source.data.materials:
        me.materials.append(mat)
    layer = me.uv_layers.new(name='source_photo_uv')
    tex[:,1] = 1-tex[:,1]
    layer.data.foreach_set('uv',tex.astype(np.float32).ravel())
    old_mesh = ob.data
    ob.data = me
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    ob['construction_mask'] = cut['mask_basis']
    changed.append(key)

bpy.context.view_layer.update()
ground = [o for o in rootcol.all_objects if o.type=='MESH' and (
    o.name in ['BS_ASPHALT','BS_SOIL','SV_LANDING_ASPHALT','BE_PAVING_ASPHALT',
               'BE_PUBLIC_PLATFORM','BE_WEST_PLATFORM'] or o.get('surface_role')=='road_concrete')]
cameras = [
    ('BE_QA_SOUTH_GROVE_WEST',[2683576.0,1246783.5],[2683583.0,1246794.0,410.5],30),
    ('BE_QA_SOUTH_GROVE_EAST',[2683604.0,1246789.0],[2683587.0,1246803.0,410.5],30),
    ('BE_QA_SOUTH_GROVE_ROOT',[2683580.0,1246781.0],[2683583.159,1246781.263,409.0],35),
]
checks = []
for name, xy, target, lens in cameras:
    local = np.asarray(xy)-[2683775,1246700]
    levels = []
    for ob in ground:
        inverse = ob.matrix_world.inverted()
        hit, point, _, _ = ob.ray_cast(inverse@Vector((*local,30)),inverse.to_3x3()@Vector((0,0,-1)))
        if hit:
            levels.append((ob.matrix_world@point).z)
    assert levels, ('Missing actual ground at review camera',name)
    floor = max(levels)
    co = bpy.data.objects.get(name)
    if co is None:
        cd = bpy.data.cameras.new(name)
        co = bpy.data.objects.new(name,cd)
        bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co)
    co.location = (*local,floor+1.65)
    co.rotation_euler = (Vector(np.asarray(target)-[2683775,1246700,400])-co.location).to_track_quat('-Z','Y').to_euler()
    co.data.lens = lens
    co['eye_height_m'] = 1.65
    co['floor_height_local'] = floor
    checks.append({'name':name,'ground_local_z':floor,'eye_height_m':1.65})

s['version'] = 'G1_015'
s['photo_cut_file'] = inputs['source_cut_file']
s.camera = bpy.data.objects['BE_QA_SOUTH_GROVE_EAST']
s.cycles.device = 'CPU'
s.render.threads_mode = 'FIXED'
s.render.threads = 10
bpy.context.view_layer.update()
bpy.ops.file.pack_all()
native = R/'native/G1_015_south_grove_working.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
record = json.loads((R/'runtime/station_road_working.json').read_text())
record.update(version=s['version'],native=str(native),source_cut_file=inputs['source_cut_file'],
              source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),
              source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True)
(R/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2))
report = {'version':s['version'],'native':str(native),'trees':all_reports,'changed_photo_nodes':changed,
          'camera_grounding':checks,'original_source_nodes':len(originals),'accepted':False,
          'all_12_island_trees_authored':True,'individual_forms_inferred':True,
          'ordinary_use_verified':False,'native_checkpoint_written':True}
(E/'construction.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'version':s['version'],'tree_ids':[t['source_id'] for t in all_reports],
                  'native':str(native),'source_nodes_changed':len(changed)}))
