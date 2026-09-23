"""Extract original near-horizontal bridge-deck supports for the023 fit.

Run before prepare_quaibruecke_build.py. These are interpreted photographic
surfaces, not a surveyed bridge structural profile.
"""
from pathlib import Path
import json,struct
import numpy as np
from shapely.geometry import shape,Point

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/quaibruecke_connection'
C=json.loads((D/'context.json').read_text())
bridge=shape(next(f['geometry'] for f in C['known_features'] if f['id']=='view_kuba_flaechen.502')).buffer(-1)
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
A=np.array([2683492.23,1246814.496]);T=np.array([-117.419,-31.436]);T/=np.linalg.norm(T);N=np.array([T[1],-T[0]])
rows=[]
for item in manifest['items']:
    m=np.array(item['mbs'])
    if Point(m[:2]).distance(bridge)>m[3]:continue
    raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
    tri=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3,3)+m[:3]
    cent=tri.mean(1);normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(normal,axis=1)
    mask=(cent[:,2]>408)&(cent[:,2]<411.5)&(abs(normal[:,2])>.94*area)&(area>.08)
    for i in np.flatnonzero(mask):
        if bridge.covers(Point(cent[i,:2])):
            rows.append([*(cent[i,:2]-A)@np.array([T,N]).T,cent[i,2],int(item['node']),int(i)])
np.savez_compressed(D/'deck_photo_support.npz',rows=np.array(rows))
print(json.dumps({'bridge_photo_support_faces':len(rows),'floor_candidates_used':False}))
