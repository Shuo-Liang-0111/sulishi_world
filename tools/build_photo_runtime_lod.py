"""Distance-dependent texture cache from the Blender GLB; original pixels remain available.

Only reference-texture sampling levels change. Geometry, UVs and world transforms are copied.
"""
from pathlib import Path
import json,struct,io,hashlib
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'web/assets'
source=ASSETS/'G1_004r2_photo.glb'
with source.open('rb') as f:
    magic,version,total=struct.unpack('<4sII',f.read(12))
    length,tag=struct.unpack('<II',f.read(8));gltf=json.loads(f.read(length))
    length,tag=struct.unpack('<II',f.read(8));binary=f.read(length)
assert magic==b'glTF' and version==2
old_views=gltf['bufferViews']
used={a['bufferView'] for a in gltf['accessors'] if 'bufferView' in a}
for a in gltf['accessors']:
    if 'sparse' in a:
        used.update(a['sparse'][k]['bufferView'] for k in ['indices','values'])
new_binary=bytearray();new_views=[];remap={}
for old_index in sorted(used):
    view=old_views[old_index];offset=view.get('byteOffset',0)
    while len(new_binary)%4:new_binary.append(0)
    remap[old_index]=len(new_views)
    new_views.append({**view,'buffer':0,'byteOffset':len(new_binary)})
    new_binary.extend(binary[offset:offset+view['byteLength']])
for a in gltf['accessors']:
    if 'bufferView' in a:a['bufferView']=remap[a['bufferView']]
    if 'sparse' in a:
        for k in ['indices','values']:a['sparse'][k]['bufferView']=remap[a['sparse'][k]['bufferView']]
folder=ASSETS/'photo_lod'
for level in ['128','256','full']:(folder/level).mkdir(parents=True,exist_ok=True)
def texture(item):
    i,image=item;view=old_views[image['bufferView']];offset=view.get('byteOffset',0)
    data=binary[offset:offset+view['byteLength']]
    ext='jpg' if image['mimeType']=='image/jpeg' else 'png'
    full=folder/'full'/f'{i}.{ext}';full.write_bytes(data)
    with Image.open(io.BytesIO(data)) as src:
        dimensions=src.size
        for level in [128,256]:
            thumb=src.convert('RGB');thumb.thumbnail((level,level),Image.Resampling.LANCZOS)
            thumb.save(folder/str(level)/f'{i}.jpg',quality=95,subsampling=0)
    return {'index':i,'width':dimensions[0],'height':dimensions[1],
            'full':f'photo_lod/full/{i}.{ext}','medium':f'photo_lod/256/{i}.jpg',
            'low':f'photo_lod/128/{i}.jpg','full_sha256':hashlib.sha256(data).hexdigest()}
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(texture,enumerate(gltf['images'])))
for image,rec in zip(gltf['images'],records):
    image.pop('bufferView',None);image.pop('mimeType',None);image['uri']=rec['low']
for material in gltf['materials']:
    ti=material['pbrMetallicRoughness']['baseColorTexture']['index']
    source_i=gltf['textures'][ti]['source']
    material.setdefault('extras',{})['runtime_texture_lod']=records[source_i]
gltf['bufferViews']=new_views
gltf['buffers']=[{'byteLength':len(new_binary),'uri':'G1_004r2_photo_geometry.bin'}]
gltf.setdefault('extras',{})['runtime_note']='Original geometry and UVs; full source texture near the camera, lower mip sampling at distance.'
(ASSETS/'G1_004r2_photo_geometry.bin').write_bytes(new_binary)
(ASSETS/'G1_004r2_photo_stream.gltf').write_text(json.dumps(gltf,separators=(',',':')),encoding='utf-8')
manifest=json.loads((ASSETS/'current.json').read_text())
manifest['photo_stream_gltf']='G1_004r2_photo_stream.gltf'
manifest['texture_streaming']={'full_visible_budget':72,'medium_visible_budget':96,'low_max_dimension':128,
                               'full_textures_preserved':True,'geometry_decimated':False}
(ASSETS/'current.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
report={'source':source.name,'geometry_bytes':len(new_binary),'images':len(records),
        'accessor_count':len(gltf['accessors']),'geometry_decimated':False,
        'full_texture_bytes_unchanged':True,'textures':records}
(ROOT/'evidence/G1_004r2/runtime_lod.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='textures'}))
