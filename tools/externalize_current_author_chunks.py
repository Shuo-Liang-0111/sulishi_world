"""Losslessly separate current GLB geometry and content-addressed native images.

Do not resize/re-encode images or change scene/material/accessor semantics.
Supports completed chunks during export, with explicit incomplete status.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import itertools
import json
import os
import numpy as np
from inspect_glb import GLB
from workspace_paths import read_path,write_path

p=argparse.ArgumentParser();p.add_argument('version');p.add_argument('--attempt',default='r01');p.add_argument('--partial',action='store_true')
p.add_argument('--reuse-verified',action='store_true',help='Reuse sealed receipts from this same immutable export; do not re-read unchanged multi-gigabyte prefixes.')
a=p.parse_args()
folder=read_path(f'web/assets/{a.version}_current_{a.attempt}')
manifest=json.loads((folder/'manifest.json').read_text());assert manifest['version']==a.version
if not a.partial:assert manifest['status']=='geometry_candidate_exported_material_review_pending'
runtime=folder/'runtime';runtime.mkdir(exist_ok=True);texture_dir=folder/'textures';texture_dir.mkdir(exist_ok=True)


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def atomic_json(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');os.replace(temp,path)


def remap_refs(value,mapping):
    if isinstance(value,list):
        for item in value:remap_refs(item,mapping)
    elif isinstance(value,dict):
        for key,item in value.items():
            if key=='bufferView':value[key]=mapping[item]
            else:remap_refs(item,mapping)


out={k:v for k,v in manifest.items() if k not in ['chunks','leaves']};out['chunks']=[];out['leaves']=manifest['leaves'];out['reused_verified_receipts']=[]
out['source_export_status']=manifest['status'];out['status']='lossless_packaging_in_progress'
for chunk in manifest['chunks']:
    source=folder/chunk['file']
    stem=source.stem;geometry=runtime/(stem+'.bin');gltf=runtime/(stem+'.gltf');receipt=runtime/(stem+'_receipt.json')
    if receipt.exists():
        row=json.loads(receipt.read_text());assert row['source_sha256']==chunk['sha256']
        assert source.stat().st_size==chunk['bytes'] and geometry.stat().st_size==row['geometry_bytes']
        assert row['geometry_view_byte_identity_verified'] and row['image_encoding_unchanged'] and gltf.is_file()
        for im in row['images']:assert (folder/im['file']).stat().st_size==im['bytes']
        if a.reuse_verified:
            out['reused_verified_receipts'].append(str(receipt.relative_to(folder)))
        else:
            assert sha(source)==chunk['sha256'] and sha(gltf)==row['sha256'] and sha(geometry)==row['geometry_sha256']
            for im in row['images']:assert sha(folder/im['file'])==im['sha256']
    else:
        assert sha(source)==chunk['sha256']
        assert not geometry.exists() and not gltf.exists(),'Review incomplete previous packaging before overwriting'
        raw=GLB(source);doc=copy.deepcopy(raw.doc)
        image_views={im['bufferView'] for im in doc.get('images',[])}
        assert all('bufferView' in im for im in doc.get('images',[]))
        mapping={};new_views=[];source_hash=hashlib.sha256()
        with geometry.open('wb') as f:
            for i,view in enumerate(doc['bufferViews']):
                if i in image_views:continue
                assert view['buffer']==0
                f.write(b'\0'*((-f.tell())%4));mapping[i]=len(new_views)
                new={**view,'buffer':0,'byteOffset':f.tell()};new_views.append(new)
                start=raw.base+view.get('byteOffset',0);end=start+view['byteLength']
                for off in range(start,end,4*1024*1024):
                    data=raw.raw[off:min(end,off+4*1024*1024)];f.write(data);source_hash.update(data)
            f.write(b'\0'*((-f.tell())%4))
        images=[]
        for im in doc.get('images',[]):
            view=doc['bufferViews'][im.pop('bufferView')];start=raw.base+view.get('byteOffset',0)
            data=raw.raw[start:start+view['byteLength']];digest=hashlib.sha256(data).hexdigest()
            suffix={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[im['mimeType']]
            texture=texture_dir/(digest+suffix)
            if not texture.exists():texture.write_bytes(data)
            assert sha(texture)==digest
            im['uri']='../textures/'+texture.name
            images.append({'file':'textures/'+texture.name,'sha256':digest,'bytes':len(data),'mimeType':im['mimeType']})
        remap_refs(doc,mapping);doc['bufferViews']=new_views
        doc['buffers']=[{'uri':geometry.name,'byteLength':geometry.stat().st_size}]
        actual_hash=hashlib.sha256()
        with geometry.open('rb') as f:
            for view in new_views:
                f.seek(view['byteOffset']);left=view['byteLength']
                while left:
                    data=f.read(min(left,4*1024*1024));assert data;actual_hash.update(data);left-=len(data)
        assert actual_hash.digest()==source_hash.digest()
        bounds=[];material_names=set();triangles=0
        for index,node in enumerate(raw.doc['nodes']):
            if 'mesh' not in node:continue
            matrix=raw.world(index)
            for primitive in raw.doc['meshes'][node['mesh']]['primitives']:
                acc=raw.doc['accessors'][primitive['attributes']['POSITION']]
                xyz=np.array(list(itertools.product(*zip(acc['min'],acc['max']))),dtype=np.float64)
                bounds.append(xyz@matrix[:3,:3].T+matrix[:3,3]);triangles+=raw.doc['accessors'][primitive['indices']]['count']//3
                if 'material' in primitive:material_names.add(raw.doc['materials'][primitive['material']]['name'])
        xyz=np.concatenate(bounds) if bounds else np.empty((0,3));raw.close()
        atomic_json(gltf,doc)
        row={'collection':chunk['collection'],'file':'runtime/'+gltf.name,'sha256':sha(gltf),'source_sha256':chunk['sha256'],
             'geometry_file':'runtime/'+geometry.name,'geometry_sha256':sha(geometry),'geometry_bytes':geometry.stat().st_size,
             'geometry_view_byte_identity_verified':True,'image_encoding_unchanged':True,'images':images,
             'bounds_yup':[xyz.min(0).tolist(),xyz.max(0).tolist()] if len(xyz) else None,
             'native_objects':chunk['native_objects'],'triangles':triangles,'materials':sorted(material_names),
             'contains_native_water_animation':chunk['contains_native_water_animation'],'material_conversion_verified':False}
        atomic_json(receipt,row)
    out['chunks'].append(row);atomic_json(folder/'runtime_manifest.json',out)
    print('CURRENT_CHUNK_EXTERNALIZED',gltf.name,row['geometry_bytes'],len(row['images']),flush=True)
out['status']='geometry_packaged_material_review_pending' if manifest['status']=='geometry_candidate_exported_material_review_pending' else 'partial_geometry_packaged'
out['unique_image_bytes']=sum(p.stat().st_size for p in texture_dir.iterdir() if p.is_file())
out['duplicated_embedded_image_bytes']=sum(im['bytes'] for c in out['chunks'] for im in c['images'])
atomic_json(folder/'runtime_manifest.json',out)
print(json.dumps({'status':out['status'],'chunks':len(out['chunks']),'unique_image_bytes':out['unique_image_bytes'],'original_glbs_retained':True}),flush=True)
