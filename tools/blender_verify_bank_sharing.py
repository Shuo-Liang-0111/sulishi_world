"""Verify026 on a fresh load before any render-only scene preparation."""
from pathlib import Path
import hashlib
import json
import sys
import bpy

R = Path('F:/MyWorld/ZurichWorld')
sys.path.insert(0, str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest

s = bpy.context.scene
assert s['version'] in ['G1_026','G1_027','G1_027r1','G1_027r2']
E = R/'evidence'/s['version']
record = json.loads((E/'checkpoint.json').read_text())
native = Path(bpy.data.filepath).resolve()
assert native == (R/record['native']).resolve()
assert record['storage_sharing_applied'] and len(s.objects) == record['objects']
with native.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['native_sha256']
actual_libraries = {}
for lib in bpy.data.libraries:
    path = Path(bpy.path.abspath(lib.filepath)).resolve()
    assert path.parent == native.parent and path.is_file(), str(path)
    with path.open('rb') as stream:
        actual_libraries[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
assert actual_libraries == record['required_immutable_libraries']
verified = []
for name, mesh_name in record['shared_objects'].items():
    ob = bpy.data.objects[name]
    assert ob.type == 'MESH' and ob.data.name == mesh_name
    assert ob.data.library and Path(bpy.path.abspath(ob.data.library.filepath)).name == 'G1_025r1_bank_tree_replacement_working.blend'
    assert json.loads(json.dumps(mesh_digest(ob.data))) == record['shared_meshes'][mesh_name], name
    assert all(slot.link == 'OBJECT' and slot.material is not None for slot in ob.material_slots), name
    verified.append(name)
assert len(verified) == 24
missing = [im.name for im in bpy.data.images if im.source == 'FILE' and im.filepath
           and not im.packed_file and not Path(bpy.path.abspath(im.filepath, library=im.library)).is_file()]
assert not missing, missing
report = dict(version=s['version'], native_sha256=record['native_sha256'],
              libraries=actual_libraries, shared_objects=verified, missing_images=missing,
              objects=len(s.objects), all_numeric_mesh_attributes_equal=True,
              native_modified=False, visual_acceptance=False, runtime_equivalent=False)
(E/'sharing_reopen_verified.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BANK_SHARING_REOPEN_VERIFIED', len(verified), len(s.objects), flush=True)
