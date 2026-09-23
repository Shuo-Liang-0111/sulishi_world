"""Independent reopen of the storage-only021r3 checkpoint, before render cleanup."""
from pathlib import Path
import hashlib
import json
import sys
import bpy

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest, object_state

s = bpy.context.scene
assert s['version'] == 'G1_021r3'
E = R/'evidence/G1_021r3'
record = json.loads((E/'shared_geometry.json').read_text())
assert Path(bpy.data.filepath).resolve() == (R/record['native']).resolve()
assert {o.name: object_state(o) for o in s.objects} == record['objects_before']
for name, digest in record['required_libraries'].items():
    assert hashlib.file_digest((R/'native'/name).open('rb'), 'sha256').hexdigest() == digest
assert {Path(bpy.path.abspath(lib.filepath)).name for lib in bpy.data.libraries} == set(record['required_libraries'])
for name, mesh_name in record['shared_objects'].items():
    o = bpy.data.objects[name]
    assert o.library is None and o.data.library is not None
    assert Path(bpy.path.abspath(o.data.library.filepath)).name == 'G1_021r2_riviera_continuous_working.blend'
    assert json.loads(json.dumps(mesh_digest(o.data))) == record['shared_meshes'][mesh_name]
missing = []
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        if not Path(bpy.path.abspath(im.filepath, library=im.library)).is_file():
            missing.append(im.name)
assert not missing
result = {'version': s['version'], 'objects': len(s.objects),
          'linked_meshes_verified': len(record['shared_objects']),
          'object_states_equal': True, 'required_library_sha256_verified': True,
          'missing_images': [], 'visual_acceptance': False, 'natural_use_verified': False}
(E/'shared_geometry_reopen.json').write_text(json.dumps(result, indent=2))
print('RIVIERA_SHARING_REOPEN', json.dumps(result), flush=True)
