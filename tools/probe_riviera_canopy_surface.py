"""Measure the actual ray-hit photographic surfaces before object-level repair.

This is a diagnostic, not an automatic city-wide vegetation segmenter. Original
source atlases and current working triangle UVs are used without image changes.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/G1_022r1'
cut = json.loads((ROOT / 'derived/bellevue/west_context/riviera_lower_canopy_cut.json').read_text())
working = {str(item['node']): item for item in cut['overrides']}
manifest = {str(item['node']): item for item in json.loads(
    (ROOT / 'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())['items']}

# Interior barycentric samples avoid extrapolation across atlas island borders.
weights = np.array([[a, b, 1-a-b] for a in np.linspace(.08, .84, 9)
                    for b in np.linspace(.08, .84, 9) if a+b <= .92])
cache = {}


def surface_arrays(node):
    if node in cache:
        return cache[node]
    rec = working[node]
    item = manifest[node]
    xyz = np.array(rec['vertices']).reshape(-1, 3, 3) + np.array(item['mbs'][:3])
    uv = np.array(rec['uv_source_v_unflipped']).reshape(-1, 3, 2)
    atlas = np.asarray(Image.open(item['texture']).convert('RGB')) / 255.
    tex = np.einsum('si,tij->tsj', weights, uv)
    x = np.clip(np.rint(tex[:, :, 0]*(atlas.shape[1]-1)).astype(int), 0, atlas.shape[1]-1)
    y = np.clip(np.rint(tex[:, :, 1]*(atlas.shape[0]-1)).astype(int), 0, atlas.shape[0]-1)
    rgb = atlas[y, x]
    red, green, blue = np.moveaxis(rgb, -1, 0)
    vegetation = (green > red*1.015) & (green > blue*1.17) & (green-blue > .025)
    fraction = vegetation.mean(axis=1)
    cache[node] = xyz, uv, fraction, np.median(rgb, axis=1)
    return cache[node]


if __name__ == '__main__':
    rays = json.loads((EVIDENCE / 'photo_residual_rays.json').read_text())
    records = []
    for ray in rays:
        if not ray['hits']:
            continue
        hit = ray['hits'][0]
        node, face = str(hit['node']), hit['face']
        xyz, uv, vegetation, rgb = surface_arrays(node)
        records.append({'camera': ray['camera'], 'pixel': ray['pixel'], 'node': node,
                        'face': face, 'vegetation_sample_fraction': float(vegetation[face]),
                        'median_srgb': rgb[face].tolist(),
                        'triangle_bounds_lv95': [xyz[face].min(0).tolist(), xyz[face].max(0).tolist()],
                        'nearest_tree': hit['nearest_inventory_trees'][0]})
    (EVIDENCE / 'canopy_surface_diagnosis.json').write_text(json.dumps(records, indent=2))
    print(json.dumps(records, indent=2))
