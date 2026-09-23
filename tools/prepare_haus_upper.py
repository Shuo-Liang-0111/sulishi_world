"""Use existing source geometry to extend the built frontage through its roof/corner."""
from pathlib import Path
import json,numpy as np,runpy
from shapely.geometry import Polygon,Point,shape,mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parents[1];D=R/'derived/haus_bellevue';d=json.loads((D/'context.json').read_text());base=json.loads((D/'build_input.json').read_text());f=base['frontage'];O=np.array(d['origin']);C=np.array(f['C']);rt=np.array(f['right']);out=np.array(f['out'])
corner=np.array([2683560.1031889734,1246886.290695432])-O[:2];radius=4.252040983826828
strip=Polygon([C+rt*u+out*v+O[:2] for u,v in [(f['u_min']-.10,1.75),(f['u_max']+.15,1.75),(f['u_max']+.15,-6.1),(f['u_min']-.10,-6.1)]])
angles=np.radians(np.linspace(-100,55,110));wedge=Polygon([corner+O[:2],*[corner+O[:2]+(radius+.95)*np.array([np.cos(a),np.sin(a)]) for a in angles]])
mask=unary_union([strip,wedge]);pieces=[];interpolated_vertices=0;max_interpolation_plane_residual=0.
def triangles(poly3):
 global interpolated_vertices,max_interpolation_plane_residual
 ring=np.array(poly3[0],dtype=float);n=np.zeros(3)
 for a,b in zip(ring, np.roll(ring,-1,axis=0)):n+=np.cross(a-O,b-O)
 if np.linalg.norm(n)<1e-10:return
 drop=int(np.argmax(abs(n)));axes=[i for i in range(3) if i!=drop];p=Polygon(ring[:,axes],holes=[np.array(h)[:,axes] for h in poly3[1:]])
 if not p.is_valid:p=p.buffer(0)
 for t in constrained_delaunay_triangles(p).geoms:
  coords=np.array(t.exterior.coords)[:3];vv=[]
  for q in coords:
   j=np.argmin(np.linalg.norm(ring[:,axes]-q,axis=1))
   if np.linalg.norm(ring[j,axes]-q)<1e-5:vv.append(ring[j])
   else:
    v3=ring[0].copy();v3[axes]=q;v3[drop]=ring[0,drop]-np.dot(n[axes],q-ring[0,axes])/n[drop];vv.append(v3);interpolated_vertices+=1
    max_interpolation_plane_residual=max(max_interpolation_plane_residual,float(np.max(abs((ring-ring[0])@n/np.linalg.norm(n)))))
  yield np.array(vv)
def subtri(tri,mask):
 p=Polygon(tri[:,:2]);normal=np.cross(tri[1]-tri[0],tri[2]-tri[0])
 if p.area<1e-10:
  if mask.covers(Point(tri[:,:2].mean(axis=0))):yield tri
  return
 inter=p.intersection(mask)
 for g in ([inter] if inter.geom_type=='Polygon' else getattr(inter,'geoms',[])):
  if g.geom_type!='Polygon' or g.area<1e-8:continue
  for t in constrained_delaunay_triangles(g).geoms:
   xy=np.array(t.exterior.coords)[:3,:2];w=np.linalg.solve((tri[1:,:2]-tri[0,:2]).T,(xy-tri[0,:2]).T).T;vv=tri[0]+w[:,0,None]*(tri[1]-tri[0])+w[:,1,None]*(tri[2]-tri[0])
   if np.dot(np.cross(vv[1]-vv[0],vv[2]-vv[0]),normal)<0:vv=vv[::-1]
   yield vv
for feat in d['building_surfaces']:
 typ=feat['properties']['type']
 if typ not in ['RoofSurface','WallSurface']:continue
 for poly in feat['geometry']['coordinates']:
  for tri in triangles(poly):
   if tri[:,2].max()<429.80:continue
   if typ=='WallSurface' and tri[:,2].min()<429.5:continue
   for vv in subtri(tri,mask):
    if vv[:,2].min()<428.7:continue
    n=np.cross(vv[1]-vv[0],vv[2]-vv[0]);nn=n/np.linalg.norm(n);slate=typ=='RoofSurface' and abs(nn[2])<.98
    key='slate' if slate else 'roof_metal' if typ=='RoofSurface' else 'dormer_wall'
    if typ=='RoofSurface' and nn[2]<0:vv=vv[::-1];nn=-nn
    u=np.array([rt[0],rt[1],0]);u=u-nn*np.dot(u,nn)
    if np.linalg.norm(u)<.05:u=np.cross(nn,[0,0,1])
    u/=np.linalg.norm(u);v=np.cross(nn,u);local=vv-O
    pieces.append({'source':feat['id'],'kind':key,'triangles':[local.tolist()],'uv':[[[(float(p@u))/3,(float(p@v))/3] for p in local]]})
info={'frontage':f,'corner':{'center_local':corner.tolist(),'radius_m':radius,'visible_angles_deg':[-96.03,53.0],'basis':'Circle fitted to existing AV exterior arc; upper ornamental projections and window joinery inferred.'},'roof_pieces':pieces,'cut_mask_lv95':mapping(mask),'levels':[{'name':'MEZZ','bottom':4.95,'top':8.12,'sill':5.54,'head':7.40},{'name':'PIANO','bottom':8.12,'top':12.85,'sill':8.92,'head':11.85},{'name':'SECOND','bottom':12.85,'top':17.15,'sill':13.53,'head':16.25},{'name':'TOP','bottom':17.15,'top':21.555,'sill':17.87,'head':20.08}],'basis':'Existing AV identity/bay rhythm, official roof geometry and already-viewed SPPA facade photo. Floor subdivisions and joinery/ornament dimensions are photo-informed inference, not architectural survey.'}
info['triangulation_audit']={'interpolated_vertices':interpolated_vertices,'max_source_face_plane_residual_m':max_interpolation_plane_residual,'note':'Repair and intersection vertices interpolate source face planes; original vertices otherwise retained.'}
(D/'upper_input.json').write_text(json.dumps(info,separators=(',',':')))
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':413.34,'CUT_UPPER':437.0,'CUT_BASE':'haus_walk_mast_photo_cut.json','CUT_OUTPUT':'haus_upper_photo_cut.json','CUT_STATS_KEY':'haus_upper','CUT_DESCRIPTION':'Replace the already reconstructed south frontage upper levels/roof strip and AV-fitted exposed corner above413.34 up to437.0m. Exact official roof surfaces retained in rebuilt meshes; adjacent facades and roof outside this mask remain.'})
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':wedge,'CUT_LOWER':408.0,'CUT_UPPER':413.34,'CUT_BASE':'haus_upper_photo_cut.json','CUT_OUTPUT':'haus_upper_corner_photo_cut.json','CUT_STATS_KEY':'haus_corner_base','CUT_DESCRIPTION':'Rebuild the exposed corner ground floor within the same surveyed curved footprint, preserving the source reference collection.'})
print(json.dumps({'roof_triangles':len(pieces),'mask_area_m2':mask.area,'corner':info['corner']}))
