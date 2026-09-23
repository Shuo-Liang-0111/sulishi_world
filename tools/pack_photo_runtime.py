"""Bundle the small initial textures to avoid thousands of simultaneous HTTP fetches."""
from pathlib import Path
import json,struct,copy
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'web/assets'
j=json.loads((ASSETS/'G1_004r2_photo_stream.gltf').read_text())
binary=bytearray((ASSETS/'G1_004r2_photo_geometry.bin').read_bytes())
for im in j['images']:
    data=(ASSETS/im.pop('uri')).read_bytes()
    while len(binary)%4:binary.append(0)
    im['bufferView']=len(j['bufferViews']);im['mimeType']='image/jpeg'
    j['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)})
    binary.extend(data)
while len(binary)%4:binary.append(0)
j['buffers']=[{'byteLength':len(binary)}]
js=json.dumps(j,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
target=ASSETS/'G1_004r2_photo_stream.glb'
with target.open('wb') as f:
    f.write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(binary)))
    f.write(struct.pack('<II',len(js),0x4E4F534A));f.write(js)
    f.write(struct.pack('<II',len(binary),0x004E4942));f.write(binary)
manifest=json.loads((ASSETS/'current.json').read_text());manifest['photo_stream_gltf']=target.name
manifest['texture_streaming']['initial_textures_bundled']=True
(ASSETS/'current.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'runtime_glb':target.name,'bytes':target.stat().st_size,'initial_images':len(j['images'])}))
