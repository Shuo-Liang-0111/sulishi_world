"""Lossless native positions for the second leaf representation candidate.

Keep the first affine candidate and its failed browser evidence. All input here
is the actual exported native arrays; no Blender file needs alteration.
"""
import hashlib
import json
import sys
import numpy as np
from workspace_paths import read_path,write_path

version=sys.argv[1]
assert version=='G1_027r15'
folder=f'web/assets/{version}_leaf_diagnostic/'
source=read_path(folder+'tree.json')
old=json.loads(source.read_text())
raw=read_path(folder+old['file']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==old['sha256']
arrays={}
for key,d in old['arrays'].items():
    data=raw[d['offset']:d['offset']+d['bytes']]
    assert hashlib.sha256(data).hexdigest()==d['sha256']
    if key!='instance_matrices':
        arrays[key]=np.frombuffer(data,dtype=d['dtype']).reshape(d['shape'])
positions=arrays['reference_positions'].reshape(-1,3)
width,height=old['normal_texture_dimensions']
texture=np.zeros((width*height,4),dtype=np.float32)
texture[:len(positions),:3]=positions
assert np.array_equal(texture[:len(positions),:3],positions)
arrays['exact_native_position_texture']=texture
blob=bytearray();description={}
for key,values in arrays.items():
    while len(blob)%4:blob.append(0)
    data=np.ascontiguousarray(values).tobytes()
    description[key]=dict(offset=len(blob),bytes=len(data),dtype=values.dtype.str,shape=list(values.shape),sha256=hashlib.sha256(data).hexdigest())
    blob.extend(data)
target=write_path(folder+'tree_exact.bin');meta=write_path(folder+'tree_exact.json')
assert not target.exists() and not meta.exists()
target.write_bytes(blob)
assert hashlib.sha256(target.read_bytes()).hexdigest()==hashlib.sha256(blob).hexdigest()
out={**old,'file':target.name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'arrays':description,
     'position_policy':'exact_native_texture','exact_position_float32_preserved':True,
     'source_affine_candidate_sha256':old['sha256'],
     'packed_attribute_bytes':sum(d['bytes'] for k,d in description.items() if not k.startswith('reference_')),
     'browser_verified':False,'full_runtime_published':False,
     'comparison_scope':'Exact saved-native positions and per-leaf normals through data textures; shared topology, UV and color pattern. Same Three.js standard material on both representations; no native subsurface/light equivalence claim.'}
out.pop('max_float32_affine_position_error_m')
meta.write_text(json.dumps(out,indent=2),encoding='utf-8')
write_path(f'evidence/{version}/leaf_exact_preparation.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(dict(file=str(meta),reference_bytes=out['reference_attribute_bytes'],packed_bytes=out['packed_attribute_bytes'],exact_positions=True)))
