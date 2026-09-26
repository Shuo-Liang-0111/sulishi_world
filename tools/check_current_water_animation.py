"""Compare actual current GLB morph targets and times against current native samples."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.spatial import cKDTree
from inspect_glb import GLB
from workspace_paths import read_path, write_path

version = 'G1_027r15'
reference = json.loads(read_path(f'evidence/{version}/current_water_reference.json').read_text())
path = Path(reference['array_file'])
assert hashlib.sha256(path.read_bytes()).hexdigest() == reference['array_sha256']
source = np.load(path, allow_pickle=False)
manifest = json.loads(read_path(f'web/assets/{version}_current_r01/manifest.json').read_text())
assert manifest['native_sha256'] == reference['native_sha256']
chunks = [x for x in manifest['chunks'] if x['contains_native_water_animation']]
assert len(chunks) == 1
chunk = chunks[0]
glb_path = read_path(f'web/assets/{version}_current_r01/'+chunk['file'])
with glb_path.open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == chunk['sha256']
glb = GLB(glb_path)
doc = glb.doc
nodes = [(i, n) for i, n in enumerate(doc['nodes']) if n.get('extras', {}).get('native_object') == reference['object']]
assert len(nodes) == 1
node_index, node = nodes[0]
mesh = doc['meshes'][node['mesh']]
R = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0.]])
basis = source['basis'] @ R.T
delta = (source['ripple'].astype(float)-source['basis']) @ R.T
tree = cKDTree(basis)
primitives = []
for primitive in mesh['primitives']:
    assert len(primitive['targets']) == 1
    positions = glb.accessor(primitive['attributes']['POSITION'])
    target = primitive['targets'][0]
    offsets = glb.accessor(target['POSITION'])
    distance, ids = tree.query(positions)
    position_error = float(distance.max())
    offset_error = float(abs(offsets-delta[ids]).max())
    assert position_error < 1e-6 and offset_error < 1e-7
    assert 'NORMAL' in target
    primitives.append({'vertices': len(positions), 'basis_error_m': position_error, 'ripple_error_m': offset_error,
                       'normal_morph_present': True, 'normal_morph_visual_equivalence': False})
matches = [(animation, channel) for animation in doc.get('animations', []) for channel in animation['channels']
           if channel['target']['node'] == node_index and channel['target']['path'] == 'weights']
assert len(matches) == 1
animation, channel = matches[0]
sampler = animation['samplers'][channel['sampler']]
assert sampler.get('interpolation', 'LINEAR') == 'LINEAR'
times = glb.accessor(sampler['input']).ravel()
weights = glb.accessor(sampler['output']).ravel()
assert len(times) == len(weights) and np.all(np.diff(times) > 0)
assert abs(times[0]) < 1e-7
duration = (reference['end_frame']-reference['start_frame'])/reference['fps']
assert abs(times[-1]-duration) < 1e-6
errors = []
for item in reference['weights']:
    t = (item['frame']-reference['start_frame'])/reference['fps']
    actual = float(np.interp(t, times, weights))
    errors.append(abs(actual-item['weight']))
assert max(errors) < 1e-6
report = {'version': version, 'native_sha256': reference['native_sha256'], 'source_glb_sha256': chunk['sha256'],
          'primitives': primitives, 'animation': animation['name'], 'duration_seconds': float(times[-1]),
          'native_integer_frames_checked': len(errors), 'maximum_weight_error': max(errors),
          'loop_endpoints_match': bool(abs(weights[0]-weights[-1]) < 1e-7),
          'browser_animation_verified': False, 'water_material_verified': False, 'natural_use_verified': False}
glb.close()
write_path(f'evidence/{version}/current_water_roundtrip.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
