"""Inspect original photogrammetric support, without treating water as floor."""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, shape

R = Path(__file__).resolve().parents[1]
D = R / 'derived/bellevue/quaibruecke_connection'
C = json.loads((D / 'context.json').read_text())
F = {f['id']: f for f in C['known_features']}
whole = shape(F['view_kuba_flaechen.477']['geometry'])
under = shape(F['av_ei_flaechenelement_a.39461']['geometry'])
manifest = json.loads((R / 'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
rows = []
diagnostics = []
for item in manifest['items']:
    m = np.array(item['mbs'])
    if Point(m[:2]).distance(whole) > m[3]:
        continue
    raw = Path(item['geometry']).read_bytes()
    nv = struct.unpack_from('<I', raw)[0]
    xyz = np.frombuffer(raw, dtype='<f4', count=nv*3, offset=8).reshape(-1, 3, 3) + m[:3]
    uv = np.frombuffer(raw, dtype='<f4', count=nv*2, offset=8+nv*12).reshape(-1, 3, 2)
    cent = xyz.mean(1)
    normal = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    size = np.linalg.norm(normal, axis=1)
    mask = (cent[:, 2] > 404.5) & (cent[:, 2] < 409.5) & (abs(normal[:, 2]) > .85*size) & (size > .08)
    indices = [int(i) for i in np.flatnonzero(mask) if whole.buffer(.5).covers(Point(cent[i, :2]))]
    if not indices:
        continue
    atlas = Image.open(item['texture']).convert('RGB')
    colors = np.array(atlas)
    for i in indices:
        pix = uv[i] * np.array(atlas.size)
        pc = np.clip(np.rint(pix.mean(0)).astype(int), 0, np.array(atlas.size)-1)
        rec = {'node': str(item['node']), 'source_face': i, 'centre': cent[i].tolist(),
               'area_m2': float(size[i]/2), 'rgb_centre': colors[pc[1], pc[0]].tolist(),
               'inside_underpass': under.buffer(-.25).covers(Point(cent[i, :2]))}
        rows.append(rec)
        if rec['inside_underpass'] and cent[i, 2] < 408:
            # Diagnostic crop only: the original source image is unchanged.
            lo = np.maximum(np.floor(pix.min(0)).astype(int)-5, 0)
            hi = np.minimum(np.ceil(pix.max(0)).astype(int)+5, np.array(atlas.size))
            crop = atlas.crop((*lo, *hi)).resize((300, 240))
            dr = ImageDraw.Draw(crop)
            pts = (pix-lo) / np.maximum(hi-lo, 1) * [300, 240]
            dr.line([tuple(p) for p in [*pts, pts[0]]], fill='magenta', width=2)
            tile = Image.new('RGB', (310, 280), 'white')
            tile.paste(crop, (5, 35))
            ImageDraw.Draw(tile).text((5, 5), f"{item['node']}:{i} Z={cent[i, 2]:.3f}", fill='black')
            diagnostics.append(tile)
if diagnostics:
    montage = Image.new('RGB', (310*len(diagnostics), 280), 'white')
    for i, tile in enumerate(diagnostics):
        montage.paste(tile, (i*310, 0))
    montage.save(D/'unclassified_support_atlas.png')
rows.sort(key=lambda r: r['centre'][1])
result = {'source_manifest_sha256': hashlib.sha256((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_bytes()).hexdigest(),
          'count': len(rows), 'samples': rows, 'classification': 'Unclassified; image review needed. Height alone is not a floor label.'}
(D/'photo_support_diagnosis.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'count': len(rows), 'underpass_candidates': [r for r in rows if r['inside_underpass'] and r['centre'][2] < 408],
                  'south_candidate_count': sum(r['centre'][1] < 1246814 for r in rows)}))
