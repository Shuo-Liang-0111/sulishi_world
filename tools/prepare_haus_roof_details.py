"""Continuous roof UV and three photo-inferred oculi in the source dome envelope."""
from pathlib import Path
import json, numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parents[1];D=R/'derived/haus_bellevue'
d=json.loads((D/'upper_input.json').read_text());C=np.array(d['corner']['center_local']);rad=d['corner']['radius_m'];rt=np.array(d['frontage']['right']);outdir=np.array(d['frontage']['out']);origin=np.array(d['frontage']['C'])
source=[]
for p in d['roof_pieces']:
 v=np.array(p['triangles'][0]);delta=v[:,:2]-C;r=np.linalg.norm(delta,axis=1);a=np.arctan2(delta[:,1],delta[:,0])
 if r.max()<5.75 and np.ptp(a)<np.pi and a.mean()>np.radians(-104):source.append((v,np.c_[a*rad,v[:,2]],r))

def radius_at(theta,z):
 q=np.array([theta*rad,z]);hits=[]
 for v,p,r in source:
  mat=(p[1:]-p[0]).T
  if abs(np.linalg.det(mat))<1e-9:continue
  w=np.linalg.solve(mat,q-p[0])
  if min(w)>=-1e-6 and sum(w)<=1.000001:hits.append(float(r[0]+w@(r[1:]-r[0])))
 assert hits,(theta,z)
 return max(hits)

windows=[];holes=[]
for angle in [-64.42,-13.6,37.24]:
 theta=np.radians(angle);z=33.63;r=radius_at(theta,z);slope=(radius_at(theta,z+.10)-radius_at(theta,z-.10))/.20
 normal=np.array([np.cos(theta),np.sin(theta),-slope]);normal/=np.linalg.norm(normal)
 tangent=np.array([-np.sin(theta),np.cos(theta),0.]);up=np.cross(normal,tangent)
 center=np.array([*(C+r*np.array([np.cos(theta),np.sin(theta)])),z])
 vertices=[center+tangent*.445*np.cos(t)+up*.705*np.sin(t) for t in np.linspace(0,2*np.pi,80,endpoint=False)]
 aperture=Polygon([[np.arctan2(p[1]-C[1],p[0]-C[0])*rad,p[2]] for p in vertices]);holes.append(aperture)
 windows.append({'angle_deg':angle,'center':center.tolist(),'normal':normal.tolist(),'right':tangent.tolist(),'up':up.tolist(),'clear_width_m':.82,'clear_height_m':1.30})
cut=unary_union(holes);pieces=[];removed=0.;split=0
def split_height(tri,h):
 results=[]
 for upper in [False,True]:
  ring=[]
  for a,b in zip(tri,np.roll(tri,-1,axis=0)):
   ia=a[2]>=h if upper else a[2]<=h;ib=b[2]>=h if upper else b[2]<=h
   if ia:ring.append(a)
   if ia!=ib:ring.append(a+(b-a)*((h-a[2])/(b[2]-a[2])))
  for i in range(1,len(ring)-1):results.append(np.array([ring[0],ring[i],ring[i+1]]))
 return results
for p in d['roof_pieces']:
 v=np.array(p['triangles'][0]);delta=v[:,:2]-C;r=np.linalg.norm(delta,axis=1);theta=np.arctan2(delta[:,1],delta[:,0]);corner=r.max()<5.75 and np.ptp(theta)<np.pi and theta.mean()>np.radians(-104)
 triangles=[v]
 if corner:
  xy=np.c_[theta*rad,v[:,2]];poly=Polygon(xy)
  if poly.area>1e-9 and poly.intersects(cut):
   diff=poly.difference(cut);removed+=poly.area-diff.area;split+=1;triangles=[]
   for g in ([diff] if diff.geom_type=='Polygon' else getattr(diff,'geoms',[])):
    if g.geom_type!='Polygon' or g.area<1e-10:continue
    for t in constrained_delaunay_triangles(g).geoms:
     q=np.array(t.exterior.coords)[:3];w=np.linalg.solve((xy[1:]-xy[0]).T,(q-xy[0]).T).T;vv=v[0]+w[:,0,None]*(v[1]-v[0])+w[:,1,None]*(v[2]-v[0])
     if np.dot(np.cross(vv[1]-vv[0],vv[2]-vv[0]),np.cross(v[1]-v[0],v[2]-v[0]))<0:vv=vv[::-1]
     triangles.append(vv)
 if corner and p['kind']=='dormer_wall':
  for height in [31.49,35.78]:
   triangles=[part for tri in triangles for part in (split_height(tri,height) if tri[:,2].min()<height<tri[:,2].max() else [tri])]
 for vv in triangles:
  if corner:
   a=np.arctan2(vv[:,1]-C[1],vv[:,0]-C[0]);uv=np.c_[a*rad/2.25,(vv[:,2]-29.95)/(2.25*.88)]
  else:
   # Choose the suitable building axis for differently oriented roof planes.
   # Fixed axes preserve continuity while avoiding zero-area UV on side slopes.
   normal=np.cross(vv[1]-vv[0],vv[2]-vv[0]);axis=rt if abs(normal[:2]@rt)<=abs(normal[:2]@outdir) else outdir
   uv=np.c_[(vv[:,:2]-origin)@axis/2.25,(vv[:,2]-29.95)/(2.25*.90)]
  pieces.append({'kind':p['kind'],'source':p['source'],'vertices':vv.tolist(),'uv':uv.tolist()})
out={'pieces':pieces,'windows':windows,'source_triangles':len(d['roof_pieces']),'clipped_triangles':split,'aperture_parametric_area_m2':removed,'basis':'Source roof envelope preserved except three explicitly photo-inferred oculus openings; positions, frame sections, and glazing inferred from existing exterior reference. UV is continuous in cylindrical/linear metres, 2.25m tile proxy.'}
(D/'roof_details_input.json').write_text(json.dumps(out,separators=(',',':')))
print(json.dumps({k:v for k,v in out.items() if k not in ['pieces','windows']}))
