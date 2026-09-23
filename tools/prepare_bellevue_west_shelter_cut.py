"""Cut the replaced shelter volume, retaining photo triangles above its roof."""
import json,hashlib,struct
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,Point
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context'
canopy=json.loads((OUT/'canopy_input.json').read_text())
mask=globals().get('CUT_MASK',shape(canopy['roof_plan_lv95']).buffer(.4));upper=float(globals().get('CUT_UPPER',413.0))
lower=globals().get('CUT_LOWER',None)
if lower is not None:
 lower=float(lower);assert lower<upper
description=globals().get('CUT_DESCRIPTION','Rebuild roof EGID302063027 and its occupied footprint within official roof plan +0.4m, bounded above at LN02 413.0m; source vegetation above that height retained.')
basepath=OUT/globals().get('CUT_BASE','photo_cut.json');base=json.loads(basepath.read_text());overrides={str(o['node']):o for o in base['overrides']};manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
stats={'nodes_changed':0,'input_triangles_replaced':0,'triangles_split_at_height':0,'high_triangles_preserved':0}
def clip(poly,above,height=upper):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ai=a[2]>=height if above else a[2]<=height;bi=b[2]>=height if above else b[2]<=height
  if ai:out.append(a)
  if ai!=bi:out.append(a+(b-a)*((height-a[2])/(b[2]-a[2])))
 return out
for item in manifest['items']:
 m=np.array(item['mbs']);key=str(item['node'])
 if Point(m[:2]).distance(mask)>m[3]:continue
 if key in overrides:
  p=overrides[key];xyz=np.array(p['vertices']).reshape(-1,3);uv=np.array(p['uv_source_v_unflipped']).reshape(-1,2)
 else:
  raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0];xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3).astype(float);uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2).copy()
 if len(xyz)==0:continue
 vv=[];uu=[];changed=False
 def keep(tri):vv.extend((np.array(tri)[:,:3]-m[:3]).tolist());uu.extend(np.array(tri)[:,3:].tolist())
 for tri,tex in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
  original=np.c_[tri,tex];poly=Polygon(tri[:,:2]);centroid=Point(tri[:,:2].mean(axis=0))
  if (poly.is_valid and poly.area>1e-9 and not poly.intersects(mask)) or (poly.area<1e-9 and not mask.intersects(poly)):
   keep(original);continue
  if min(tri[:,2])>=upper:stats['high_triangles_preserved']+=1;keep(original);continue
  if lower is not None and max(tri[:,2])<=lower:keep(original);continue
  low=clip(list(original),False);high=clip(list(original),True)
  if high:stats['triangles_split_at_height']+=1
  for i in range(1,len(high)-1):keep([high[0],high[i],high[i+1]])
  if lower is not None:
   below=clip(low,False,lower);low=clip(low,True,lower)
   for i in range(1,len(below)-1):keep([below[0],below[i],below[i+1]])
  changed=True;stats['input_triangles_replaced']+=1
  for i in range(1,len(low)-1):
   src=np.array([low[0],low[i],low[i+1]]);lp=Polygon(src[:,:2])
   if not lp.is_valid or lp.area<1e-9:
    if not mask.covers(Point(src[:,:2].mean(axis=0))):keep(src)
    continue
   diff=lp.difference(mask)
   if diff.area<1e-9:continue
   ab=(src[1:,:2]-src[0,:2]).T;normal=np.cross(src[1,:3]-src[0,:3],src[2,:3]-src[0,:3])
   for p in ([diff] if diff.geom_type=='Polygon' else getattr(diff,'geoms',[])):
    if p.geom_type!='Polygon' or p.area<1e-9:continue
    for sub in constrained_delaunay_triangles(p).geoms:
     xy=np.array(sub.exterior.coords)[:3,:2];w=np.linalg.solve(ab,(xy-src[0,:2]).T).T;t=src[0]+w[:,0,None]*(src[1]-src[0])+w[:,1,None]*(src[2]-src[0])
     if np.dot(np.cross(t[1,:3]-t[0,:3],t[2,:3]-t[0,:3]),normal)<0:t=t[::-1]
     keep(t)
 if changed:stats['nodes_changed']+=1;overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']}
result={'mask_basis':base['mask_basis']+' '+description,'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),globals().get('CUT_STATS_KEY','shelter_stats'):stats,'changed_nodes':len(overrides),'overrides':list(overrides.values())}
(OUT/globals().get('CUT_OUTPUT','shelter_photo_cut.json')).write_text(json.dumps(result,separators=(',',':')));print(json.dumps({k:v for k,v in result.items() if k not in ['overrides','mask_basis']}))
