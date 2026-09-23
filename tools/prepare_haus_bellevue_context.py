"""Survey identity and photographic ground support for the next connected streetfront."""
from pathlib import Path
import json,hashlib,struct
import numpy as np
from shapely.geometry import shape,Point,mapping
from inspect_platform_road_join import Surface,road

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/haus_bellevue';OUT.mkdir(exist_ok=True)
O=np.array([2683775,1246700,400]);paths={k:ROOT/'sources/features'/f'{k}.geojson' for k in ['av_bo_boflaeche_a','av_geb_gebaeudeadresse_t','bauten_dachmodell_3d','bauminventar','tbl_routennetz']}
layers={k:json.loads(p.read_text())['features'] for k,p in paths.items()}
side=next(f for f in layers['av_bo_boflaeche_a'] if f['properties']['objectid']==35946);g=shape(side['geometry'])
building=next(f for f in layers['av_bo_boflaeche_a'] if f['properties']['objectid']==13983)
addresses=[f for f in layers['av_geb_gebaeudeadresse_t'] if f['properties'].get('gwr_egid')==9011202]
surfaces=[f for f in layers['bauten_dachmodell_3d'] if f['properties'].get('egid')==9011202]
trees=[f for f in layers['bauminventar'] if shape(f['geometry']).distance(g)<.1]
walks=[f for f in layers['tbl_routennetz'] if f['properties'].get('fuss') and shape(f['geometry']).intersects(g.buffer(.5))]
adjacent=[f for f in layers['av_bo_boflaeche_a'] if f['properties'].get('status_txt')=='real' and shape(f['geometry']).distance(g)<.05 and f['id']!=side['id']]
support=[];manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());bottom=Surface(road)
x0,y0,x1,y1=g.bounds
for item in manifest['items']:
 m=np.array(item['mbs'])
 if Point(m[:2]).distance(g)>m[3]:continue
 raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
 t=(np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+m[:3]).reshape(-1,3,3)
 c=t.mean(axis=1);cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);area=np.linalg.norm(cross,axis=1)/2;vertical=abs(cross[:,2])/np.maximum(2*area,1e-12)
 ix=np.flatnonzero((c[:,0]>=x0)&(c[:,0]<=x1)&(c[:,1]>=y0)&(c[:,1]<=y1)&(c[:,2]>406)&(c[:,2]<414)&(vertical>.90)&(area>.008))
 for i in ix:
  if not g.buffer(-.10).contains(Point(c[i,:2])):continue
  rz,dist=bottom.sample(c[i,:2]-O[:2]);dz=float(c[i,2]-O[2]-rz)
  support.append({'point_ln02':c[i].tolist(),'above_nearest_road_m':dz,'nearest_road_distance_m':dist,'area_m2':float(area[i]),'normal_vertical':float(vertical[i]),'source_node':item['node'],'triangle_index':int(i),'initial_height_support':-.04<dz<.55})
good=np.array([s['point_ln02'] for s in support if s['initial_height_support']])-O
assert len(good)>=12,'Insufficient support: inspect source instead of inventing a level surface.'
A=np.c_[good[:,:2]-good[:,:2].mean(axis=0),np.ones(len(good))];coef=np.linalg.lstsq(A,good[:,2],rcond=None)[0]
for _ in range(12):
 residual=good[:,2]-A@coef;w=np.minimum(1,.045/np.maximum(abs(residual),1e-8));coef=np.linalg.lstsq(A*w[:,None],good[:,2]*w,rcond=None)[0]
record={'place':'Haus Bellevue, former Grandhotel Bellevue; not Odeon','egid':9011202,'origin':O.tolist(),'sidewalk':side,'building_footprint':building,'addresses':addresses,'building_surfaces':surfaces,'trees':trees,'walking_links':walks,'adjacent_surfaces':adjacent,'ground_samples':support,
 'robust_ground_fit':{'xy_center_local':good[:,:2].mean(axis=0).tolist(),'coefficients':coef.tolist(),'support_count':len(good),'residual_quantiles_m':np.quantile(good[:,2]-A@coef,[0,.1,.5,.9,1]).tolist(),'grade':float(np.linalg.norm(coef[:2]))},
 'sources':[{'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths.values()],
 'caution':'Initial photography-supported heights are inference. Address label points are not exact door geometry; roof-model GroundSurface is not a finished-floor survey. No construction accepted.'}
(OUT/'context.json').write_text(json.dumps(record,separators=(',',':'),ensure_ascii=False))
print(json.dumps({'sidewalk_m2':g.area,'trees':[f['id'] for f in trees],'walking_links':len(walks),'ground_fit':record['robust_ground_fit'],'adjacent':[(f['id'],f['properties']['art_txt']) for f in adjacent]}))
