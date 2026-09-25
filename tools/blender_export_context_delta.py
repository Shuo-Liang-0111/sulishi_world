"""Export all cumulative photograph edits from the exact current native file.

This is one component of the new runtime, not a published/accepted world. An
independent reader must compare the actual GLB triangles and UVs before use.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path, validate_native
from blender_geometry_fingerprint import mesh_digest

s=bpy.context.scene;version=s['version'];native=validate_native(bpy.data.filepath)
# Blender's format enum is callback-backed: RNA's static list can be empty.
# Query the installed exporter's actual callback instead of guessing its values.
params=bpy.ops.export_scene.gltf.get_rna_type().properties
enum_choices={}
for name,value in [('export_format','GLB'),('export_materials','NONE')]:
    choices=[i.identifier for i in params[name].enum_items]
    if not choices and name=='export_format':
        import io_scene_gltf2
        choices=[row[0] for row in io_scene_gltf2.get_format_items(s,bpy.context)]
    enum_choices[name]=choices
    assert value in choices,(name,value,choices)
print('CURRENT_CONTEXT_EXPORT_ENUMS',json.dumps(enum_choices),flush=True)
inventory=json.loads(read_path(f'evidence/{version}/runtime_inventory.json').read_text())
with native.open('rb') as stream:native_hash=hashlib.file_digest(stream,'sha256').hexdigest()
assert inventory['version']==version and inventory['native_sha256']==native_hash
assert not inventory['photo_missing_nodes']
target=write_path(f'web/assets/{version}_context_delta.glb')
manifest_path=write_path(f'web/assets/{version}_context_delta.json')
expected_path=write_path(f'evidence/{version}/context_delta_expected.npz')
pending=target.with_name(target.stem+'.pending.glb')
assert not any(p.exists() for p in [target,manifest_path,expected_path,pending]), 'Keep previous evidence; do not overwrite an export attempt.'
source={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
current={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
assert set(source)==set(current)=={r['node'] for r in inventory['photo']}
changed=[];empty=[];arrays={};geometry=[]
for row in inventory['photo']:
    key=row['node'];ob=current[key];origin=source[key]
    assert ob.name==row['object'] and ob.parent is None and not ob.constraints and not ob.modifiers
    assert len(ob.data.polygons)==row['faces']
    assert ob.matrix_basis==origin.matrix_basis
    assert [slot.material for slot in ob.material_slots]==[slot.material for slot in origin.material_slots]
    if not row['changed']:
        assert ob.data is origin.data or mesh_digest(ob.data)==mesh_digest(origin.data)
        continue
    assert mesh_digest(ob.data)['sha256']==row['current_mesh_sha256']
    if not len(ob.data.polygons):
        empty.append(key);continue
    assert len(ob.data.uv_layers)==1 and all(len(p.vertices)==3 for p in ob.data.polygons)
    uv=ob.data.uv_layers.active;positions=[];coordinates=[]
    for face in ob.data.polygons:
        tri=[];tex=[]
        for vertex,loop in zip(face.vertices,face.loop_indices):
            p=ob.matrix_basis@ob.data.vertices[vertex].co
            tri.append([p.x,p.z,-p.y])
            u,v=uv.data[loop].uv;tex.append([u,1-v])
        positions.append(tri);coordinates.append(tex)
    arrays['node_'+key+'_positions']=np.asarray(positions,dtype=np.float64)
    arrays['node_'+key+'_uv']=np.asarray(coordinates,dtype=np.float64)
    geometry.append(dict(node=key,native_object=ob.name,triangles=len(positions),mesh_sha256=row['current_mesh_sha256']))
    changed.append(ob)
assert sorted(empty)==sorted(inventory['photo_empty_nodes'])
assert len(changed)+len(empty)==len(inventory['photo_changed_nodes'])

selection=[ob for ob in bpy.context.selected_objects]
active=bpy.context.view_layer.objects.active
temporary=bpy.data.collections.new('TEMP_CURRENT_CONTEXT_DELTA');s.collection.children.link(temporary)
copies=[];native_stat=native.stat()
try:
    for ob in bpy.context.selected_objects:ob.select_set(False)
    for ob in changed:
        dup=bpy.data.objects.new('RT_'+ob.name,ob.data)
        temporary.objects.link(dup);copies.append(dup)
        dup.matrix_world=ob.matrix_basis.copy()
        dup['native_object']=ob.name;dup['source_node']=str(ob['source_node']);dup['construction_version']=version
        dup.select_set(True)
    bpy.context.view_layer.update()
    result=bpy.ops.export_scene.gltf(filepath=str(pending),export_format='GLB',use_selection=True,
        export_extras=True,export_yup=True,export_apply=False,export_materials='NONE',
        export_texcoords=True,export_normals=True,export_tangents=False,export_cameras=False,
        export_lights=False,export_animations=False)
    assert 'FINISHED' in result and pending.is_file()
finally:
    for ob in copies:bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.collections.remove(temporary)
    for ob in selection:ob.select_set(True)
    bpy.context.view_layer.objects.active=active
assert native.stat().st_size==native_stat.st_size and native.stat().st_mtime_ns==native_stat.st_mtime_ns
# Export buffers are committed only after Blender has finished and temporary
# scene objects are gone. Verification remains explicitly false.
np.savez_compressed(expected_path,**arrays)
pending.rename(target)
report=dict(version=version,native=str(native),native_sha256=native_hash,export_enum_choices=enum_choices,
    file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    expected_arrays=str(expected_path),expected_arrays_sha256=hashlib.sha256(expected_path.read_bytes()).hexdigest(),
    changed_nodes=inventory['photo_changed_nodes'],empty_nodes=empty,geometry=geometry,
    base_source_nodes=2039,unchanged_source_nodes=2039-len(inventory['photo_changed_nodes']),
    native_unmodified=True,geometry_verified=False,texture_binding_verified=False,
    published_to_viewer=False,runtime_same_version_verified=False,natural_use_verified=False,
    texture_policy='Use the original photograph material for each source_node; this GLB contains geometry and exact UVs only.')
manifest_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
write_path(f'evidence/{version}/context_delta_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CURRENT_CONTEXT_EXPORTED',json.dumps({k:report[k] for k in ['version','file','bytes','sha256','unchanged_source_nodes']} |
      dict(changed_nodes=len(report['changed_nodes']),empty_nodes=len(empty),exported_meshes=len(changed))),flush=True)
if '--profile-leaves' in sys.argv:
    import runpy
    runpy.run_path(str(read_path('tools/blender_profile_leaf_instances.py')),run_name='__main__')
