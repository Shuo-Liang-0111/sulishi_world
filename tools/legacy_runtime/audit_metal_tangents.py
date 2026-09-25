import json,struct,numpy as np
from pathlib import Path
b=Path('web/assets/G1_006r1_bellevue.glb').read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);binary=b[28+n:]
ids=[i for i,m in enumerate(j['materials']) if 'KHR_materials_anisotropy' in m.get('extensions',{})]
def arr(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];d={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];c={'VEC2':2,'VEC3':3,'VEC4':4,'SCALAR':1}[a['type']];return np.frombuffer(binary,dtype=d,count=a['count']*c,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,c)
bad=[]
for m in j['meshes']:
 for p in m['primitives']:
  if p.get('material') not in ids:continue
  t=arr(p['attributes']['TANGENT']);normal=arr(p['attributes']['NORMAL']);bad.append({'name':m['name'],'nan':int((~np.isfinite(t)).sum()),'minTangentNorm':float(np.linalg.norm(t[:,:3],axis=1).min()),'parallelNormals':int((abs(np.sum(t[:,:3]*normal,axis=1))>.99).sum())})
print(json.dumps(bad))
Path('evidence/G1_006r1/tangent_attribute_audit.json').write_text(json.dumps(bad,indent=2))
