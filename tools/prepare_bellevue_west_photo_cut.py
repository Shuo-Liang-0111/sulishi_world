"""Bounded low-ground replacement; retain overhead and upright photo structures."""
import json,struct,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,Point
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context'
platform=json.loads((OUT/'platform_input.json').read_text());coef=np.array(platform['report']['robust_plane_local']);O=np.array([2683775,1246700,400])
mask=shape(platform['geometry_lv95']).difference(Point(2683532.398,1246843.141).buffer(1.03))
basepath=ROOT/'derived/bellevue/transport/photo_cut.json';base=json.loads(basepath.read_text());overrides={str(o['node']):o for o in base['overrides']}
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());stats={'changed_west_nodes':0,'removed_ground_triangles':0,'retessellated_ground_triangles':0,'preserved_high_or_upright_triangles':0}
for item in manifest['items']:
 m=np.array(item['mbs']);key=str(item['node'])
 if Point(m[:2]).distance(mask)>m[3]:continue
 if key in overrides:
  p=overrides[key];xyz=np.array(p['vertices']);uv=np.array(p['uv_source_v_unflipped'])
 else:
  raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
  xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3).astype(float)
  uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2).copy()
 world=(xyz+m[:3]).reshape(-1,3,3);ut=uv.reshape(-1,3,2);vv=[];uu=[];changed=False
 def keep(t,u):vv.extend((t-m[:3]).tolist());uu.extend(u.tolist())
 for tri,tex in zip(world,ut):
  poly=Polygon(tri[:,:2]);local=tri-O;dz=local[:,2]-(local[:,:2]@coef[:2]+coef[2]);n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);length=np.linalg.norm(n)
  upright=length>1e-10 and abs(n[2])/length<.5 and np.ptp(tri[:,2])>.12
  # The source tree pit and bases of substantial upright surfaces remain. This
  # pass does not remove tree crowns or station roofs using a 2D mask alone.
  if not poly.is_valid or poly.area<1e-9 or not poly.intersects(mask):keep(tri,tex);continue
  if max(dz)>.35 or upright:
   stats['preserved_high_or_upright_triangles']+=1;keep(tri,tex);continue
  diff=poly.difference(mask)
  if abs(diff.area-poly.area)<1e-9:keep(tri,tex);continue
  changed=True
  if diff.is_empty or diff.area<1e-9:stats['removed_ground_triangles']+=1;continue
  stats['retessellated_ground_triangles']+=1
  matrix=np.column_stack([tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2]])
  for piece in ([diff] if diff.geom_type=='Polygon' else diff.geoms):
   if piece.geom_type!='Polygon' or piece.area<1e-9:continue
   for sub in constrained_delaunay_triangles(piece).geoms:
    xy=np.array(list(sub.exterior.coords)[:3]);w=np.linalg.solve(matrix,(xy-tri[0,:2]).T).T
    t=tri[0]+w[:,0,None]*(tri[1]-tri[0])+w[:,1,None]*(tri[2]-tri[0]);u=tex[0]+w[:,0,None]*(tex[1]-tex[0])+w[:,1,None]*(tex[2]-tex[0])
    if np.dot(np.cross(t[1]-t[0],t[2]-t[0]),n)<0:t=t[::-1];u=u[::-1]
    keep(t,u)
 if changed:
  stats['changed_west_nodes']+=1;overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']}
result={'mask_basis':base['mask_basis']+' West AV459: only low ground triangles up to photo-supported plane +0.35m, retaining upright and overhead structures and surveyed tree pit. Earlier road-mask upper-volume limitation is not repaired in this pass.','base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'west_stats':stats,'changed_nodes':len(overrides),'overrides':list(overrides.values())}
(OUT/'photo_cut.json').write_text(json.dumps(result,separators=(',',':')));print(json.dumps({k:v for k,v in result.items() if k!='overrides'}))
