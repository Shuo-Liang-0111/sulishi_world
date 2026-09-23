"""Photographic height support for complete surveyed west-platform and refuge polygons."""
import json,struct,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Point,Polygon
from inspect_platform_road_join import Surface,road,origin

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context'
IDS={459,454,455,36233,36234,36235,37084,37081,37269,106989}
features=[f for f in json.loads((ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features'] if int(f['properties']['objectid']) in IDS]
assert len(features)==len(IDS)
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());surface=Surface(road)
samples={f['id']:[] for f in features};polys={f['id']:shape(f['geometry']) for f in features}
for item in manifest['items']:
 m=np.array(item['mbs']);near=[k for k,g in polys.items() if Point(m[:2]).distance(g)<=m[3]]
 if not near:continue
 raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
 t=(np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+m[:3]).reshape(-1,3,3)
 c=t.mean(axis=1);cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(cross,axis=1)
 normal=np.abs(cross[:,2])/np.maximum(length,1e-12)
 for k in near:
  g=polys[k];x0,y0,x1,y1=g.bounds
  inds=np.flatnonzero((c[:,0]>=x0)&(c[:,0]<=x1)&(c[:,1]>=y0)&(c[:,1]<=y1)&(normal>.83)&(c[:,2]>405)&(c[:,2]<411)&(length>.006))
  for i in inds:
   if not g.buffer(-.08).contains(Point(c[i,:2])):continue
   rz,dist=surface.sample(c[i,:2]-origin);dz=float(c[i,2]-400-rz)
   samples[k].append({'point_ln02':c[i].tolist(),'above_road_m':dz,'road_nearest_distance_m':dist,'area_m2':float(length[i]/2),'normal_vertical':float(normal[i]),'source_node':item['node'],'triangle_index':int(i),'accepted_height_support':-.025<dz<.65})
records=[]
for f in features:
 ss=samples[f['id']];good=[s for s in ss if s['accepted_height_support']]
 heights=np.array([s['point_ln02'][2] for s in good]);up=np.array([s['above_road_m'] for s in good])
 rec={'id':f['id'],'area_m2':polys[f['id']].area,'geometry':f['geometry'],'source_properties':f['properties'],'samples':ss,'support_count':len(good),'z_quantiles_ln02':np.quantile(heights,[0,.1,.5,.9,1]).tolist() if len(good) else None,'upstand_quantiles_m':np.quantile(up,[0,.1,.5,.9,1]).tolist() if len(good) else None}
 records.append(rec)
result={'origin':[2683775,1246700,400],'surfaces':records,'road_input_sha256':hashlib.sha256((ROOT/'derived/bellevue/transport/road_input.json').read_bytes()).hexdigest(),'basis':'Original unmodified I3S near-horizontal triangle centroids within complete actual AV surface polygons; inferred-road-relative filters; not a survey of curb heights','accepted':False}
(OUT/'ground_support.json').write_text(json.dumps(result,separators=(',',':')))
print(json.dumps([{k:r[k] for k in ['id','area_m2','support_count','z_quantiles_ln02','upstand_quantiles_m']} for r in records]))
