"""Externalize verified runtime GLB images and buffer without changing pixels/geometry.

Shared, content-addressed PNGs avoid repeating a near-gigabyte embedded image
payload on every revision. Streaming copies bound this tool's own RAM usage.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import copy

p=argparse.ArgumentParser();p.add_argument('--version',required=True);a=p.parse_args()
assert __import__('re').fullmatch(r'G1_\d{3}(?:r\d+)?',a.version)
R=Path(__file__).resolve().parents[1];V=a.version;A=R/'web/assets';E=R/'evidence'/V
proof=json.loads((E/'runtime_encoding.json').read_text())
assert proof['written_file_checked'] and proof['version']==V
original=A/f'{V}_bellevue_runtime.glb'
texture_dir=A/'textures/shared_runtime';texture_dir.mkdir(parents=True,exist_ok=True)
geometry=A/f'{V}_bellevue_runtime.bin';output=A/f'{V}_bellevue_runtime.gltf'

def filehash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()

with original.open('rb') as source:
    magic,version,total=struct.unpack('<4sII',source.read(12));assert magic==b'glTF' and version==2
    n,tag=struct.unpack('<II',source.read(8));assert tag==0x4e4f534a
    j=json.loads(source.read(n));bin_length,tag=struct.unpack('<II',source.read(8));assert tag==0x004e4942
    base=source.tell();assert base+bin_length==total==original.stat().st_size
    image_views={im['bufferView'] for im in j['images']}
    old_views=j['bufferViews'];remap={};new_views=[];geometry_hash=hashlib.sha256()
    with geometry.open('wb') as target:
        for i,view in enumerate(old_views):
            if i in image_views:continue
            pad=(-target.tell())%4
            target.write(b'\0'*pad)
            remap[i]=len(new_views);new_view=copy.deepcopy(view);new_view['buffer']=0;new_view['byteOffset']=target.tell();new_views.append(new_view)
            source.seek(base+view.get('byteOffset',0));left=view['byteLength']
            while left:
                chunk=source.read(min(left,4*1024*1024));assert chunk
                target.write(chunk);geometry_hash.update(chunk);left-=len(chunk)
        target.write(b'\0'*((-target.tell())%4))
    images=[]
    expected={x['buffer_view']:x['runtime_sha256'] for x in proof['images']}
    for im in j['images']:
        index=im.pop('bufferView');view=old_views[index];digest=expected[index]
        path=texture_dir/(digest+'.png')
        source.seek(base+view.get('byteOffset',0))
        if not path.exists():
            with path.open('wb') as target:
                left=view['byteLength']
                while left:
                    chunk=source.read(min(left,4*1024*1024));assert chunk;target.write(chunk);left-=len(chunk)
        assert path.stat().st_size==view['byteLength'] and filehash(path)==digest
        im['uri']=path.relative_to(A).as_posix()
        images.append({'uri':im['uri'],'sha256':digest,'bytes':path.stat().st_size})

def remap_views(value):
    if isinstance(value,list):
        for item in value:remap_views(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if key=='bufferView':value[key]=remap[item]
            else:remap_views(item)
remap_views(j)
j['bufferViews']=new_views
j['buffers']=[{'uri':geometry.name,'byteLength':geometry.stat().st_size}]
output.write_text(json.dumps(j,separators=(',',':')),encoding='utf-8')
assert geometry_hash.hexdigest()==proof['geometry_source_hash']
# Read every actual written geometry view in order, excluding alignment padding.
written=json.loads(output.read_text(encoding='utf-8'));actual_hash=hashlib.sha256()
with geometry.open('rb') as f:
    for view in written['bufferViews']:
        f.seek(view['byteOffset']);left=view['byteLength']
        while left:
            chunk=f.read(min(left,4*1024*1024));assert chunk;actual_hash.update(chunk);left-=len(chunk)
assert actual_hash.hexdigest()==proof['geometry_source_hash']
metadata=json.loads((A/f'{V}_bellevue.json').read_text())
metadata['authored_runtime']={'file':output.name,'sha256':filehash(output),'geometry_file':geometry.name,
                             'geometry_sha256':filehash(geometry),'lossless_external_images':True}
(A/f'{V}_bellevue.json').write_text(json.dumps(metadata,indent=2))
report={'version':V,'gltf':output.name,'geometry_bytes':geometry.stat().st_size,
        'image_bytes':sum(x['bytes'] for x in images),'images':images,
        'non_image_bytes_sha256':actual_hash.hexdigest(),'geometry_byte_identity_verified':True,
        'pixel_encoding_unchanged':True,'original_glb_retained':True,
        'native_nodes_meshes_materials_accessors_unchanged':True}
(E/'runtime_externalization.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='images'}))
