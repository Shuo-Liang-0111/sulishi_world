"""Bounded replacement of rebuilt ground and15 trees; immutable source retained.

Lower tree cutting is confined to each trunk. Broad crown replacement begins4m
above the new ground, so unbuilt street furniture is not erased by tall masks.
"""
from pathlib import Path
import json,struct,hashlib,sys
import numpy as np
from shapely.geometry import Point,Polygon,shape,mapping,box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from scipy.interpolate import RegularGridInterpolator

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/limmat_sidewalk';d=json.loads((D/'context.json').read_text(encoding='utf-8'));p=json.loads((D/'ground_input.json').read_text(encoding='utf-8'));O=np.array(d['origin']);g=shape(d['source']['geometry'])
refine_low='--low-canopy' in sys.argv
gr=p['grade_grid'];interp=RegularGridInterpolator((gr['x'],gr['y']),gr['z'],bounds_error=False,fill_value=None)
def floor(xy):
 xy=np.asarray(xy)-O[:2];xy=np.clip(xy,[gr['x'][0],gr['y'][0]],[gr['x'][-1],gr['y'][-1]])
 return float(interp(xy.reshape(1,2))[0])+O[2]
features=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
buildings=unary_union([shape(f['geometry']).buffer(.10) for f in features if f['properties']['art_txt'].startswith('Gebaeude') and shape(f['geometry']).distance(g)<20])
alltrees=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
volumes=[{'id':'AV24105_ground','mask':g,'lo':-.24,'hi':.24,'relative':True}]
if refine_low:
 # Actual human-height rays identified remnants of rebuilt trees at1.2..3.1m,
 # not legitimate4m-high obstacles. Protect the unbuilt kiosk incl. its eaves,
 # and cadastral walls/stairs; only clear within the already rebuilt sidewalk.
 guards=[shape(f['geometry']).buffer(1.0) for f in features if f['properties']['art_txt'].startswith('Gebaeude') and shape(f['geometry']).distance(g)<20]
 for f in json.loads((R/'sources/features/av_ei_flaechenelement_a.geojson').read_text())['features']:
  if f['properties']['art_txt'] in ['Mauer.Mauer','wichtige_Treppe'] and shape(f['geometry']).distance(g)<.5:guards.append(shape(f['geometry']).buffer(.18))
 low_guards=unary_union(guards);volumes=[]
records=[]
for tree in p['pits']:
 c=np.array(tree['source']['geometry']['coordinates']);h=tree['height_m'];rad=max(tree['inferred']['crown_radius_m'])+2.4
 area=Point(c).buffer(rad,quad_segs=56)
 for other in alltrees:
  q=np.array(other['geometry']['coordinates']);distance=np.linalg.norm(q-c)
  if distance<.01 or distance>2*rad+5:continue
  n=(q-c)/distance;mid=(q+c)/2;v=np.array([-n[1],n[0]])
  area=area.intersection(Polygon([mid+v*100,mid-v*100,mid-v*100-n*100,mid+v*100-n*100]))
 area=area.difference(buildings)
 ident=tree['source']['id'];ground=tree['ground_ln02_m']
 if refine_low:
  volumes.append({'id':ident+'_low_remnants','mask':area.intersection(g).difference(low_guards),'lo':.12,'hi':4.6,'relative':True})
 else:
  volumes += [{'id':ident+'_crown','mask':area,'lo':ground+4.0,'hi':ground+h+1.25,'relative':False},
              {'id':ident+'_trunk','mask':Point(c).buffer(max(.90,tree['inferred']['trunk_diameter_m']*.9),quad_segs=40).intersection(g).difference(buildings),'lo':-.02,'hi':4.08,'relative':True}]
 records.append({'id':ident,'crown_mask_lv95':mapping(area),'lower_ln02':ground+4,'upper_ln02':ground+h+1.25,'ground_furniture_preserved_below_m':4.0})
basepath=R/'derived/bellevue/west_context'/('limmat_sidewalk_photo_cut.json' if refine_low else 'fountain59_photo_cut.json');base=json.loads(basepath.read_text());overrides={str(x['node']):x for x in base['overrides']};manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());changed=[];counts={v['id']:0 for v in volumes}
def clip(poly,v,above,height):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  az=a[2]-(floor(a[:2]) if v['relative'] else 0)-height;bz=b[2]-(floor(b[:2]) if v['relative'] else 0)-height
  ai=az>=0 if above else az<=0;bi=bz>=0 if above else bz<=0
  if ai:out.append(a)
  if ai!=bi:out.append(a+(b-a)*(az/(az-bz)))
 return out
def fan(poly):return [np.array([poly[0],poly[i],poly[i+1]]) for i in range(1,len(poly)-1)]
def subtract(src,v):
 xy=Polygon(src[:,:2]);mask=v['mask']
 if not xy.intersects(mask):return [src],False
 z=src[:,2]-np.array([floor(q) for q in src[:,:2]]) if v['relative'] else src[:,2]
 if z.min()>=v['hi'] or z.max()<=v['lo']:return [src],False
 low=clip(list(src),v,False,v['hi']);high=clip(list(src),v,True,v['hi']);below=clip(low,v,False,v['lo']);mid=clip(low,v,True,v['lo']);keep=fan(high)+fan(below)
 normal=np.cross(src[1,:3]-src[0,:3],src[2,:3]-src[0,:3]);did=False
 for tri in fan(mid):
  poly=Polygon(tri[:,:2])
  if not poly.is_valid or poly.area<1e-9:
   if not mask.covers(Point(tri[:,:2].mean(0))):keep.append(tri)
   else:did=True
   continue
  diff=poly.difference(mask)
  if diff.area>=poly.area-1e-10:keep.append(tri);continue
  did=True;ab=(tri[1:,:2]-tri[0,:2]).T
  for chunk in ([diff] if diff.geom_type=='Polygon' else getattr(diff,'geoms',[])):
   if chunk.geom_type!='Polygon' or chunk.area<1e-9:continue
   for t in constrained_delaunay_triangles(chunk).geoms:
    pts=np.array(t.exterior.coords)[:3,:2];w=np.linalg.solve(ab,(pts-tri[0,:2]).T).T;out=tri[0]+w[:,0,None]*(tri[1]-tri[0])+w[:,1,None]*(tri[2]-tri[0])
    if np.dot(np.cross(out[1,:3]-out[0,:3],out[2,:3]-out[0,:3]),normal)<0:out=out[::-1]
    keep.append(out)
 return (keep,True) if did else ([src],False)

for item in manifest['items']:
 m=np.array(item['mbs']);near=[v for v in volumes if Point(m[:2]).distance(v['mask'])<=m[3]]
 if not near:continue
 key=str(item['node'])
 if key in overrides:
  q=overrides[key];xyz=np.asarray(q['vertices']).reshape(-1,3);uv=np.asarray(q['uv_source_v_unflipped']).reshape(-1,2)
 else:
  raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0];xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3);uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2)
 vv=[];uu=[];dirty=False
 for tri,tex in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
  pieces=[np.c_[tri,tex]]
  for v in near:
   nextpieces=[]
   for piece in pieces:
    out,did=subtract(piece,v);nextpieces.extend(out)
    if did:dirty=True;counts[v['id']]+=1
   pieces=nextpieces
  for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
 if dirty:
  overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']};changed.append(key)
  print('Bounded node replacement',key,flush=True)
description='; G1_019r2 actual same-camera ray diagnosis: remove lower photographic remnants of replaced trees only above rebuilt AV24105, floor+0.12..4.6m, tree bisectors retained; preserve building/eaves1m and official wall/stair guards. Original2039 source nodes retained.' if refine_low else '; G1_019 AV24105 ground only within fitted floor-0.24..+0.24m; each new tree bounded by neighboring tree bisectors and building guards; broad crown cuts start4m above root, lower cuts only at trunk. Original2039 source meshes retained.'
result={'mask_basis':base['mask_basis']+description,'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),'changed_nodes':len(overrides),'limmat_changed_nodes':changed,'limmat_counts':counts}
out=R/'derived/bellevue/west_context'/('limmat_sidewalk_low_canopy_cut.json' if refine_low else 'limmat_sidewalk_photo_cut.json');out.write_text(json.dumps(result,separators=(',',':')))
(D/('low_canopy_basis.json' if refine_low else 'cut_basis.json')).write_text(json.dumps({'base_version':'G1_019r1' if refine_low else 'G1_018r3','base_cut':str(basepath.relative_to(R)),'trees':records,'ground_geometry_lv95':d['source']['geometry'],'changed_nodes':changed,'source_cut_file':str(out.relative_to(R)),'original_sources_untouched':True,'building_wall_stair_guards':mapping(low_guards) if refine_low else None},indent=2))
print(json.dumps({'changed':len(changed),'total_overrides':len(overrides),'cut':str(out)}))
