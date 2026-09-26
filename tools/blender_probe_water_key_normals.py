"""Read the shape-key normal source actually used by the installed glTF exporter."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path, validate_native

version = bpy.context.scene['version']
assert version == 'G1_027r15'
native = validate_native(bpy.data.filepath)
with native.open('rb') as f:
    digest = hashlib.file_digest(f, 'sha256').hexdigest()
reference = json.loads(read_path(f'evidence/{version}/current_water_reference.json').read_text())
assert digest == reference['native_sha256']
water = bpy.data.objects['F59_WATER_SURFACE']
mesh = water.data
assert not water.modifiers and len(mesh.shape_keys.key_blocks) == 2
basis, ripple = mesh.shape_keys.key_blocks
assert ripple.relative_key == basis
arrays = {'basis_loop_normals': np.asarray(basis.normals_split_get(), np.float32).reshape(-1, 3),
          'ripple_loop_normals': np.asarray(ripple.normals_split_get(), np.float32).reshape(-1, 3)}
xyz = np.empty(len(mesh.vertices)*3, np.float32)
mesh.vertices.foreach_get('co', xyz)
loops = np.empty(len(mesh.loops), np.int32)
mesh.loops.foreach_get('vertex_index', loops)
assert arrays['basis_loop_normals'].shape == arrays['ripple_loop_normals'].shape == (len(mesh.loops), 3)
path = write_path(f'evidence/{version}/current_water_key_normals.npz')
assert not path.exists()
np.savez_compressed(path, **arrays)
report = {'version': version, 'native_sha256': digest, 'process_id': os.getpid(), 'object': water.name,
          'normal_source': 'Actual Basis and ripple ShapeKey.normals_split_get, matching installed primitive_extract.py:1428-1477.',
          'mesh_positions_sha256': hashlib.sha256(xyz.tobytes()).hexdigest(),
          'loop_vertex_indices_sha256': hashlib.sha256(loops.tobytes()).hexdigest(),
          'loops': len(mesh.loops), 'vertices': len(mesh.vertices), 'array_file': str(path),
          'array_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'native_modified': False}
write_path(f'evidence/{version}/current_water_key_normals.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CURRENT_WATER_NATIVE_KEY_NORMALS_READ', len(mesh.loops), flush=True)
