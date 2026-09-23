"""Remove only the photographic surface volume replaced by the AV145 works."""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from shapely.geometry import Point,Polygon,shape
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/riviera_quay'
p=json.loads((D/'build_input.json').read_text());source=json.loads((D/'sources.json').read_text())
mask=unary_union([shape(f['geometry']) for f in source['features'] if f['id'] in
 ['av_bo_boflaeche_a.145','av_ei_flaechenelement_a.35398','av_ei_flaechenelement_a.18091']])
basepath=R/'derived/bellevue/west_context/utoquai_kiosk_roof_cut.json'
base=json.loads(basepath.read_text());overrides={str(r['node']):r for r in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
def clip(poly,height,above):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  av=a[2]-height;bv=b[2]-height;ai=av>=0 if above else av<=0;bi=bv>=0 if above else bv<=0
  if ai:out.append(a)
  if ai!=bi:out.append(a+(b-a)*(av/(av-bv)))
 return out
def fan(p):return [np.array([p[0],p[i],p[i+1]]) for i in range(1,len(p)-1)]
def subtract(src):
 poly=Polygon(src[:,:2])
 if not poly.intersects(mask) or src[:,2].min()>408.25 or src[:,2].max()<404.9:return [src],False
 lower=clip(list(src),408.25,False);upper=clip(list(src),408.25,True)
 under=clip(lower,404.9,False);middle=clip(lower,404.9,True)
 keep=fan(upper)+fan(under);changed=False
 normal=np.cross(src[1,:3]-src[0,:3],src[2,:3]-src[0,:3])
 for tri in fan(middle):
  g=Polygon(tri[:,:2])
  if not g.is_valid or g.area<1e-10:
   if not mask.covers(Point(tri[:,:2].mean(0))):keep.append(tri)
   else:changed=True
   continue
  difference=g.difference(mask)
  if difference.area>=g.area-1e-10:keep.append(tri);continue
  changed=True;ab=(tri[1:,:2]-tri[0,:2]).T
  for q in ([difference] if difference.geom_type=='Polygon' else getattr(difference,'geoms',[])):
   if q.geom_type!='Polygon' or q.area<1e-10:continue
   for tr in constrained_delaunay_triangles(q).geoms:
    v=np.array(tr.exterior.coords)[:3];w=np.linalg.solve(ab,(v-tri[0,:2]).T).T
    result=tri[0]+w[:,0,None]*(tri[1]-tri[0])+w[:,1,None]*(tri[2]-tri[0])
    if np.dot(np.cross(result[1,:3]-result[0,:3],result[2,:3]-result[0,:3]),normal)<0:result=result[::-1]
    keep.append(result)
 return (keep,True) if changed else ([src],False)
changed=[]
for item in manifest['items']:
 m=np.array(item['mbs']);key=str(item['node'])
 if Point(m[:2]).distance(mask)>m[3]:continue
 if key in overrides:
  q=overrides[key];xyz=np.asarray(q['vertices']).reshape(-1,3);uv=np.asarray(q['uv_source_v_unflipped']).reshape(-1,2)
 else:
  raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
  xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)
  uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2)
 vertices=[];tex=[];dirty=False
 for tr,tt in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
  pieces,did=subtract(np.c_[tr,tt]);dirty=dirty or did
  for part in pieces:vertices.extend((part[:,:3]-m[:3]).tolist());tex.extend(part[:,3:].tolist())
 if dirty:
  overrides[key]={'node':item['node'],'vertices':vertices,'uv_source_v_unflipped':tex,'source_sha256':item['geometry_sha256']};changed.append(key)
result={'mask_basis':base['mask_basis']+'; G1_021 exact AV145 promenade + AV35398 stair +18091 wall, only LN02 404.9..408.25 replaced surface volume; upper photography/permanent context outside footprint retained.',
 'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),'changed_nodes':len(overrides),'riviera_changed_nodes':changed}
out=R/'derived/bellevue/west_context/riviera_quay_photo_cut.json';out.write_text(json.dumps(result,separators=(',',':')))
(D/'cut_basis.json').write_text(json.dumps({'base_cut':str(basepath.relative_to(R)),'changed_nodes':changed,'mask_area_m2':mask.area,'height_band_ln02':[404.9,408.25],
 'all_original_sources_preserved':True,'unrebuilt_curved_lower_path_40750_preserved':True,'source_geometry_not_deleted':True},indent=2))
print(json.dumps({'changed_nodes':len(changed),'total_overrides':len(overrides),'bytes':out.stat().st_size}))
