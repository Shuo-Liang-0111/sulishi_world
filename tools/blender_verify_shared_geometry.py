"""Reopen check for shared native meshes; use before temporary render cleanup."""
from pathlib import Path
import hashlib
import json
import sys
import bpy

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'tools'))
from blender_geometry_fingerprint import mesh_digest, object_state

scene = bpy.context.scene
assert scene['version'] == 'G1_020r3'
evidence = root/'evidence/G1_020r3'
record = json.loads((evidence/'shared_geometry.json').read_text())
assert Path(bpy.data.filepath).resolve() == (root/record['native']).resolve()
assert hashlib.file_digest((root/record['base']).open('rb'), 'sha256').hexdigest() == record['base_sha256']
assert {obj.name: object_state(obj) for obj in scene.objects} == record['objects_before']
checked = {}
for name, mesh_name in record['shared_objects'].items():
    obj = bpy.data.objects[name]
    assert obj.library is None and obj.data.library is not None
    assert Path(bpy.path.abspath(obj.data.library.filepath)).resolve() == (root/record['base']).resolve()
    assert obj.data.name == mesh_name
    if mesh_name not in checked:
        actual = mesh_digest(obj.data)
        # JSON normalizes tuples to lists; normalize current UV metadata too.
        assert json.loads(json.dumps(actual)) == record['shared_meshes'][mesh_name], mesh_name
        checked[mesh_name] = actual['sha256']
missing = []
for image in bpy.data.images:
    if image.source == 'FILE' and not image.packed_file:
        path = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
        if not path.is_file():
            missing.append({'image': image.name, 'path': str(path)})
assert not missing, missing[:10]
result = {'version': scene['version'], 'objects': len(scene.objects),
          'linked_meshes_verified': len(checked), 'object_states_equal': True,
          'base_sha256_verified': True, 'missing_images': [],
          'visual_acceptance': False, 'natural_use_verified': False}
(evidence/'shared_geometry_reopen.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('SHARED_GEOMETRY_REOPEN', json.dumps(result), flush=True)
