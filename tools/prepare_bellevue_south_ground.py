"""Survey support for the next continuous sidewalk, using already cached data."""
from pathlib import Path
import json,struct,numpy as np,hashlib
from shapely.geometry import shape,Point
from inspect_platform_road_join import Surface,road,origin
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_context';D.mkdir(exist_ok=True)
av=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features'];f=next(f for f in av if f['id']=='av_bo_boflaeche_a.3573');g=shape(f['geometry']);O=np.array([2683775,1246700,400]);rs=Surface(road)
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());samples=[]
for item in manifest['items']:
 m=np.array(item['mbs'])
 if Point(m[:2]).distance(g)>m[3]:continue
 raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0];t=(np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+m[:3]).reshape(-1,3,3);c=t.mean(axis=1);normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(normal,axis=1)
 inds=np.flatnonzero((c[:,2]>407.4)&(c[:,2]<409.7)&(abs(normal[:,2])>.88*np.maximum(length,1e-12))&(length>.015))
 for i in inds:
  if not g.buffer(-.12).covers(Point(c[i,:2])):continue
  rz,dist=rs.sample(c[i,:2]-O[:2]);dz=c[i,2]-400-rz
  samples.append({'world_xyz':c[i].tolist(),'source_node':item['node'],'triangle':int(i),'area_m2':float(length[i]/2),'road_distance_m':dist,'above_road_m':float(dz),'accepted_support':bool(-.08<dz<.55)})
pts=np.array([x['world_xyz'] for x in samples if x['accepted_support']])-O
assert len(pts)>20,(len(samples),len(pts))
# Equal spatial weight: dense tessellation around a tree must not dominate grade.
cells={}
for p in pts:cells.setdefault(tuple(np.floor(p[:2])),[]).append(p)
pts=np.array([np.median(v,axis=0) for v in cells.values()]);A=np.c_[pts[:,:2],np.ones(len(pts))];coef=np.linalg.lstsq(A,pts[:,2],rcond=None)[0]
for _ in range(12):
 residual=pts[:,2]-A@coef;w=np.minimum(1,.06/np.maximum(abs(residual),1e-7));coef=np.linalg.lstsq(A*w[:,None],pts[:,2]*w,rcond=None)[0]
trees=[x for x in json.loads((R/'sources/features/bauminventar.geojson').read_text(encoding='utf-8'))['features'] if g.covers(Point(x['geometry']['coordinates']))]
facilities=[]
for p in (R/'sources/features/vbz').glob('*.geojson'):
 for x in json.loads(p.read_text())['features']:
  geom=shape(x['geometry'])
  if geom.geom_type in ['Point','MultiPoint'] and geom.distance(g)<1:facilities.append(x)
edge=[]
for st in np.arange(0,g.exterior.length,1):
 xy=np.array(g.exterior.interpolate(st).coords[0])-O[:2];rz,dist=rs.sample(xy)
 if dist<.55:edge.append({'local_xy':xy.tolist(),'road_z':rz,'plane_z':float(np.r_[xy,1]@coef),'above_road':float(np.r_[xy,1]@coef-rz)})
report={'source_id':f['id'],'area_m2':g.area,'height_candidates':len(samples),'spatial_support_cells':len(pts),'plane_local':coef.tolist(),'plane_slope':float(np.linalg.norm(coef[:2])),'residual_quantiles_m':np.quantile(pts[:,2]-A@coef,[0,.1,.5,.9,1]).tolist(),'tree_count':len(trees),'nearby_vbz_points':len(facilities),'road_edge_height_quantiles':np.quantile([x['above_road'] for x in edge],[0,.1,.5,.9,1]).tolist(),'basis':'Existing AV3573 plan and original I3S ground candidates constrained by constructed neighboring roads. Grade is an inference, not a new height survey. No scene altered yet.','accepted':False}
(D/'ground_support.json').write_text(json.dumps({'report':report,'av':f,'samples':samples,'support_local':pts.tolist(),'trees':trees,'facilities':facilities,'road_edge':edge,'origin':O.tolist()},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))

