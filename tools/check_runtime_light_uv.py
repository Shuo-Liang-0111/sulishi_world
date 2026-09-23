"""Compare actual exported light UVs with the native atlas coordinates."""
import json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];V='G1_015r3'
j=json.loads((R/'web/assets'/f'{V}_bellevue_runtime.gltf').read_text())
buffer=(R/'web/assets'/j['buffers'][0]['uri']).read_bytes()
def accessor(index):
    a=j['accessors'][index];v=j['bufferViews'][a['bufferView']]
    assert not v.get('byteStride')
    dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
    return np.frombuffer(buffer,dtype,a['count']*{'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']],v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],-1)
m=json.loads((R/'derived/runtime_occlusion'/V/'manifest.json').read_text())
uvs=np.load(R/m['uv_file'])
report={}
for name in ['SV_SOURCE_SOFFIT','SV_CERAMIC_FACE_TILES','BS_ASPHALT']:
    node=next(n for n in j['nodes'] if n.get('extras',{}).get('native_object')==name)
    records=[node] if 'mesh' in node else [j['nodes'][i] for i in node['children']]
    actual=np.concatenate([accessor(p['attributes']['TEXCOORD_1']) for n in records for p in j['meshes'][n['mesh']]['primitives']])
    rec=next(x for x in m['receivers'] if x['name']==name);native=uvs[rec['uv_key']]
    flip=native.copy();flip[:,1]=1-flip[:,1]
    def nearest_error(reference):
        from scipy.spatial import cKDTree
        return float(cKDTree(reference).query(actual)[0].max())
    report[name]={'exported_range':[actual.min(0).tolist(),actual.max(0).tolist()],
                  'native_range':[native.min(0).tolist(),native.max(0).tolist()],
                  'unflipped_max_error':nearest_error(native),'flipped_max_error':nearest_error(flip)}
report['native_view_settings']=json.loads((R/'web/assets'/f'{V}_bellevue.json').read_text())['native_view_settings']
areas=[]
receivers={x['name'] for x in m['receivers']}
for node in j['nodes']:
    name=node.get('extras',{}).get('native_object')
    if name not in receivers:continue
    records=[node] if 'mesh' in node else [j['nodes'][i] for i in node['children']]
    total=0
    for n in records:
        for p in j['meshes'][n['mesh']]['primitives']:
            uv=accessor(p['attributes']['TEXCOORD_1']);idx=accessor(p['indices']).reshape(-1,3)
            tri=uv[idx];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
            total+=float((np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])*.5).sum())
    areas.append((name,total))
report['uv_triangle_area_sum']=sum(x[1] for x in areas)
report['largest_uv_areas']=sorted(areas,key=lambda x:-x[1])[:12]
(R/'evidence'/V/'light_uv_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
