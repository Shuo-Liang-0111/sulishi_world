"""Refine the surveyed 2015 roof envelope using the contractor's published section logic."""
import json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,Point,box,LineString,mapping
from shapely.affinity import translate
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context';O=np.array([2683775,1246700,400])
source=ROOT/'sources/features/bauten_dachmodell_3d.geojson';fs=json.loads(source.read_text())['features'];selected=[f for f in fs if f['properties'].get('egid')==302063027]
f=next(f for f in selected if f['properties']['type']=='RoofSurface');g=translate(shape(f['geometry']).geoms[0],-O[0],-O[1]);g=Polygon(np.array(g.exterior.coords)[:,:2])
wide=np.array([2683537.10351757,1246847.85177490])-O[:2];narrow=np.array([2683556.83670247,1246859.45886520])-O[:2];axis=narrow-wide;length=np.linalg.norm(axis);unit=axis/length
# Circle centres fit surveyed rounded ends. They suggest, but do not survey,
# the end support locations. The third support follows the contractor's midline.
def axispoint(p):return wide+unit*np.clip((np.array(p)-wide)@unit,0,length)
def section(p):
 q=axispoint(p);r=np.linalg.norm(np.array(p)-q);t=np.clip((q-wide)@unit/length,0,1);edge=4.07897935*(1-t)+2.29672586*t
 a=np.clip(r/edge,0,1);a=a*a*(3-2*a)
 return 12.12+.178*a,11.798+.420*a
parts={'roof_metal':[],'soffit':[],'fascia':[]};x0,y0,x1,y1=g.bounds
for x in np.arange(np.floor(x0*2)/2,x1,.5):
 for y in np.arange(np.floor(y0*2)/2,y1,.5):
  inter=g.intersection(box(x,y,x+.5,y+.5))
  for p in ([inter] if inter.geom_type=='Polygon' else getattr(inter,'geoms',[])):
   if p.geom_type!='Polygon' or p.area<1e-9:continue
   for tri in constrained_delaunay_triangles(p).geoms:
    xy=np.array(tri.exterior.coords)[:3,:2]
    a,b=xy[1]-xy[0],xy[2]-xy[0]
    if a[0]*b[1]-a[1]*b[0]<0:xy=xy[::-1]
    parts['roof_metal'].append([[*v,section(v)[0]] for v in xy]);parts['soffit'].append([[*v,section(v)[1]] for v in xy[::-1]])
ring=g.exterior;ss=sorted({*np.arange(0,ring.length,.25),ring.length,*[ring.project(Point(p)) for p in ring.coords]})
for s0,s1 in zip(ss,ss[1:]):
 p,q=[np.array(ring.interpolate(s).coords[0]) for s in [s0,s1]];pt,pb=section(p);qt,qb=section(q)
 a,b,c,d=[*p,pb],[*q,qb],[*q,qt],[*p,pt];parts['fascia'] += [[a,b,c],[a,c,d]]
seams=[]
for s in np.arange(0,ring.length,.52):
 edge=np.array(ring.interpolate(s).coords[0]);center=axispoint(edge);d=edge-center;dist=np.linalg.norm(d)
 if dist<.2:continue
 points=[]
 for t in np.linspace(.1/dist,.99,18):
  p=center+d*t;points.append([*p,section(p)[0]+.007])
 seams.append(points)
record={'egid':302063027,'roof_source':f['id'],'source_ids':[f['id'] for f in selected],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'roof_plan_area_m2':g.area,'roof_plan_lv95':mapping(translate(g,O[0],O[1])),'axis_local':[wide.tolist(),narrow.tolist()],'support_centres_local':[(wide+axis*t).tolist() for t in [0,.5,1]],'source_envelope_z_local':[11.798,12.298],'parts':parts,'standing_seams':seams,'basis':'Exact official roof plan; section refined inside surveyed height envelope using contractor account and photographs (Immobilia May 2016 p76). Roof centre drainage, three mushroom steel supports, concrete soffit and radial metal seams are source-supported types. Support centres from fitted roof end circles/midline; precise profiles, seam spacing and finishes are inference. GroundSurface is roof underside, not pedestrian floor.','accepted':False}
(OUT/'canopy_input.json').write_text(json.dumps(record,separators=(',',':')));print(json.dumps({k:v for k,v in record.items() if k not in ['parts','standing_seams','roof_plan_lv95']}))
