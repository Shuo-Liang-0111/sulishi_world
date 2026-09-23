"""Source-constrained, continuous AV24105 paving, road curb and tree pits.

The grade is an explicitly inferred smooth surface fitted to existing official
terrain and spatially balanced photo support. It is not a new topographic survey.
"""
from pathlib import Path
import sys,json,math
import numpy as np
from shapely.geometry import shape,Point,Polygon,box,mapping
from shapely.affinity import translate
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,nearest_points
from shapely import constrained_delaunay_triangles
from scipy.interpolate import BSpline
from functools import lru_cache
from inspect_platform_road_join import Surface

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/limmat_sidewalk';d=json.loads((D/'context.json').read_text(encoding='utf-8'));O=np.array(d['origin'])
g=orient(translate(shape(d['source']['geometry']),-O[0],-O[1]),1);tin=Surface(np.asarray(d['terrain_triangles_local']))
roadplans=unary_union([translate(shape(f['geometry']),-O[0],-O[1]) for f in d['neighbors'] if f['properties']['art_txt']=='befestigt.Strasse_Weg.Strasse'])
street_edge=g.exterior.intersection(roadplans.buffer(.003));curb=g.intersection(street_edge.buffer(.20,join_style=2))
# Use broad longitudinal stationing along the sidewalk, with one fitted crossfall.
lo,hi=g.bounds[1],g.bounds[3];knots=np.r_[[lo]*4,np.arange(lo+8,hi-3,8),[hi]*4];nc=len(knots)-4
def design(xy):
 xy=np.atleast_2d(xy);s=np.clip(xy[:,1],lo,hi)
 b=BSpline.design_matrix(s,knots,3).toarray()
 # The northward street axis drifts west by approximately0.357m/m, a numerical
 # coordinate basis only. No surveyed geometry is moved to follow this line.
 cross=xy[:,0]+.357*(xy[:,1]-200)+274
 return np.c_[b,cross]
cells={}
for p in d['candidate_ground_support']:
 xyz=np.array(p['point_ln02'])-O;cells.setdefault(tuple(np.floor(xyz[:2])),[]).append(xyz)
photo=np.array([np.median(v,axis=0) for v in cells.values()])
terrain=[]
for x in np.arange(g.bounds[0],g.bounds[2]+1,2):
 for y in np.arange(g.bounds[1],g.bounds[3]+1,2):
  if g.buffer(-.28).covers(Point(x,y)):terrain.append([x,y,tin.sample(np.array([x,y]))[0]])
terrain=np.array(terrain);points=np.vstack([photo,terrain]);A=design(points[:,:2]);z=points[:,2]
baseweights=np.r_[np.ones(len(photo)),np.full(len(terrain),.60)]
regular=np.zeros((nc-2,nc+1))
for i in range(nc-2):regular[i,i:i+3]=[1,-2,1]
weights=baseweights.copy()
for _ in range(12):
 coef=np.linalg.lstsq(np.vstack([A*weights[:,None],regular*.8]),np.r_[z*weights,np.zeros(nc-2)],rcond=None)[0]
 residual=z-A@coef;weights=baseweights*np.minimum(1,.08/np.maximum(abs(residual),1e-7))

roadcells={}
for rec in d['photo_samples']:
 p=np.array(rec['point_ln02'])-O
 if roadplans.buffer(-.35).covers(Point(p[:2])) and abs(rec['photo_minus_tin_m'])<.40:
  roadcells.setdefault(tuple(np.floor(p[:2])),[]).append(p)
roadpoints=np.array([np.median(v,axis=0) for v in roadcells.values()]);assert len(roadpoints)>100
RA=design(roadpoints[:,:2]);rw=np.ones(len(roadpoints))
for _ in range(12):
 roadcoef=np.linalg.lstsq(np.vstack([RA*rw[:,None],regular*.8]),np.r_[roadpoints[:,2]*rw,np.zeros(nc-2)],rcond=None)[0]
 rr=roadpoints[:,2]-RA@roadcoef;rw=np.minimum(1,.06/np.maximum(abs(rr),1e-7))
def roadfloor(xy):return float(design(xy)[0]@roadcoef)

ramps=[]
for f in json.loads((R/'sources/features/tbl_routennetz.geojson').read_text())['features']:
 if f['properties'].get('fuss')!=1:continue
 geom=translate(shape(f['geometry']),-O[0],-O[1]);cut=geom.intersection(g.exterior)
 for q in ([cut] if cut.geom_type=='Point' else getattr(cut,'geoms',[])):
  if q.geom_type=='Point' and q.distance(street_edge)<.025:
   xy=np.array(q.coords[0]);z0=roadfloor(xy)+.006
   ramps.append({'source':f['id'],'xy_local':xy.tolist(),'threshold_z_local':z0,'width_m_inferred':2.8,'grade_inferred':.045})
def basefloor(xy):return float(design(xy)[0]@coef)
@lru_cache(maxsize=150000)
def floor(x,y):
 p=np.array([x,y]);z=basefloor(p)
 # Millimetre negative inferred upstands are not meaningful measured depressions.
 # Join continuously to a positive road edge, localized near that shared edge.
 z=max(z,roadfloor(p)+.012-.03*Point(p).distance(street_edge))
 for r in ramps:
  c=np.array(r['xy_local']);dist=np.linalg.norm(p-c);fan=r['threshold_z_local']+.045*max(0,dist-1.4)
  z=min(z,fan)
 return z

forms={24688:(.63,(4.8,4.6),3.5),60153:(.77,(6,5.6),3.9),72765:(.70,(5.6,5.0),4.1),87439:(.74,(5.5,5.2),4.2),122134:(.55,(4.4,4.1),3.5),123846:(.78,(5.8,5.4),4.0),131024:(.61,(4.7,4.3),3.7),119453:(.43,(4.1,3.5),3.0),110287:(.24,(2.6,2.3),2.6),63844:(.38,(3.3,2.9),2.9),59566:(.20,(2.5,2.3),2.8),127665:(.40,(3.6,3.1),3.0),131030:(.35,(3.1,2.7),2.8),142355:(.32,(2.9,2.6),2.9),133551:(.28,(2.7,2.4),2.7)}
pits=[]
for tree in d['trees']:
 if not shape(d['source']['geometry']).covers(shape(tree['geometry'])):continue
 ident=tree['properties']['objectid'];diam,radii,clearance=forms[ident];xy=np.array(tree['geometry']['coordinates'])-O[:2]
 # Open soil dimensions are inference. Retain a clear, continuous roadside strip
 # and never overlap the existing building hole or a neighboring road.
 radius=1.03 if 'Platanus' in tree['properties']['baumart_lat'] else .66+.25*diam
 # Tree72765 has0.787m to the surveyed road edge. Its inferred buttressed collar
 # needs more than the old0.547m clipped opening; keep6cm of road-side edge and
 # enlarge only this inferred soil opening. Source tree/ground coordinates stay.
 margin=.06 if ident==72765 else .24
 pit=Point(xy).buffer(radius,quad_segs=40).intersection(g.buffer(-margin))
 assert pit.covers(Point(xy)),tree['id']
 pits.append({'source':tree,'xy_local':xy.tolist(),'geometry_local':mapping(pit),'radius_m_inferred':radius,'edge_margin_m_inferred':margin,'ground_ln02_m':floor(*xy)-.028+400,'origin':O.tolist(),'height_m':tree['properties']['hoehe'],'inferred':{'seed':ident,'trunk_diameter_m':diam,'crown_radius_m':radii,'branch_clearance_m':clearance},'basis':'Inventory2022 XY/species/height; inferred crown, girth, branches and leaf arrangement. Ground follows AV24105 fitted surface.'})
assert len(pits)==15
soil=unary_union([shape(p['geometry_local']) for p in pits]);masks={'asphalt':g.difference(curb).difference(soil),'curb_top':curb.difference(soil),'soil':soil}
parts={k:[] for k in masks};parts.update(curb_face=[],curb_joint=[],pit_edge=[],retaining_edge=[])
def polygons(obj):return [p for p in ([obj] if obj.geom_type=='Polygon' else getattr(obj,'geoms',[])) if p.geom_type=='Polygon' and p.area>1e-10]
def addface(key,tri):
 parts[key].append([list(v) for v in tri])
def height(x,y,key):return floor(x,y)-(.028 if key=='soil' else 0)
step=.5;gx=np.arange(math.floor(g.bounds[0]),math.ceil(g.bounds[2])+step,step);gy=np.arange(math.floor(g.bounds[1]),math.ceil(g.bounds[3])+step,step)
grid=np.array([[floor(float(x),float(y)) for y in gy] for x in gx])
@lru_cache(maxsize=150000)
def meshfloor(x,y):
 i=int(np.clip(math.floor((x-gx[0])/step),0,len(gx)-2));j=int(np.clip(math.floor((y-gy[0])/step),0,len(gy)-2));u=(x-gx[i])/step;v=(y-gy[j])/step
 if u+v<=1:return float(grid[i,j]*(1-u-v)+grid[i+1,j]*u+grid[i,j+1]*v)
 return float(grid[i+1,j+1]*(u+v-1)+grid[i,j+1]*(1-u)+grid[i+1,j]*(1-v))
for i,x in enumerate(gx[:-1]):
 for j,y in enumerate(gy[:-1]):
  if not g.intersects(box(x,y,x+step,y+step)):continue
  for tri in [Polygon([(x,y),(x+step,y),(x,y+step)]),Polygon([(x+step,y+step),(x,y+step),(x+step,y)])]:
   for key,mask in masks.items():
    for p in polygons(mask.intersection(tri)):
     for t in constrained_delaunay_triangles(p).geoms:
      vv=np.array([[xx,yy,meshfloor(xx,yy)-(.028 if key=='soil' else 0)] for xx,yy in list(t.exterior.coords)[:3]])
      if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:vv=vv[::-1]
      addface(key,vv)
ring=g.exterior
stations=sorted({0.,ring.length,*np.arange(0,ring.length,.25),*(ring.project(Point(p)) for p in ring.coords)})
curb_report=[];retaining_report=[]
for a,b in zip(stations,stations[1:]):
 if b-a<1e-8:continue
 p,q=[np.array(ring.interpolate(v).coords[0]) for v in [a,b]];mid=(p+q)/2
 if Point(mid).distance(street_edge)<.02:
  za,zb=meshfloor(*p),meshfloor(*q);ra=roadfloor(p);rb=roadfloor(q)
  # Roadside face ends just below the photo-supported road. The city TIN blends
  # across curb steps and sits around0.15m above the photographic asphalt here.
  # Actual runtime road
  # integration still requires a separate continuous edge check.
  lowa=min(za-.035,ra-.025);lowb=min(zb-.035,rb-.025)
  addface('curb_face',[[*p,za],[*q,lowb],[*q,zb]]);addface('curb_face',[[*p,za],[*p,lowa],[*q,lowb]])
  curb_report.append([float((a+b)/2),float(za-ra)])
 else:
  # No curb across the southern/northern sidewalk continuation. Only model
  # retaining thickness where the cached ground just outside is genuinely lower.
  tangent=(q-p)/np.linalg.norm(q-p);out=np.array([tangent[1],-tangent[0]])
  za,zb=meshfloor(*p),meshfloor(*q);ra=tin.sample(p+out*.40)[0];rb=tin.sample(q+out*.40)[0]
  if min(za-ra,zb-rb)>.18:
   addface('retaining_edge',[[*p,za-.018],[*q,rb-.025],[*q,zb-.018]]);addface('retaining_edge',[[*p,za-.018],[*p,ra-.025],[*q,rb-.025]])
   retaining_report.append([mid.tolist(),float(za-ra),float(zb-rb)])
for st in np.arange(.4,ring.length,1.14):
 p=np.array(ring.interpolate(st).coords[0])
 if Point(p).distance(street_edge)>.012:continue
 t=np.array(ring.interpolate(st+.01).coords[0])-np.array(ring.interpolate(st-.01).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])
 vv=[[xx,yy,meshfloor(xx,yy)+.0007] for xx,yy in [p-t*.0014,p+t*.0014,p+n*.199+t*.0014,p+n*.199-t*.0014]]
 for piece in polygons(Polygon(np.array(vv)[:,:2]).difference(soil)):
  for tri in constrained_delaunay_triangles(piece).geoms:
   addface('curb_joint',[[xx,yy,meshfloor(xx,yy)+.0007] for xx,yy in list(tri.exterior.coords)[:3]])
for pit in pits:
 p=shape(pit['geometry_local']);coords=list(p.exterior.coords)
 for a,b in zip(coords,coords[1:]):
  za,zb=meshfloor(*a),meshfloor(*b)
  addface('pit_edge',[[*a,za],[*b,zb-.03],[*b,zb]]);addface('pit_edge',[[*a,za],[*a,za-.03],[*b,zb-.03]])
 pit['ground_ln02_m']=meshfloor(*pit['xy_local'])-.028+400
uv={}
for key,tris in parts.items():
 uv[key]=[]
 for tri in tris:
  if key in ['curb_face','retaining_edge']:
   stations=[ring.project(Point(v[:2])) for v in tri]
   if max(stations)-min(stations)>ring.length/2:stations=[st+ring.length if st<ring.length/2 else st for st in stations]
   uv[key].append([[st/.67,v[2]/.67] for st,v in zip(stations,tri)])
  elif key=='pit_edge':
   origin=np.array(tri[0][:2]);deltas=np.array(tri)[:,:2]-origin;span=deltas[np.argmax(np.linalg.norm(deltas,axis=1))];span/=max(np.linalg.norm(span),1e-12)
   uv[key].append([[float(np.dot(np.array(v[:2]),span))/.67,v[2]/.67] for v in tri])
  else:
   size=2.05 if key=='asphalt' else 1. if key=='soil' else .67
   uv[key].append([[v[0]/size,v[1]/size] for v in tri])
top=np.array(parts['asphalt']+parts['curb_top']+parts['soil']);norm=np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0]);area=abs(norm[:,2]).sum()/2
valid=abs(norm[:,2])>1e-8;slopes=np.linalg.norm(norm[valid,:2],axis=1)/abs(norm[valid,2]);assert abs(area-g.area)<1e-5
assert slopes.max()<.12,slopes.max()
report={'source_id':d['source']['id'],'area_m2':g.area,'mesh_plan_area_m2':float(area),'holes_preserved':len(g.interiors),'tree_pits':len(pits),'grade_quantiles':np.quantile(slopes,[.5,.9,.99,1]).tolist(),'height_local_range':np.quantile(top[:,:,2],[0,1]).tolist(),'photo_support_cells':len(photo),'tin_support_points':len(terrain),'photo_residual_quantiles_m':np.quantile(photo[:,2]-design(photo[:,:2])@coef,[0,.1,.5,.9,1]).tolist(),'road_photo_support_cells':len(roadpoints),'road_fit_residual_quantiles_m':np.quantile(roadpoints[:,2]-RA@roadcoef,[0,.1,.5,.9,1]).tolist(),'curb_road_upstand_quantiles_m':np.quantile(np.array(curb_report)[:,1],[0,.1,.5,.9,1]).tolist(),'retaining_segments':len(retaining_report),'road_curb_length_m':street_edge.length,'ramps':ramps,'basis':'Cached AV24105 footprint and building hole; official TIN plus balanced photographic ground support. Neighboring road grade fitted separately from cached photographic asphalt; TIN blends curb and road and cannot determine its upstand. Smooth grade, road curb20cm wide,1.14m joints, soil openings, surface finishes and ramp detail are explicit inference. No accessibility or runtime claim.','accepted':False}
(D/'ground_input.json').write_text(json.dumps({'report':report,'origin':O.tolist(),'geometry_lv95':d['source']['geometry'],'parts':parts,'uv':uv,'pits':pits,'grade_grid':{'x':gx.tolist(),'y':gy.tolist(),'z':grid.tolist()},'fit':{'knots':knots.tolist(),'coefficients':coef.tolist()},'retaining_edge_diagnostics':retaining_report},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps(report,indent=2))
