"""Broaden the observed bark transition with discrete exfoliating patches.

Derived working PBR maps: existing CC0 coarse bark plus the project's inferred
upper bark. These are not scans of the local trees. Originals stay untouched.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates, zoom

root = Path(__file__).resolve().parents[1]
output = root/'derived/materials/plane_trunk_patch'
assert not (output/'receipt.json').exists(), 'Preserve any previously generated material'
output.mkdir(parents=True, exist_ok=True)
n = 4096
rng = np.random.default_rng(60153)
u = np.arange(n, dtype=np.float32)[None, :]/n
z = (1-np.arange(n, dtype=np.float32)[:, None]/(n-1))*4.5


def noise(size, sigma):
    field = gaussian_filter(rng.standard_normal((size, size)).astype(np.float32), sigma, mode='wrap')
    field /= field.std()
    return zoom(field, n/size, order=1, mode='grid-wrap', grid_mode=True)


# A height-dependent *coverage*, not a single wavy boundary around the trunk:
# small pale islands appear among coarse bark, while coarse plates remain
# farther up. Fine patch boundaries retain a recognizable flaking structure.
patch = .76*noise(256, 4.8)+.19*noise(512, 3)+.045*noise(1024, 1.7)
threshold = 1.5-.95*z+.26*np.sin(2*np.pi*u*2+.7)+.20*noise(64, 2.5)
mask = np.clip((patch-threshold)/.095+.5, 0, 1)
mask = mask*mask*(3-2*mask)
base = np.clip((z-.12)/.36, 0, 1)
top = np.clip((z-3.3)/1.15, 0, 1)
mask = np.maximum(mask*base, top*top*(3-2*top))


def sample(path, tile, mode):
    source = np.asarray(Image.open(path).convert(mode), dtype=np.float32)/255
    yy = np.broadcast_to(np.mod(-z/tile, 1)*source.shape[0], (n, n))
    xx = np.broadcast_to(np.mod(u*2.5/tile, 1)*source.shape[1], (n, n))
    if source.ndim == 2:
        return map_coordinates(source, [yy, xx], order=1, mode='wrap')
    return np.stack([map_coordinates(source[:, :, c], [yy, xx], order=1, mode='wrap')
                     for c in range(3)], axis=-1)


coarse = root/'sources/textures/polyhaven/bark_platanus'
upper = root/'derived/materials/platanus_flaking'
files = []
source_hashes = {}
for role, suffix, mode in [('albedo', 'Diffuse', 'RGB'), ('roughness', 'Rough', 'L'),
                           ('normal_gl', 'nor_gl', 'RGB')]:
    a_path = coarse/f'bark_platanus_{suffix}_4k.png'
    b_path = upper/f'{role}.png'
    source_hashes[str(a_path.relative_to(root))] = hashlib.sha256(a_path.read_bytes()).hexdigest()
    source_hashes[str(b_path.relative_to(root))] = hashlib.sha256(b_path.read_bytes()).hexdigest()
    a = sample(a_path, 1.5, mode)
    b = sample(b_path, 2.4, mode)
    weight = mask if mode == 'L' else mask[:, :, None]
    if role == 'albedo':
        def linear(x):
            return np.where(x <= .04045, x/12.92, ((x+.055)/1.055)**2.4)
        values = linear(a)*(1-weight)+linear(b)*weight
        values = np.where(values <= .0031308, values*12.92,
                          1.055*np.maximum(values, 0)**(1/2.4)-.055)
    elif role == 'normal_gl':
        values = (a*2-1)*(1-weight)+(b*2-1)*weight
        values /= np.maximum(np.linalg.norm(values, axis=-1)[:, :, None], 1e-6)
        values = values*.5+.5
    else:
        values = a*(1-weight)+b*weight
    path = output/f'{role}.png'
    Image.fromarray(np.uint8(np.clip(values*255, 0, 255))).save(path, compress_level=6)
    files.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    del a, b, values
    print('BARK_PATCH_MAP', role, flush=True)
record = {'kind': 'inferred surface, not a local tree scan', 'resolution': [n, n],
          'physical_size_m': [2.5, 4.5], 'source_files_sha256': source_hashes,
          'source_files_untouched': True, 'files': files, 'seed': 60153,
          'reason': '020r2 south approach shows a coarse/pale cuff repeated at similar tree heights.',
          'method': 'Broad change in exfoliated coverage, with separate rough plates and pale islands.',
          'scene_visual_acceptance': False}
(output/'receipt.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('BARK_PATCH_COMPLETE', str(output), flush=True)
