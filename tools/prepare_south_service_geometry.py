"""Align dated service-building reference to retained official geometry."""
from pathlib import Path
import json,hashlib,ast,numpy as np
from shapely.geometry import shape,Polygon,mapping,Point
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_service';D.mkdir(parents=True,exist_ok=True);O=np.array([2683775,1246700,400.]);fs=json.loads((R/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features'];fs=[f for f in fs if f['properties'].get('egid')==302040350]
ground=next(f for f in fs if f['properties']['type']=='GroundSurface' and f['properties']['art']=='BB04');poly=unary_union([Polygon(np.array(p[0])[:,:2]) for p in ground['geometry']['coordinates']]);C=np.array(poly.centroid.coords[0]);ring=np.array(poly.exterior.coords)[:,:2];deltas=np.diff(ring,axis=0);u=deltas[np.argmax(np.linalg.norm(deltas,axis=1))];u=u/np.linalg.norm(u)
if u[0]<0:u=-u
v=np.array([-u[1],u[0]])
def xy(q):return np.c_[(q-C)@u,(q-C)@v]
# Existing general source-plane triangulation preserves actual roof geometry.
src=ast.parse((R/'tools/prepare_bellevue_block.py').read_text(encoding='utf-8'));ORIGIN=O;exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='triangulate'],type_ignores=[]),'triangulation','exec'))
parts=[];summary=[]
for f in fs:
 tt=[t for p in f['geometry']['coordinates'] for t in triangulate(p)];pp=np.array([p for face in f['geometry']['coordinates'] for r in face for p in r]);uv=xy(pp[:,:2]);summary.append({'id':f['id'],'type':f['properties']['type'],'kind':f['properties']['art_txt'],'uv_bounds':[uv.min(0).tolist(),uv.max(0).tolist()],'z_bounds_ln02':[float(pp[:,2].min()),float(pp[:,2].max())]})
 parts.append({'id':f['id'],'type':f['properties']['type'],'kind':f['properties']['art'],'triangles':tt})
roof=next(f for f in fs if f['properties']['type']=='RoofSurface' and f['properties']['art']=='EO13');roofplan=unary_union([Polygon(np.array(p[0])[:,:2]) for p in roof['geometry']['coordinates']]);cad=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features'];foot=shape(next(f['geometry'] for f in cad if f['id']=='av_bo_boflaeche_a.75249'));walk=shape(next(f['geometry'] for f in cad if f['id']=='av_bo_boflaeche_a.3573'));addr=next(f for f in json.loads((R/'sources/features/av_geb_gebaeudeadresse_t.geojson').read_text())['features'] if f['properties'].get('gwr_egid')==302040350);addr_uv=xy(np.array([addr['geometry']['coordinates']]))[0]
p=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text());tt=np.array(p['parts']['asphalt']+p['parts']['curb_top']);centres=tt[:,:,:2].mean(1)
def support(q):
 q=np.array(q)-O[:2]
 for idx in np.argsort(np.linalg.norm(centres-q,axis=1))[:80]:
  t=tt[idx];A=(t[1:,:2]-t[0,:2]).T
  if abs(np.linalg.det(A))<1e-10:continue
  w=np.linalg.solve(A,q-t[0,:2])
  if min(w)>=-1e-6 and sum(w)<=1.000001:return float(t[0,2]+w@(t[1:,2]-t[0,2]))
 return None
samples=[]
for i in range(80):
 q=np.array(foot.buffer(.08).exterior.interpolate(i*foot.buffer(.08).exterior.length/80).coords[0]);z=support(q)
 if z is not None:samples.append([*q,z])
floor=float(np.median([z[2] for z in samples]))+.025
record={'egid':302040350,'address':'Bellevueplatz2','origin':O.tolist(),'center_lv95':C.tolist(),'axis_u':u.tolist(),'axis_v':v.tolist(),'source_parts':parts,'source_summary':summary,'building_plan_lv95':mapping(poly),'av_footprint_lv95':mapping(foot),'canopy_plan_lv95':mapping(roofplan),'address_point':addr,'address_point_uv':addr_uv.tolist(),'floor_local_inferred':floor,'perimeter_ground_samples':samples,'basis':'Retained official2025 geometry/AV footprint and address;2015 municipal WC plan/photo supports use and facade logic. Floor at existing reconstructed street grade, not source extruded volume bottom405.029. Flat floor, exact bay/door/fabrication dimensions and finishes inferred. Historical plan is not current as-built proof.','accepted':False}
(D/'input.json').write_text(json.dumps(record,separators=(',',':')))
fig,axes=plt.subplots(1,3,figsize=(15,5));ax=axes[0]
for g,color in [(poly,'black'),(foot,'red'),(roofplan,'blue')]:
 for pp in ([g] if g.geom_type=='Polygon' else g.geoms):
  q=xy(np.array(pp.exterior.coords)[:,:2]);ax.plot(q[:,0],q[:,1],color=color)
ax.scatter(*addr_uv,color='green');ax.set_aspect('equal');ax.set_title('Official body black / AV red / canopy blue')
for part in parts:
 if part['type']!='RoofSurface':continue
 t=np.array(part['triangles'])+O;q=xy(t[:,:,:2].reshape(-1,2)).reshape(-1,3,2)
 axes[1].scatter(q[:,:,0].ravel(),t[:,:,2].ravel(),s=3);axes[2].scatter(q[:,:,1].ravel(),t[:,:,2].ravel(),s=3)
axes[1].set_title('Roof longitudinal profile');axes[2].set_title('Roof transverse profile');fig.tight_layout();fig.savefig(D/'source_alignment.png',dpi=150);plt.close(fig)
print(json.dumps({'center':C.tolist(),'axes':[u.tolist(),v.tolist()],'floor_local':floor,'ground_range':[min(x[2] for x in samples),max(x[2] for x in samples)],'av_area':foot.area,'body_area':poly.area,'canopy_area':roofplan.area,'address_uv':addr_uv.tolist(),'parts':summary}))
