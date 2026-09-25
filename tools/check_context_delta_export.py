"""Compare actual exported triangles/UVs to native expectations, including winding.

Run with tools/python.ps1 tools/check_context_delta_export.py G1_027r7.
This does not validate runtime material binding, rendering, or walking.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import numpy as np
from scipy.spatial import cKDTree
from workspace_paths import read_path,write_path

parser=argparse.ArgumentParser();parser.add_argument('version');args=parser.parse_args()
version=args.version
manifest_path=read_path(f'web/assets/{version}_context_delta.json')
manifest=json.loads(manifest_path.read_text())
path=read_path('web/assets/'+manifest['file']);raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()==manifest['sha256']
magic,revision,total=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and revision==2 and total==len(raw)
offset=12;chunks=[]
while offset<len(raw):
    length,tag=struct.unpack_from('<II',raw,offset);offset+=8
    assert length%4==0 and offset+length<=len(raw)
    chunks.append((tag,raw[offset:offset+length]));offset+=length
assert len(chunks)==2 and [p[0] for p in chunks]==[0x4E4F534A,0x004E4942]
document=json.loads(chunks[0][1]);binary=chunks[1][1]
dtypes={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}


def accessor(index):
    a=document['accessors'][index]
    assert 'sparse' not in a and not a.get('normalized',False)
    view=document['bufferViews'][a['bufferView']];dtype=np.dtype(dtypes[a['componentType']]);width=widths[a['type']]
    assert view['buffer']==0
    offset=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',dtype.itemsize*width)
    assert offset+(a['count']-1)*stride+dtype.itemsize*width<=view.get('byteOffset',0)+view['byteLength']
    result=np.ndarray((a['count'],width),dtype=dtype,buffer=binary,offset=offset,
        strides=(stride,dtype.itemsize)).copy()
    assert np.isfinite(result).all()
    return result


parents={}
for i,node in enumerate(document['nodes']):
    for child in node.get('children',[]):
        assert child not in parents;parents[child]=i
matrices={}


def world_matrix(index,stack=()):
    assert index not in stack,'Node hierarchy cycle'
    if index in matrices:return matrices[index]
    node=document['nodes'][index]
    if 'matrix' in node:matrix=np.array(node['matrix']).reshape(4,4).T
    else:
        x,y,z,w=node.get('rotation',[0,0,0,1]);assert abs(x*x+y*y+z*z+w*w-1)<1e-5
        rotation=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                           [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                           [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        matrix=np.eye(4);matrix[:3,:3]=rotation@np.diag(node.get('scale',[1,1,1]));matrix[:3,3]=node.get('translation',[0,0,0])
    if index in parents:matrix=world_matrix(parents[index],stack+(index,))@matrix
    matrices[index]=matrix;return matrix


expected_file=read_path(manifest['expected_arrays'])
assert hashlib.sha256(expected_file.read_bytes()).hexdigest()==manifest['expected_arrays_sha256']
expected=np.load(expected_file,allow_pickle=False)
nodes={str(n.get('extras',{}).get('source_node')):(i,n) for i,n in enumerate(document['nodes']) if 'mesh' in n}
assert len(nodes)==sum('mesh' in n for n in document['nodes'])
assert set(nodes)=={r['node'] for r in manifest['geometry']}
assert not set(nodes)&set(manifest['empty_nodes'])
checks=[]
for row in manifest['geometry']:
    key=row['node'];index,node=nodes[key]
    assert node['extras']['native_object']==row['native_object'] and node['extras']['construction_version']==version
    actual_positions=[];actual_uv=[];matrix=world_matrix(index)
    for primitive in document['meshes'][node['mesh']]['primitives']:
        assert primitive.get('mode',4)==4 and 'material' not in primitive
        attributes=primitive['attributes'];assert 'TEXCOORD_0' in attributes
        positions=accessor(attributes['POSITION']).astype(np.float64)
        positions=np.column_stack((positions,np.ones(len(positions))))@matrix.T
        uv=accessor(attributes['TEXCOORD_0']).astype(np.float64)
        ids=accessor(primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(positions))
        assert len(ids)%3==0 and ids.max()<len(positions)
        actual_positions.append(positions[ids,:3].reshape(-1,3,3));actual_uv.append(uv[ids].reshape(-1,3,2))
    positions=np.concatenate(actual_positions);uv=np.concatenate(actual_uv)
    reference=expected['node_'+key+'_positions'];reference_uv=expected['node_'+key+'_uv']
    assert positions.shape==reference.shape==(row['triangles'],3,3)
    tree=cKDTree(positions.mean(1));candidates=tree.query_ball_point(reference.mean(1),.0001)
    used=set();max_position_error=0.;max_uv_error=0.
    for i,options in enumerate(candidates):
        found=None
        for j in options:
            if j in used:continue
            for shift in range(3):
                p=np.roll(positions[j],shift,axis=0);t=np.roll(uv[j],shift,axis=0)
                pe=float(np.max(abs(p-reference[i])));te=float(np.max(abs(t-reference_uv[i])))
                if pe<.0001 and te<.000002:
                    found=j;max_position_error=max(max_position_error,pe);max_uv_error=max(max_uv_error,te);break
            if found is not None:break
        assert found is not None,('Triangle/UV/winding changed',key,i,options)
        used.add(found)
    assert len(used)==len(positions)
    checks.append(dict(node=key,triangles=len(positions),max_world_position_error_m=max_position_error,max_uv_error=max_uv_error))
report=dict(version=version,glb=str(path),glb_sha256=manifest['sha256'],meshes=len(nodes),
    triangles=sum(r['triangles'] for r in checks),changed_nodes=len(manifest['changed_nodes']),
    empty_nodes=manifest['empty_nodes'],geometry_uv_winding_verified=True,
    checks=checks,texture_binding_verified=False,published_to_viewer=False,natural_use_verified=False)
write_path(f'evidence/{version}/context_delta_roundtrip.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','empty_nodes']} | dict(empty_nodes=len(manifest['empty_nodes'])),indent=2))
