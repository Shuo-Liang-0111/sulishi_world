"""Complete AV3573 ground, with inferred grade tied to existing roads and walks."""
from pathlib import Path
import json,math,numpy as np
from functools import lru_cache
from shapely.geometry import shape,Point,Polygon,box,mapping
from shapely.geometry.polygon import orient
from shapely.affinity import translate
from shapely.ops import unary_union,nearest_points
from shapely import constrained_delaunay_triangles
from scipy.ndimage import gaussian_filter
from inspect_platform_road_join import Surface,road
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_context';d=json.loads((D/'ground_support.json').read_text(encoding='utf-8'));O=np.array(d['origin']);g=orient(translate(shape(d['av']['geometry']),-O[0],-O[1]),1);co=np.array(d['report']['plane_local']);bottom=Surface(road)
cad=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features'];roads=unary_union([translate(shape(f['geometry']),-O[0],-O[1]) for f in cad if f['properties']['art_txt']=='befestigt.Strasse_Weg.Strasse' and shape(f['geometry']).distance(shape(d['av']['geometry']))<1]);edge=g.exterior.intersection(roads.buffer(.003));curb=g.intersection(edge.buffer(.20,join_style=2));ramps=[]
for f in json.loads((R/'sources/features/tbl_routennetz.geojson').read_text())['features']:
 cross=translate(shape(f['geometry']),-O[0],-O[1]).intersection(g.exterior)
 if cross.geom_type!='Point' or cross.distance(edge)>.1:continue
 st=g.exterior.project(cross);ss=[]
 for ds in np.linspace(-1.5,1.5,25):
  q=np.array(g.exterior.interpolate((st+ds)%g.exterior.length).coords[0]);z,dist=bottom.sample(q)
  if Point(q).distance(edge)<.01 and dist<.10:ss.append([*q,z+.006])
 if len(ss)>1:ramps.append({'source':f['id'],'center_local':list(cross.coords[0]),'width_m_inferred':3.,'threshold':ss})
assert len(ramps)==4,len(ramps)
segments=np.array([p for r in ramps for p in zip(r['threshold'][:-1],r['threshold'][1:])]);sa=segments[:,0];sv=segments[:,1]-sa;ss=np.sum(sv[:,:2]**2,axis=1)
def initial_floor(x,y):
 p=np.array([x,y]);base=float(np.r_[p,1]@co);q=np.array(nearest_points(edge,Point(p))[0].coords[0]);rz,dist=bottom.sample(q);distance=np.linalg.norm(p-q);w=np.clip(1-distance/6.0,0,1);w=w*w*(3-2*w);z=base*(1-w)+(rz+.13)*w
 t=np.clip(np.sum((p-sa[:,:2])*sv[:,:2],axis=1)/ss,0,1);near=sa+sv*t[:,None];fan=float(np.min(near[:,2]+.045*np.linalg.norm(p-near[:,:2],axis=1)))
 return min(z,fan)
step=.5;gx=np.arange(math.floor(g.bounds[0])-1,math.ceil(g.bounds[2])+1.5,step);gy=np.arange(math.floor(g.bounds[1])-1,math.ceil(g.bounds[3])+1.5,step);grid=gaussian_filter(np.array([[initial_floor(x,y) for y in gy] for x in gx]),.55)
@lru_cache(maxsize=200000)
def floor(x,y):
 i=int(np.clip(math.floor((x-gx[0])/step),0,len(gx)-2));j=int(np.clip(math.floor((y-gy[0])/step),0,len(gy)-2));u=(x-gx[i])/step;v=(y-gy[j])/step
 if u+v<=1:return float(grid[i,j]*(1-u-v)+grid[i+1,j]*u+grid[i,j+1]*v)
 return float(grid[i+1,j+1]*(u+v-1)+grid[i,j+1]*(1-u)+grid[i+1,j]*(1-v))
pits=[]
for tree in d['trees']:
 xy=np.array(tree['geometry']['coordinates'])-O[:2];r=1.1 if tree['properties']['hoehe']>=18 else .9;pit=Point(xy).buffer(r,quad_segs=32).intersection(g.buffer(-.24));pits.append({'id':tree['id'],'xy_local':xy.tolist(),'radius_m_inferred':r,'soil_z_local':floor(*xy)-.032,'geometry_local':mapping(pit),'source':tree})
soil=unary_union([shape(p['geometry_local']) for p in pits]);masks={'asphalt':g.difference(curb).difference(soil),'curb_top':curb.difference(soil),'soil':soil};parts={k:[] for k in masks};parts['curb_face']=[];parts['curb_joint']=[]
def polygons(x):return [p for p in ([x] if x.geom_type=='Polygon' else getattr(x,'geoms',[])) if p.geom_type=='Polygon' and p.area>1e-10]
for i,x in enumerate(gx[:-1]):
 for j,y in enumerate(gy[:-1]):
  cell=box(x,y,x+step,y+step)
  if not g.intersects(cell):continue
  # Clip within the SAME planar grade triangles, avoiding skinny-face bilinear artifacts.
  for base in [Polygon([(x,y),(x+step,y),(x,y+step)]),Polygon([(x+step,y+step),(x,y+step),(x+step,y)])]:
   for key,mask in masks.items():
    for p in polygons(mask.intersection(base)):
     for tri in constrained_delaunay_triangles(p).geoms:
      vv=[[xx,yy,floor(xx,yy)+(-.032 if key=='soil' else 0)] for xx,yy in list(tri.exterior.coords)[:3]]
      if np.cross(np.array(vv[1])-vv[0],np.array(vv[2])-vv[0])[2]<0:vv.reverse()
      parts[key].append(vv)
ring=g.exterior;stations=sorted({0.,ring.length,*np.arange(0,ring.length,.30),*(ring.project(Point(p)) for p in ring.coords)})
for s0,s1 in zip(stations,stations[1:]):
 if s1-s0<1e-7:continue
 p,q=[np.array(ring.interpolate(s).coords[0]) for s in [s0,s1]]
 if Point((p+q)/2).distance(edge)>.01:continue
 a=[*p,floor(*p)];b=[*q,floor(*q)];c=[*q,bottom.sample(q)[0]-.018];dd=[*p,bottom.sample(p)[0]-.018];parts['curb_face'] += [[a,c,b],[a,dd,c]]
for st in np.arange(.34,ring.length,1.08):
 p=np.array(ring.interpolate(st).coords[0])
 if Point(p).distance(edge)>.01:continue
 t=np.array(ring.interpolate(st+.01).coords[0])-np.array(ring.interpolate(st-.01).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]]);vv=[[xx,yy,floor(xx,yy)+.0008] for xx,yy in [p-t*.0015,p+t*.0015,p+n*.199+t*.0015,p+n*.199-t*.0015]];parts['curb_joint'] += [[vv[0],vv[1],vv[2]],[vv[0],vv[2],vv[3]]]
uv={}
for key,tt in parts.items():
 uv[key]=[]
 for tri in tt:
  if key=='curb_face':
   ss=[ring.project(Point(v[:2])) for v in tri]
   if max(ss)-min(ss)>ring.length/2:ss=[s+ring.length if s<ring.length/2 else s for s in ss]
   uv[key].append([[s/(2/3),v[2]/(2/3)] for s,v in zip(ss,tri)])
  else:
   size=2.05 if key=='asphalt' else 1 if key=='soil' else 2/3;uv[key].append([[v[0]/size,v[1]/size] for v in tri])
top=np.array(parts['asphalt']+parts['curb_top']+parts['soil']);norm=np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0]);valid=abs(norm[:,2])>1e-10;slopes=np.linalg.norm(norm[valid,:2],axis=1)/abs(norm[valid,2]);area=abs(norm[:,2]).sum()/2
assert abs(area-g.area)<1e-5
assert slopes.max()<.09,slopes.max()
joins=[{'route':r['source'],'threshold_step_m':floor(*r['center_local'])-bottom.sample(np.array(r['center_local']))[0]} for r in ramps]
report={'source_id':d['av']['id'],'area_m2':g.area,'actual_mesh_area_m2':float(area),'street_curb_length_m':edge.length,'grade_quantiles':np.quantile(slopes,[.5,.9,.99,1]).tolist(),'ramps':ramps,'joins':joins,'preserved_building_holes':len(g.interiors),'tree_pits':len(pits),'basis':'Official AV3573 outline including its real building hole; existing photo-supported plane blended over6m to reconstructed road+13cm, four official walking connections with inferred3m-wide4.5% approach. Surface grade, curb profile, soil pits and material are inference, not surveyed accessibility approval.','accepted':False}
assert max(abs(x['threshold_step_m']) for x in joins)<.025,joins
(D/'platform_input.json').write_text(json.dumps({'report':report,'geometry_lv95':d['av']['geometry'],'parts':parts,'uv':uv,'pits':pits,'grade_grid':{'x':gx.tolist(),'y':gy.tolist(),'z':grid.tolist()}},separators=(',',':'),ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='ramps'}))
