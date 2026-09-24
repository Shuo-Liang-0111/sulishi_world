"""Show original I3S atlas pixels for the disputed road support faces.

Diagnostic crops only; no source image, geometry or scene is modified.
"""
from pathlib import Path
import json, struct
import numpy as np
from PIL import Image, ImageDraw

R = Path(__file__).resolve().parents[1]
D = R/'derived/bellevue/bridge_deck'
source = json.loads((D/'grade_evidence.json').read_text())
manifest = {str(i['node']): i for i in json.loads(
    (R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())['items']}
selected = [s for s in source['horizontal_photo_candidates']
            if s['kind'] == 'road' and s['xyz'][2] > 409.2 and s['area_m2'] > .3]
tiles = []
for s in selected:
    item = manifest[s['node']]
    raw = Path(item['geometry']).read_bytes()
    nv = struct.unpack_from('<I', raw)[0]
    uv = np.frombuffer(raw, dtype='<f4', count=nv*2,
                       offset=8+nv*12).reshape(-1, 3, 2)[s['face']]
    with Image.open(item['texture']) as im:
        atlas = im.convert('RGB')
    pixels = uv*np.array(atlas.size)
    lo = np.maximum(0, np.floor(pixels.min(0)).astype(int)-8)
    hi = np.minimum(np.array(atlas.size), np.ceil(pixels.max(0)).astype(int)+8)
    crop = atlas.crop((*lo, *hi))
    ImageDraw.Draw(crop).line([tuple(p-lo) for p in pixels] + [tuple(pixels[0]-lo)],
                              fill=(255, 210, 0), width=2)
    crop.thumbnail((330, 246))
    tile = Image.new('RGB', (344, 292), (240, 240, 240))
    tile.paste(crop, ((344-crop.width)//2, 40+(246-crop.height)//2))
    draw = ImageDraw.Draw(tile)
    draw.text((6, 5), f"{s['node']}:{s['face']}  Z {s['xyz'][2]:.3f}m", fill='black')
    draw.text((6, 21), f"area {s['area_m2']:.2f}m2; original source crop", fill='black')
    tiles.append(tile)
sheet = Image.new('RGB', (344*4, 292*((len(tiles)+3)//4)), (220, 220, 220))
for i, tile in enumerate(tiles):
    sheet.paste(tile, ((i % 4)*344, (i//4)*292))
sheet.save(D/'road_support_atlas.png')
(D/'road_support_atlas_index.json').write_text(json.dumps(selected, indent=2), encoding='utf-8')
print(json.dumps(dict(faces=len(tiles),file=str(D/'road_support_atlas.png'))))
