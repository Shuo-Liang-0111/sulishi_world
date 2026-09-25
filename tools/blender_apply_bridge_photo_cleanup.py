"""Remove only identified folded deck remnants, then save a new H checkpoint.

This does not alter the measured deck, trees, original photo collection, flags,
lamps or neighbouring buildings. Linked libraries and images must resolve to
exactly the same files after the cross-drive save.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state

scene = bpy.context.scene
assert scene['version']=='G1_027r2'
target = write_path('native/G1_027r3_bridge_edge_cleanup_working.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 1_000_000_000
input_path = read_path('derived/bridge_context/027r3_cleanup_input.json')
spec = json.loads(input_path.read_text())
before_objects = {o.name:object_state(o) for o in scene.objects}
before_data = {o.name:o.data.as_pointer() if o.data else None for o in scene.objects}
originals = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
assert len(originals.objects)==2039
original_ids = {o.name:o.data.as_pointer() for o in originals.objects}

def asset_paths():
    images = {im.name:str(Path(bpy.path.abspath(im.filepath,library=im.library)).resolve())
              for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file}
    libraries = {lib.name:str(Path(bpy.path.abspath(lib.filepath)).resolve()) for lib in bpy.data.libraries}
    fonts = {font.name:str(Path(bpy.path.abspath(font.filepath,library=font.library)).resolve())
             for font in bpy.data.fonts if font.filepath and font.filepath!='<builtin>' and not font.packed_file}
    return dict(images=images,libraries=libraries,fonts=fonts)

assets_before = asset_paths()
missing_before = [(kind,name,path) for kind,rows in assets_before.items() for name,path in rows.items() if not Path(path).is_file()]
assert not missing_before, missing_before[:10]
prepared = []
try:
    for row in spec['objects']:
        ob = bpy.data.objects[row['object']]
        assert ob.name.startswith('CTX_I3S_') and ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects.values()
        assert json.loads(json.dumps(mesh_digest(ob.data)))==row['before_fingerprint'],ob.name
        old = ob.data
        # sharp_face is Blender's built-in inverse of polygon.use_smooth, which
        # is copied below. Reject unknown custom shading/point data.
        assert all(attr.data_type=='FLOAT2' or attr.name.startswith('.') or attr.name in {'position','sharp_face'} for attr in old.attributes)
        remove = set(row['removed_faces'])
        kept = [poly for poly in old.polygons if poly.index not in remove]
        assert len(kept)==len(old.polygons)-len(remove)
        mesh = bpy.data.meshes.new('BRIDGE_EDGE_CLEAN_'+row['source_node'])
        mesh.from_pydata([v.co[:] for v in old.vertices],[],[tuple(p.vertices) for p in kept])
        mesh.update()
        for mat in old.materials:mesh.materials.append(mat)
        mesh.polygons.foreach_set('material_index',np.array([p.material_index for p in kept],dtype=np.int32))
        mesh.polygons.foreach_set('use_smooth',np.array([p.use_smooth for p in kept],dtype=np.bool_))
        for uv in old.uv_layers:
            new_uv = mesh.uv_layers.new(name=uv.name)
            new_uv.data.foreach_set('uv',np.array([uv.data[i].uv[:] for p in kept for i in p.loop_indices],dtype=np.float32).ravel())
            new_uv.active_render=uv.active_render;new_uv.active_clone=uv.active_clone
        mesh.uv_layers.active_index=old.uv_layers.active_index
        assert not mesh.validate(clean_customdata=False),ob.name
        prepared.append((row,ob,mesh))
    for row,ob,mesh in prepared:
        ob.data=mesh
        ob['bridge_edge_cleanup']='G1_027r3; identified folded deck component only'
    assert {o.name:object_state(o) for o in scene.objects}==before_objects
    changed={row['object'] for row in spec['objects']}
    assert all((o.data.as_pointer() if o.data else None)==before_data[o.name] for o in scene.objects if o.name not in changed)
    assert {o.name:o.data.as_pointer() for o in originals.objects}==original_ids
    record=dict(version='G1_027r3',base_version='G1_027r2',input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
        objects=[dict(object=row['object'],removed_faces=len(row['removed_faces']),after_fingerprint=mesh_digest(mesh)) for row,ob,mesh in prepared],
        source_originals_preserved=True,existing_authored_geometry_materials_cameras_lights_unchanged=True,
        flags_lamps_water_unmodified=True,visual_acceptance=False,natural_use_verified=False,runtime_exported=False)
    write_path('evidence/G1_027r3/construction.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    scene['version']='G1_027r3'
    scene['bridge_edge_cleanup_file']='derived/bridge_context/027r3_cleanup_input.json'
    bpy.context.view_layer.update()
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
    result=bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=True)
    assert 'FINISHED' in result and target.is_file()
    assets_after=asset_paths()
    assert assets_after==assets_before, 'Cross-drive reference identity changed; keep working pointer at the old native.'
    with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    checkpoint=json.loads(read_path('evidence/G1_027r2/checkpoint.json').read_text())
    checkpoint.update(version=scene['version'],native=target.relative_to(ROOT).as_posix(),native_bytes=target.stat().st_size,
        native_sha256=digest,objects=len(scene.objects),visual_acceptance=False,natural_use_verified=False,runtime_exported=False,
        native_fresh_reopen_verified=False,asset_paths=assets_after,geometry_globally_accepted=False,
        pre_save_checks=['Exact retained face vertices and UVs; original collection and other datablocks unchanged',
                         'Cross-drive library/image/font resolved paths unchanged'],
        bridge_edge_cleanup=record)
    write_path('evidence/G1_027r3/checkpoint.json').write_text(json.dumps(checkpoint,indent=2),encoding='utf-8')
    print('BRIDGE_EDGE_CANDIDATE_SAVED',json.dumps(dict(path=str(target),bytes=target.stat().st_size,sha256=digest,removed_faces=sum(r['removed_faces'] for r in record['objects']))),flush=True)
except Exception:
    # Unused prepared IDs can be removed safely; the old native is never saved.
    for _,ob,mesh in prepared:
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    raise
