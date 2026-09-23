"""Explicit floor/apron repair and bounded replacement of the actual service building."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import shape,Polygon,Point,box,mapping
from shapely.affinity import translate
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_service';d=json.loads((D/'input.json').read_text());O=np.array(d['origin']);body=translate(shape(d['av_footprint_lv95']),-O[0],-O[1]);sourcebody=translate(shape(d['building_plan_lv95']),-O[0],-O[1]);p=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text(encoding='utf-8'));walk=translate(shape(p['geometry_lv95']),-O[0],-O[1]);apron=body.buffer(1.25).difference(body).intersection(walk);asphalt=walk.difference(unary_union([shape(x['geometry_local']) for x in p['pits']]));gg=p['grade_grid'];gx=np.array(gg['x']);gy=np.array(gg['y']);grid=np.array(gg['z']);step=.5;floor=d['floor_local_inferred']
def z(q):
 x,y=q;i=int(np.clip(np.floor((x-gx[0])/step),0,len(gx)-2));j=int(np.clip(np.floor((y-gy[0])/step),0,len(gy)-2));u=(x-gx[i])/step;v=(y-gy[j])/step
 if u+v<=1:return float(grid[i,j]*(1-u-v)+grid[i+1,j]*u+grid[i,j+1]*v)
 return float(grid[i+1,j+1]*(u+v-1)+grid[i,j+1]*(1-u)+grid[i+1,j]*(1-v))
def polygons(g):return [p for p in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[])) if p.geom_type=='Polygon' and p.area>1e-10]
parts={'outside_asphalt':[],'apron':[],'floor':[],'ceiling':[]};apron=apron.intersection(asphalt)
for tri in p['parts']['asphalt']:
 g=Polygon(np.array(tri)[:,:2]);remaining=g.difference(apron)
 if remaining.equals(g):parts['outside_asphalt'].append(tri);continue
 for pp in polygons(remaining):
  for t in constrained_delaunay_triangles(pp).geoms:parts['outside_asphalt'].append([[x,y,z((x,y))] for x,y in list(t.exterior.coords)[:3]])
# A common piecewise-planar grade is clipped AFTER its heights are evaluated.
# Evaluating a nonlinear distance field on tiny boundary slivers amplifies slopes.
# The .2m constant landing and outer .35m unchanged band also keep both seams exact.
apron=body.buffer(2.5).difference(body).intersection(asphalt)
parts['outside_asphalt']=[]
for tri in p['parts']['asphalt']:
 g=Polygon(np.array(tri)[:,:2]);remaining=g.difference(apron)
 if remaining.equals(g):parts['outside_asphalt'].append(tri);continue
 for pp in polygons(remaining):
  for t in constrained_delaunay_triangles(pp).geoms:parts['outside_asphalt'].append([[x,y,z((x,y))] for x,y in list(t.exterior.coords)[:3]])
x0,y0,x1,y1=apron.bounds;resolution=.125
fields=[]
for x in np.arange(np.floor(x0/resolution)*resolution,x1,resolution):
 for y in np.arange(np.floor(y0/resolution)*resolution,y1,resolution):
  if not apron.intersects(box(x,y,x+resolution,y+resolution)):continue
  q=np.array([[x,y],[x+resolution,y],[x,y+resolution],[x+resolution,y+resolution]])
  for ids in [[0,1,2],[1,3,2]]:
   xy=q[ids];blend=np.array([np.clip((Point(*pt).distance(body)-.2)/1.95,0,1) for pt in xy]);a=1-blend;b=blend*np.array([z(pt) for pt in xy]);aa=np.linalg.solve(xy[1:]-xy[0],a[1:]-a[0]);bb=np.linalg.solve(xy[1:]-xy[0],b[1:]-b[0]);fields.append((xy,a,b,aa,bb))
from scipy.optimize import minimize_scalar
A=np.array([f[3] for f in fields]);B=np.array([f[4] for f in fields]);samples=np.array(d['perimeter_ground_samples'])[:,2]
opt=minimize_scalar(lambda h:np.linalg.norm(A*h+B,axis=1).max(),bounds=(float(samples.min()),float(samples.max())),method='bounded',options={'xatol':1e-9});floor=float(opt.x)
for xy,a,b,aa,bb in fields:
   zz=a*floor+b;gradient=aa*floor+bb
   for pp in polygons(apron.intersection(Polygon(xy))):
    for t in constrained_delaunay_triangles(pp).geoms:
     parts['apron'].append([[xx,yy,float(zz[0]+gradient@(np.array([xx,yy])-xy[0]))] for xx,yy in list(t.exterior.coords)[:3]])
for t in constrained_delaunay_triangles(body).geoms:parts['floor'].append([[x,y,floor] for x,y in list(t.exterior.coords)[:3]])
roof_tri=np.array(next(x for x in d['source_parts'] if x['kind']=='BB04' and x['type']=='RoofSurface')['triangles']);high=roof_tri[roof_tri[:,:,2].max(1)>11.89];skylight=unary_union([Polygon(t[:,:2]) for t in high]);ceiling=body.difference(skylight)
for pp in polygons(ceiling):
 for t in constrained_delaunay_triangles(pp).geoms:parts['ceiling'].append([[x,y,11.384] for x,y in list(t.exterior.coords)[:3]][::-1])
for key,tt in parts.items():
 for t in tt:
  if (np.cross(np.array(t[1])-t[0],np.array(t[2])-t[0])[2]>0)==(key=='ceiling'):t.reverse()
ctx=json.loads((R/'derived/bellevue/south_context/ground_support.json').read_text(encoding='utf-8'));plan=shape(d['canopy_plan_lv95']).union(shape(d['building_plan_lv95']));fixtures=[f for f in ctx['facilities'] if plan.buffer(.5).intersects(shape(f['geometry']))]
current=json.loads((R/'runtime/station_road_working.json').read_text());assert current['version']=='G1_013r2'
mask=plan.buffer(.30);fountain_guards=[]
for f in ctx['facilities']:
 if f in fixtures:continue
 if mask.intersects(shape(f['geometry'])):fountain_guards.append(shape(f['geometry']).buffer(.55))
if fountain_guards:mask=mask.difference(unary_union(fountain_guards))
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':405.0,'CUT_UPPER':413.08,'CUT_BASE':Path(current['source_cut_file']).name,'CUT_OUTPUT':'south_service_photo_cut.json','CUT_STATS_KEY':'service_building','CUT_DESCRIPTION':'Physical reconstruction of EGID302040350 complete building/cantilever footprint plus0.30m, LN02405..413.08; six source ads and three source benches recreated. Trees above the roof remain until individually rebuilt; original source collection unchanged.'})
ap=np.array(parts['apron']);n=np.cross(ap[:,1]-ap[:,0],ap[:,2]-ap[:,0]);valid=abs(n[:,2])>1e-9;slope=np.linalg.norm(n[valid,:2],axis=1)/abs(n[valid,2]);out={'parts':parts,'apron_area_m2':apron.area,'apron_max_slope':float(slope.max()),'source_floor_replaced_m2':body.area,'skylight_plan_local':mapping(skylight),'facilities':fixtures,'photo_cut_file':'derived/bellevue/west_context/south_service_photo_cut.json','basis':'Flat inferred indoor floor at supported street grade;1.25m outer apron transitions continuously to existing ground without changing AVplan. Official footprint, source roof envelope and existing tree pits preserved. Not surveyed accessibility approval.'}
out['floor_local_inferred']=floor;out['basis']='Flat interior elevation inferred within supported perimeter height range by minimising maximum landing grade, not a surveyed floor. 2.5m apron uses common planar triangles, a constant inner landing and unchanged outer band. AV footprint and source roofs retained; tree pits untouched. Not accessibility acceptance.'
centre=np.array(d['center_lv95'])-O[:2];u=np.array(d['axis_u']);v=np.array(d['axis_v']);coords=np.array(body.exterior.coords);local=(coords-centre)@np.array([u,v]).T;bp=Polygon(local);ft=[]
for xx in np.arange(-12,12,.6):
 for yy in np.arange(-4.2,4.2,.6):
  for pp in polygons(bp.intersection(box(xx+.002,yy+.002,xx+.598,yy+.598))):
   tt=[]
   for t in constrained_delaunay_triangles(pp).geoms:
    vv=[]
    for a,b in list(t.exterior.coords)[:3]:
     pt=centre+u*a+v*b;vv.append([float(pt[0]),float(pt[1]),floor])
    if np.cross(np.array(vv[1])-vv[0],np.array(vv[2])-vv[0])[2]<0:vv.reverse()
    tt.append(vv)
   ft.append({'id':len(ft),'triangles':tt})
out['floor_tiles']=ft
(D/'build_input.json').write_text(json.dumps(out,separators=(',',':')));print(json.dumps({'floor_local':floor,'apron_area':apron.area,'apron_max_slope':out['apron_max_slope'],'sky_area':skylight.area,'facilities':[f['id'] for f in fixtures]}))
