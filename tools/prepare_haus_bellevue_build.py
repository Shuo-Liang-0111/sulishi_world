"""Prepare one continuous sidewalk and measured frontage from existing AV/photo support."""
from pathlib import Path
from functools import lru_cache
import json, numpy as np, runpy
from shapely.geometry import shape,Point,Polygon,LineString,box,mapping
from shapely.geometry.polygon import orient
from shapely.affinity import translate
from shapely.ops import unary_union,nearest_points
from shapely import constrained_delaunay_triangles
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter
from inspect_platform_road_join import Surface,road
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'derived/haus_bellevue';O=np.array([2683775,1246700,400])
d=json.loads((D/'context.json').read_text());g=orient(translate(shape(d['sidewalk']['geometry']),-O[0],-O[1]),1);bottom=Surface(road)
roads=unary_union([translate(shape(f['geometry']),-O[0],-O[1]) for f in d['adjacent_surfaces'] if f['properties']['art_txt']=='befestigt.Strasse_Weg.Strasse'])
edge=g.boundary.intersection(roads.buffer(.003));curb=g.intersection(edge.buffer(.22,join_style=2))
fit=d['robust_ground_fit'];co=np.array(fit['coefficients']);cen=np.array(fit['xy_center_local']);ramps=[]
for f in d['walking_links']:
 cross=translate(shape(f['geometry']),-O[0],-O[1]).intersection(g.boundary)
 if cross.geom_type!='Point' or cross.distance(edge)>.1:continue
 xy=np.array(cross.coords[0]);station=g.exterior.project(cross);samples=[]
 for ds in np.linspace(-1.35,1.35,19):
  p=np.array(g.exterior.interpolate((station+ds)%g.exterior.length).coords[0]);z,dist=bottom.sample(p)
  if Point(p).distance(edge)<.03:samples.append([*p,z+.008])
 if len(samples)>1:ramps.append({'source':f['id'],'center':xy.tolist(),'threshold':samples,'width_inferred':2.7})
seg=np.array([pair for r in ramps for pair in zip(r['threshold'][:-1],r['threshold'][1:])]);sa=seg[:,0];sv=seg[:,1]-sa;sl=np.sum(sv[:,:2]**2,axis=1)
@lru_cache(maxsize=150000)
def initial_floor(x,y):
 p=np.array([x,y]);base=float((p-cen)@co[:2]+co[2]);q=np.array(nearest_points(edge,Point(p))[0].coords[0]);rz,dist=bottom.sample(q)
 # Shared road heights constrain the seam. Fade toward photo-supported facade
 # height over the full sidewalk; never allow an inverted curb lip.
 distance=np.linalg.norm(p-q);mix=max(0,1-distance/4.5);mix=mix*mix*(3-2*mix)
 z=base*(1-mix)+(rz+.10)*mix
 t=np.clip(np.sum((p-sa[:,:2])*sv[:,:2],axis=1)/sl,0,1);nn=sa+sv*t[:,None]
 fan=float(np.min(nn[:,2]+.05*np.linalg.norm(p-nn[:,:2],axis=1)))
 return min(z,fan)
gx=np.arange(np.floor(g.bounds[0])-1,np.ceil(g.bounds[2])+1.5,.5);gy=np.arange(np.floor(g.bounds[1])-1,np.ceil(g.bounds[3])+1.5,.5)
grid=gaussian_filter(np.array([[initial_floor(x,y) for y in gy] for x in gx]),sigma=.65);interp=RegularGridInterpolator((gx,gy),grid,bounds_error=True)
@lru_cache(maxsize=150000)
def floor(x,y):
 # A shared grid removes Voronoi-nearest-edge discontinuities around the tip.
 return float(interp([[x,y]])[0])
tree_xy=np.array(shape(d['trees'][0]['geometry']).coords[0][:2])-O[:2];pit=Point(tree_xy).buffer(1.15,quad_segs=32).intersection(g)
masks={'asphalt':g.difference(curb).difference(pit),'curb_top':curb.difference(pit),'soil':pit};parts={k:[] for k in masks};parts['curb_face']=[];parts['curb_joint']=[]
x0,y0,x1,y1=g.bounds
for x in np.arange(np.floor(x0*2)/2,x1,.5):
 for y in np.arange(np.floor(y0*2)/2,y1,.5):
  cell=box(x,y,x+.5,y+.5)
  if not g.intersects(cell):continue
  for name,mask in masks.items():
   inter=mask.intersection(cell)
   for p in ([inter] if inter.geom_type=='Polygon' else getattr(inter,'geoms',[])):
    if p.geom_type!='Polygon' or p.area<1e-10:continue
    for t in constrained_delaunay_triangles(p).geoms:
     if t.area<1e-8:continue
     vv=[[xx,yy,floor(xx,yy)+(-.035 if name=='soil' else 0)] for xx,yy in list(t.exterior.coords)[:3]]
     if np.cross(np.array(vv[1])-vv[0],np.array(vv[2])-vv[0])[2]<0:vv.reverse()
     parts[name].append(vv)
ring=g.exterior;stations=sorted({0.,ring.length,*np.arange(0,ring.length,.35),*(ring.project(Point(p)) for p in ring.coords)})
for s0,s1 in zip(stations,stations[1:]):
 if s1-s0<1e-7:continue
 p,q=[np.array(ring.interpolate(s).coords[0]) for s in [s0,s1]]
 if Point((p+q)/2).distance(edge)>.01:continue
 a=[*p,floor(*p)];b=[*q,floor(*q)];c=[*q,bottom.sample(q)[0]-.015];dd=[*p,bottom.sample(p)[0]-.015]
 parts['curb_face'] += [[a,c,b],[a,dd,c]]
for s in np.arange(.31,ring.length,1.13):
 p=np.array(ring.interpolate(s).coords[0])
 if Point(p).distance(edge)>.01:continue
 t=np.array(ring.interpolate(min(s+.02,ring.length)).coords[0])-np.array(ring.interpolate(max(s-.02,0)).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])
 vv=[[x,y,floor(x,y)+.001] for x,y in [p-t*.002,p+t*.002,p+n*.219+t*.002,p+n*.219-t*.002]]
 parts['curb_joint'] += [[vv[0],vv[1],vv[2]],[vv[0],vv[2],vv[3]]]
top=np.array(parts['asphalt']+parts['curb_top']+parts['soil']);norm=np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0]);grades=np.linalg.norm(norm[:,:2],axis=1)/np.maximum(abs(norm[:,2]),1e-10)
assert abs(np.abs(norm[:,2]).sum()/2-g.area)<1e-5
assert grades.max()<.09, f'Excessive local slope: {grades.max()}'
# Piers/recesses already appear in the AV facade; preserve that bay rhythm.
a=np.array(d['sidewalk']['geometry']['coordinates'][0])-O[:2];C=a[5];right=a[31]-C;right/=np.linalg.norm(right);out=np.array([right[1],-right[0]])
proj=lambda i:float((a[i]-C)@right)
bays=[[-.92,1.12],[2.20,4.25],[5.31,7.34]]+[[proj(i),proj(i+1)] for i in [9,13,17,21,25,29]]
front={'C':C.tolist(),'right':right.tolist(),'out':out.tolist(),'u_min':proj(3),'u_max':proj(32),'bays':bays,'entry_bay_index':5,'floor_local':8.39,'top_local':13.34,'source':'AV13983/AV35946 stepped facade plus SPPA exterior reference; elevations and fabrication inferred'}
uv={}
for key,tt in parts.items():
 uv[key]=[]
 for tri in tt:
  if key=='curb_face':uv[key].append([[ring.project(Point(v[:2]))/2,v[2]/2] for v in tri])
  else:uv[key].append([[v[0]/(2.05 if key=='asphalt' else 2),v[1]/(2.05 if key=='asphalt' else 2)] for v in tri])
report={'sidewalk_source':'av_bo_boflaeche_a.35946','area_m2':g.area,'street_curb_length_m':edge.length,'grade_quantiles':np.quantile(grades,[.5,.9,.99,1]).tolist(),'ramps':ramps,'basis':'Existing AV footprint; photo-supported facade grade blended to existing road edge. Material, curb and ramp profiles are reconstruction inference, not a measured engineering surface.','accepted':False}
result={'parts':parts,'uv':uv,'frontage':front,'tree_pit':{'source_id':119962,'center_local':tree_xy.tolist(),'ground_z_local':floor(*tree_xy)-.035},'report':report}
(D/'build_input.json').write_text(json.dumps(result,separators=(',',':')))
cutmask=translate(g,O[0],O[1]);facepoly=Polygon([C+right*u+out*v+O[:2] for u,v in [(front['u_min']-.08,.50),(front['u_max']+.08,.50),(front['u_max']+.08,-3.6),(front['u_min']-.08,-3.6)]])
cuttool=ROOT/'tools/prepare_bellevue_west_shelter_cut.py'
runpy.run_path(str(cuttool),init_globals={'CUT_MASK':cutmask,'CUT_UPPER':408.98,'CUT_LOWER':407.7,'CUT_BASE':'tree_69773_refined_photo_cut.json','CUT_OUTPUT':'haus_sidewalk_photo_cut.json','CUT_STATS_KEY':'haus_sidewalk','CUT_DESCRIPTION':'Replace only the AV35946 ground slab LN02 407.7–408.98m; tree canopy and adjacent source facade retained.'})
runpy.run_path(str(cuttool),init_globals={'CUT_MASK':facepoly,'CUT_UPPER':413.34,'CUT_LOWER':408.0,'CUT_BASE':'haus_sidewalk_photo_cut.json','CUT_OUTPUT':'haus_frontage_photo_cut.json','CUT_STATS_KEY':'haus_frontage','CUT_DESCRIPTION':'Replace the south ground-floor frontage only, with measured bay positions and a 3.6m deep closed display zone; no change to upper floors or corner tower.'})
print(json.dumps({'surface':report,'frontage':front},ensure_ascii=False))
