"""Losslessly share the eighteen stable Riviera crown meshes with retained021r2.

Run in a fresh Blender process. Old objects, materials, geometry, visibility and
the existing020r2 links are verified; no construction or visual improvement is
claimed by this storage-only checkpoint. Neither library may be removed.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import bpy

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest, object_state

BASE = R/'native/G1_021r2_riviera_continuous_working.blend'
TARGET = R/'native/G1_021r3_riviera_linked_working.blend'
E = R/'evidence/G1_021r3'
LIBRARIES = {
    'G1_020r2_utoquai_coating_working.blend': '9de0f5d2d50cb599fb140e9837ade183fe6bd538e06f879889299a858d19ca13',
    BASE.name: '6783e9ce386f6ae2c53e24bfa3a5ba9d61a3a6f0b5dac0eda0e1e48733e4b756',
}
assert not bpy.data.filepath and not TARGET.exists()
assert shutil.disk_usage(R).free > 650_000_000
for name, digest in LIBRARIES.items():
    assert hashlib.file_digest((R/'native'/name).open('rb'), 'sha256').hexdigest() == digest
E.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
bootstrap = bpy.context.scene
bootstrap.name = '__RIVIERA_STORAGE_BOOTSTRAP__'
bootstrap.world = None
bpy.data.batch_remove(ids=list(bpy.data.collections) + [w for w in bpy.data.worlds if w.users == 0])
with bpy.data.libraries.load(str(BASE), link=False) as (source, destination):
    assert 'Zurich_G1' in source.scenes
    destination.scenes = ['Zurich_G1']
s = destination.scenes[0]
bpy.context.window.scene = s
bpy.data.scenes.remove(bootstrap)
bpy.context.view_layer.update()
assert s['version'] == 'G1_021r2' and len(s.objects) == 9556
before = {o.name: object_state(o) for o in s.objects}
targets = [o for o in bpy.data.collections['34_RIVIERA_TREES'].objects
           if o.name.endswith(('_TWIGS', '_LEAVES'))]
assert len(targets) == 18 and all(o.data.library is None for o in targets)
owners = {o.data.name: o for o in targets}
assert len(owners) == 18
fingerprints = {name: mesh_digest(o.data) for name, o in owners.items()}
unchanged = {o.name: o.data for o in s.objects if o.type == 'MESH' and o not in targets}
old_links = {o.name: (o.data, o.data.library.filepath) for o in s.objects
             if o.type == 'MESH' and o.data.library is not None}
names = sorted(owners)
print('RIVIERA_SHARE_BASELINE', len(names), len(old_links), flush=True)
with bpy.data.libraries.load(str(BASE), link=True, relative=True) as (source, destination):
    assert set(names) <= set(source.meshes)
    destination.meshes = names[:]
for name, mesh in zip(names, destination.meshes):
    assert mesh is not None and mesh.library is not None
    assert mesh_digest(mesh) == fingerprints[name], name
    obj = owners[name]
    old = obj.data
    materials = [slot.material for slot in obj.material_slots]
    obj.data = mesh
    assert len(obj.material_slots) == len(materials)
    for slot, mat in zip(obj.material_slots, materials):
        slot.link = 'OBJECT'
        slot.material = mat
    assert object_state(obj) == before[obj.name]
    old.use_fake_user = False
    assert old.users == 0
    bpy.data.meshes.remove(old)
bpy.context.view_layer.update()
assert {o.name: object_state(o) for o in s.objects} == before
assert all(bpy.data.objects[n].data == mesh for n, mesh in unchanged.items())
assert all(bpy.data.objects[n].data == value[0] for n, value in old_links.items())
assert all(o.library is None for o in s.objects)
assert all(slot.material is None or slot.material.library is None
           for o in s.objects for slot in o.material_slots)
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects) == 2039
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or im.packed_file:
        continue
    path = Path(bpy.path.abspath(im.filepath, library=im.library)).resolve()
    if not path.is_file():
        missing.append(str(path))
    elif im.library is None:
        im.filepath = bpy.path.relpath(str(path), start=str(TARGET.parent))
assert not missing, missing[:5]
assert {Path(bpy.path.abspath(lib.filepath)).name for lib in bpy.data.libraries} == set(LIBRARIES)
for lib in bpy.data.libraries:
    path = Path(bpy.path.abspath(lib.filepath)).resolve()
    assert path.parent == TARGET.parent.resolve()
    lib.filepath = bpy.path.relpath(str(path), start=str(TARGET.parent))
s['version'] = 'G1_021r3'
s['storage_variant_of'] = 'G1_021r2'
s['riviera_crown_library'] = BASE.name
s['riviera_crown_library_sha256'] = LIBRARIES[BASE.name]
record = {'version': s['version'], 'native': str(TARGET.relative_to(R)),
          'required_libraries': LIBRARIES, 'shared_meshes': fingerprints,
          'shared_objects': {o.name: o.data.name for o in targets},
          'objects_before': before, 'previous_linked_objects_unchanged': len(old_links),
          'other_mesh_objects_unchanged': len(unchanged), 'native_saved': False,
          'visual_acceptance': False, 'natural_use_verified': False}
receipt = E/'shared_geometry.json'
receipt.write_text(json.dumps(record, indent=2), encoding='utf-8')
assert shutil.disk_usage(R).free > 600_000_000
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET), compress=True, relative_remap=False)
record.update(native_saved=True, native_bytes=TARGET.stat().st_size,
              native_sha256=hashlib.file_digest(TARGET.open('rb'), 'sha256').hexdigest())
receipt.write_text(json.dumps(record, indent=2), encoding='utf-8')
print('RIVIERA_SHARE_SAVED', record['native_bytes'], record['native_sha256'], flush=True)
