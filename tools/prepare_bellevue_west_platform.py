"""Build a surveyed platform with photo-supported grade and explicitly inferred ramp profiles."""
import json,hashlib
from pathlib import Path
from functools import lru_cache
import numpy as np
from shapely.geometry import shape,Polygon,Point,box
from shapely.geometry.polygon import orient
from shapely.affinity import translate
from shapely import constrained_delaunay_triangles
from inspect_platform_road_join import Surface,road

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context';O=np.array([2683775,1246700,400])
support=json.loads((OUT/'ground_support.json').read_text());rec=next(r for r in support['surfaces'] if r['id'].endswith('.459'))
g=orient(translate(shape(rec['geometry']),-O[0],-O[1]),1);bottom=Surface(road)
pts=np.array([s['point_ln02'] for s in rec['samples'] if s['accepted_height_support']])-O
A=np.c_[pts[:,:2],np.ones(len(pts))];coef=np.linalg.lstsq(A,pts[:,2],rcond=None)[0]
for _ in range(8):
 residual=pts[:,2]-A@coef;weights=np.minimum(1,.07/np.maximum(abs(residual),1e-6));coef=np.linalg.lstsq(A*weights[:,None],pts[:,2]*weights,rcond=None)[0]
ramps=[]
# Actual footpath/AV-edge intersections. Profile lengths and widths are inference,
# not prescribed survey values or a claim of accessibility certification.
for route,p in [
 ('tbl_routennetz.10598',[2683529.3552356125,1246848.9067886157]),
 ('tbl_routennetz.28609',[2683533.8466414344,1246840.1687634508]),
 ('tbl_routennetz.13266',[2683568.8447562247,1246868.541879021])]:
 p=np.array(p)-O[:2];station=g.exterior.project(Point(p));threshold=[];distances=[]
 # Lower the actual curb arc, not an infinite line projected across the platform.
 # The adjoining fan inherits a bounded grade; the former narrow side flare
 # produced 27% crossfalls despite an apparently gentle longitudinal ramp.
 for ds in np.linspace(-1.5,1.5,17):
  xy=np.array(g.exterior.interpolate((station+ds)%g.exterior.length).coords[0]);rz,dist=bottom.sample(xy)
  threshold.append([*xy,rz+.005]);distances.append(dist)
 ramps.append({'route_id':route,'center_local':p.tolist(),'clear_width_m_inferred':3.0,'fan_grade_inferred':.045,'threshold_local':threshold,'road_sample_distance_max_m':max(distances)})

segments=np.array([pair for r in ramps for pair in zip(r['threshold_local'][:-1],r['threshold_local'][1:])])
sa=segments[:,0];sv=segments[:,1]-sa;slen2=np.sum(sv[:,:2]**2,axis=1)
@lru_cache(maxsize=70000)
def floor(x,y):
 p=np.array([x,y]);z=float(np.r_[p,1]@coef)
 t=np.clip(np.sum((p-sa[:,:2])*sv[:,:2],axis=1)/slen2,0,1)
 nearest=sa+sv*t[:,None];dist=np.linalg.norm(p-nearest[:,:2],axis=1)
 fan=float(np.min(nearest[:,2]+.045*dist))
 # A 12 mm smooth join avoids a sharp crease where the fan meets the supported
 # platform plane. It does not fabricate measured accessibility compliance.
 k=.012;h=max(k-abs(z-fan),0)/k
 return min(z,fan)-h*h*k*.25

tree=Point(2683532.398-O[0],1246843.141-O[1]);pit=tree.buffer(1.0,quad_segs=24).intersection(g)
band=g.difference(g.buffer(-.22,join_style=2));inside=g.difference(band).difference(pit)
masks={'platform':inside,'curb_top':band,'tree_soil':pit}
parts={k:[] for k in masks};parts['curb_face']=[];parts['curb_joint']=[]
x0,y0,x1,y1=g.bounds
for x in np.arange(np.floor(x0*2)/2,x1,.5):
 for y in np.arange(np.floor(y0*2)/2,y1,.5):
  cell=box(x,y,x+.5,y+.5)
  if not g.intersects(cell):continue
  for name,mask in masks.items():
   inter=cell.intersection(mask)
   for p in ([inter] if inter.geom_type=='Polygon' else getattr(inter,'geoms',[])):
    if p.geom_type!='Polygon' or p.area<1e-10:continue
    for t in constrained_delaunay_triangles(p).geoms:
     v=[[xx,yy,floor(xx,yy)+(.002 if name=='curb_top' else -.025 if name=='tree_soil' else 0)] for xx,yy in list(t.exterior.coords)[:3]]
     if np.cross(np.array(v[1])-v[0],np.array(v[2])-v[0])[2]<0:v.reverse()
     parts[name].append(v)
ring=g.exterior;stations={0.,ring.length};stations.update(np.arange(0,ring.length,.3));stations.update(ring.project(Point(p)) for p in ring.coords)
stations=sorted(stations)
for s0,s1 in zip(stations,stations[1:]):
 if s1-s0<1e-7:continue
 p,q=[np.array(ring.interpolate(s).coords[0]) for s in [s0,s1]]
 a=[*p,floor(*p)+.002];b=[*q,floor(*q)+.002];c=[*q,min(bottom.sample(q)[0]-.03,b[2]-.02)];d=[*p,min(bottom.sample(p)[0]-.03,a[2]-.02)]
 parts['curb_face'] += [[a,c,b],[a,d,c]]
for s in np.arange(.5,ring.length,1.1):
 p=np.array(ring.interpolate(s).coords[0]);t=np.array(ring.interpolate(min(s+.02,ring.length)).coords[0])-np.array(ring.interpolate(max(s-.02,0)).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])
 corners=[p-t*.0015,p+t*.0015,p+n*.219+t*.0015,p+n*.219-t*.0015];v=[[x,y,floor(x,y)+.003] for x,y in corners]
 parts['curb_joint'] += [[v[0],v[1],v[2]],[v[0],v[2],v[3]]]
uv={}
for name,tt in parts.items():
 uv[name]=[]
 for tri in tt:
  if name=='curb_face':
   ss=[ring.project(Point(v[:2])) for v in tri]
   if max(ss)-min(ss)>ring.length/2:ss=[s+ring.length if s<ring.length/2 else s for s in ss]
   uv[name].append([[s/2,v[2]/2] for s,v in zip(ss,tri)])
  else:uv[name].append([[v[0]/(2.05 if name=='platform' else 2),v[1]/(2.05 if name=='platform' else 2)] for v in tri])
top=np.array(parts['platform']+parts['curb_top']+parts['tree_soil']);norm=np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0]);slopes=np.linalg.norm(norm[:,:2],axis=1)/np.maximum(abs(norm[:,2]),1e-10)
actual_area=float(abs(norm[:,2]).sum()/2);assert abs(actual_area-g.area)<1e-5
assert slopes.max()<.09, f'Unusable local ramp transition: {slopes.max():.3f}'
report={'source_id':rec['id'],'area_m2':g.area,'area_rebuilt_m2':actual_area,'perimeter_m':ring.length,'height_support_count':len(pts),'robust_plane_local':coef.tolist(),'residual_quantiles_m':np.quantile(pts[:,2]-A@coef,[0,.1,.5,.9,1]).tolist(),'ramps':ramps,'slope_quantiles':np.quantile(slopes,[.5,.9,.99,1]).tolist(),'tree_pit':{'source_tree_id':'bauminventar.69773','radius_m_inferred':1.0,'depth_m_inferred':.025},'curb_width_m_inferred':.22,'joint_module_m_inferred':1.1,'basis':'Actual AV459 plan, original photographic height samples and official walking crossings; ramp profiles, curb detail and pit are inferred. Small refuge islands with unreliable photo height were not built.','accepted':False}
result={'report':report,'geometry_lv95':rec['geometry'],'parts':parts,'uv':uv,'road_input_sha256':support['road_input_sha256']}
(OUT/'platform_input.json').write_text(json.dumps(result,separators=(',',':')));print(json.dumps(report))
