"""Finish read-only current-native anchors, material semantics and water references."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import sys
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path, validate_native

scene = bpy.context.scene
version = scene['version']
assert version == 'G1_027r15'
native = validate_native(bpy.data.filepath)
initial_stat = native.stat()
with native.open('rb') as f:
    digest = hashlib.file_digest(f, 'sha256').hexdigest()
runpy.run_path(str(ROOT/'tools/blender_material_semantics.py'), run_name='__main__')
water = bpy.data.objects['F59_WATER_SURFACE']
assert not water.modifiers
keys = water.data.shape_keys
assert len(keys.key_blocks) == 2
basis, ripple = keys.key_blocks
assert ripple.relative_key == basis and not ripple.vertex_group and keys.use_relative
arrays = {}
for name, key in [('basis', basis), ('ripple', ripple)]:
    xyz = np.empty(len(key.data)*3, np.float32)
    key.data.foreach_get('co', xyz)
    arrays[name] = xyz.reshape(-1, 3)
action = keys.animation_data.action
start, end = [int(round(x)) for x in action.frame_range]
assert start == 1 and end == 81
old_frame, old_subframe = scene.frame_current, scene.frame_subframe
weights = []
try:
    for frame in range(start, end+1):
        scene.frame_set(frame)
        weights.append({'frame': frame, 'weight': ripple.value})
finally:
    scene.frame_set(old_frame, subframe=old_subframe)
path = write_path(f'evidence/{version}/current_water_reference.npz')
assert not path.exists()
np.savez_compressed(path, **arrays)
report = {'version': version, 'native_sha256': digest, 'process_id': os.getpid(),
    'object': water.name, 'action': action.name, 'start_frame': start, 'end_frame': end,
    'fps': scene.render.fps/scene.render.fps_base, 'weights': weights, 'original_frame_restored': old_frame,
    'array_file': str(path), 'array_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'default_weight_at_saved_frame': ripple.value, 'native_modified': False, 'runtime_animation_verified': False}
write_path(f'evidence/{version}/current_water_reference.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert native.stat().st_mtime_ns == initial_stat.st_mtime_ns and native.stat().st_size == initial_stat.st_size
with native.open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == digest
print('CURRENT_RUNTIME_COMPLETION_REFERENCES_READ_NOT_PUBLISHED', os.getpid(), flush=True)
