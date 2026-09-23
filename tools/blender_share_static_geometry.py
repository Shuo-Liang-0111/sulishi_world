"""Build a fully editable object hierarchy with immutable linked heavy meshes.

Run in a fresh, otherwise empty Blender process. The retained020r2 native is
the permanent geometry library; never overwrite or remove that dependency.
This is a storage change, not a claim of visual or natural-use improvement.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import bpy

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'tools'))
from blender_geometry_fingerprint import mesh_digest, object_state

base = root/'native/G1_020r2_utoquai_coating_working.blend'
target = root/'native/G1_020r3_linked_working.blend'
evidence = root/'evidence/G1_020r3'
expected_sha = '9de0f5d2d50cb599fb140e9837ade183fe6bd538e06f879889299a858d19ca13'
assert not bpy.data.filepath, 'Use --factory-startup, not an open native file'
assert not target.exists(), 'Never overwrite a retained checkpoint'
assert shutil.disk_usage(root).free > 900_000_000
assert hashlib.file_digest(base.open('rb'), 'sha256').hexdigest() == expected_sha
evidence.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bootstrap = bpy.context.scene
bootstrap.name = '__EMPTY_STORAGE_BOOTSTRAP__'
bootstrap.world = None
bpy.data.batch_remove(ids=list(bpy.data.collections) + [w for w in bpy.data.worlds if w.users == 0])
with bpy.data.libraries.load(str(base), link=False) as (source, destination):
    assert 'Zurich_G1' in source.scenes
    destination.scenes = ['Zurich_G1']
scene = destination.scenes[0]
bpy.context.window.scene = scene
bpy.data.scenes.remove(bootstrap)
bpy.context.view_layer.update()
assert scene['version'] == 'G1_020r2' and len(scene.objects) == 9325
assert all(obj.library is None for obj in scene.objects)
objects_before = {obj.name: object_state(obj) for obj in scene.objects}
photo_collections = {'03_I3S_PHOTOGRAPHIC_REFERENCE', '04_RETAINED_PHOTO_CONTEXT'}
tree_prefixes = ('BE_TREE_', 'HB_TREE_', 'BS_TREE_', 'LM_TREE_')
candidates = [obj for obj in scene.objects if obj.type == 'MESH' and (
    any(c.name in photo_collections for c in obj.users_collection) or
    (obj.name.startswith(tree_prefixes) and obj.name.endswith(('_TWIGS', '_LEAVES'))))]
owners = {}
for obj in candidates:
    assert obj.data.library is None and obj.data.shape_keys is None
    owners.setdefault(obj.data.name, []).append(obj)
mesh_names = sorted(owners)
print('SHARE_STATIC_PREPARED', len(mesh_names), 'meshes', flush=True)

# Hash numerical attributes (including UVs, leaf colors and sharpness) before
# any replacement. Non-target datablocks remain local and untouched.
fingerprints = {}
for index, name in enumerate(mesh_names):
    fingerprints[name] = mesh_digest(owners[name][0].data)
    if index % 500 == 0:
        print('SHARE_BASELINE', index, flush=True)
candidate_set = set(candidates)
local_non_targets = {obj.name: obj.data for obj in scene.objects
                     if obj.type == 'MESH' and obj not in candidate_set}
with bpy.data.libraries.load(str(base), link=True, relative=True) as (source, destination):
    assert set(mesh_names) <= set(source.meshes)
    # Blender replaces destination entries with ID objects on context exit.
    # Pass a new list so our original source-name keys remain strings.
    destination.meshes = mesh_names[:]
linked = dict(zip(mesh_names, destination.meshes))
assert all(mesh is not None and mesh.library is not None for mesh in linked.values())
print('SHARE_LIBRARY_LOADED', flush=True)
for index, name in enumerate(mesh_names):
    mesh = linked[name]
    assert mesh_digest(mesh) == fingerprints[name], ('Linked geometry differs', name)
    old = owners[name][0].data
    for obj in owners[name]:
        materials = [slot.material for slot in obj.material_slots]
        obj.data = mesh
        assert len(obj.material_slots) == len(materials)
        for slot, material in zip(obj.material_slots, materials):
            slot.link = 'OBJECT'
            slot.material = material
        assert object_state(obj) == objects_before[obj.name], obj.name
    if old.use_fake_user:
        old.use_fake_user = False
    assert old.users == 0, ('Unexpected other local mesh user', name, old.users)
    bpy.data.meshes.remove(old)
    if index % 500 == 0:
        print('SHARE_VERIFIED', index, flush=True)
bpy.context.view_layer.update()
assert {obj.name: object_state(obj) for obj in scene.objects} == objects_before
assert all(bpy.data.objects[name].data == mesh for name, mesh in local_non_targets.items())
assert all(obj.library is None for obj in scene.objects)
assert all(slot.material is None or slot.material.library is None
           for obj in scene.objects for slot in obj.material_slots)
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects) == 2039

# Appending a scene may remap relative image paths. Resolve each dependency
# against its actual owning library; preserve encoded files and packed images.
missing = []
for image in bpy.data.images:
    if image.source != 'FILE' or image.packed_file:
        continue
    resolved = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
    if not resolved.is_file():
        missing.append({'image': image.name, 'path': str(resolved)})
    elif image.library is None:
        image.filepath = bpy.path.relpath(str(resolved), start=str(target.parent))
assert not missing, missing[:10]
libraries = list(bpy.data.libraries)
assert len(libraries) == 1 and Path(bpy.path.abspath(libraries[0].filepath)).resolve() == base.resolve()
libraries[0].filepath = bpy.path.relpath(str(base), start=str(target.parent))
scene['version'] = 'G1_020r3'
scene['shared_geometry_library'] = base.name
scene['shared_geometry_library_sha256'] = expected_sha
scene['storage_variant_of'] = 'G1_020r2'
manifest = {'version': scene['version'], 'base': str(base.relative_to(root)),
            'base_sha256': expected_sha, 'native': str(target.relative_to(root)),
            'geometry_library_is_required': True, 'shared_meshes': fingerprints,
            'shared_objects': {obj.name: obj.data.name for obj in candidates},
            'objects_before': objects_before, 'unchanged_local_mesh_objects': len(local_non_targets),
            'mesh_attributes_equal_before_save': True, 'image_dependencies_present': True,
            'native_saved': False, 'visual_acceptance': False, 'natural_use_verified': False}
path = evidence/'shared_geometry.json'
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
assert shutil.disk_usage(root).free > 800_000_000
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True, relative_remap=False)
manifest.update(native_saved=True, native_bytes=target.stat().st_size,
                native_sha256=hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(),
                source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('SHARE_STATIC_SAVED', json.dumps({k: manifest[k] for k in
      ['native', 'native_bytes', 'native_sha256', 'unchanged_local_mesh_objects']}), flush=True)
