"""Grounded station-road geometry. XY is cadastral; Z is explicitly inferred from photo ground.

No change to original meshes. The paired native author must remove the corresponding
working-context ground only after inspecting this support and the resulting views.
"""
import json,struct
from pathlib import Path
from functools import lru_cache
import numpy as np
from shapely.geometry import shape,box,Point,mapping,Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles,contains_xy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/transport'
ORIGIN=np.array([2683775,1246700,400.]);CENTER=np.array([2683575.,1246838.])
AREA=box(2683500,1246765,2683650,1246910)
cad=json.loads((ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
regions=[{'id':f['id'],'polygon':shape(f['geometry']).intersection(AREA)} for f in cad if f['properties']['art_txt']=='befestigt.Strasse_Weg.Strasse' and f['properties']['status_txt']=='real' and shape(f['geometry']).intersects(AREA)]
road=unary_union([r['polygon'] for r in regions]);manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
tri=[]
for item in manifest['items']:
    m=item['mbs']
    if Point(m[:2]).distance(AREA)>m[3]:continue
    raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
    v=(np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+np.array(m[:3])).reshape(-1,3,3)
    cross=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);length=np.linalg.norm(cross,axis=1)
    ok=(v[:,:,2].min(axis=1)>407.3)&(v[:,:,2].max(axis=1)<409.2)&(np.abs(cross[:,2])>.92*np.maximum(length,1e-10))
    v=v[ok];centers=v.mean(axis=1);ok=contains_xy(road.buffer(-.22),centers[:,0],centers[:,1]);tri.extend(v[ok])
tri=np.array(tri);samples=tri.mean(axis=1)
# Equalise density so highly tessellated seams do not dominate the local grade.
cells={}
for p in samples:cells.setdefault(tuple(np.floor((p[:2]-CENTER)/.7).astype(int)),[]).append(p)
samples=np.array([np.median(v,axis=0) for v in cells.values()]);xy=samples[:,:2]-CENTER;zz=samples[:,2]
assert len(samples)>500,'Insufficient actual ground support'
raw_samples=samples.copy();q=xy/50
design=np.c_[np.ones(len(q)),q,q[:,0]**2,q[:,0]*q[:,1],q[:,1]**2];weights=np.ones(len(q))
for _ in range(12):
    trend=np.linalg.lstsq(design*weights[:,None],zz*weights,rcond=None)[0]
    residual=zz-design@trend;weights=np.minimum(1,.065/np.maximum(abs(residual),1e-8))
support=np.abs(residual)<.20
samples=samples[support];xy=samples[:,:2]-CENTER;zz=samples[:,2]
assert len(samples)>1000,'Regional grade filtering left too little support'
def local_fit(e,n):
    d=xy-np.array([e,n]);distance=np.linalg.norm(d,axis=1);idx=np.argpartition(distance, min(55,len(distance)-1))[:55]
    a=np.c_[d[idx],np.ones(len(idx))];z=zz[idx];base=1/(1+(distance[idx]/4)**2);w=base.copy()
    qe,qn=e/50,n/50
    prior_z=float(np.array([1,qe,qn,qe*qe,qe*qn,qn*qn])@trend)
    prior_gradient=np.array([trend[1]+2*trend[3]*qe+trend[4]*qn,trend[2]+trend[4]*qe+2*trend[5]*qn])/50
    # Narrow parallel strips and occluded road patches do not determine arbitrary
    # transverse slopes. Regularise that ill-conditioned fit to the observed
    # regional grade instead of extrapolating metre-high ridges between samples.
    prior_a=np.diag([50.,50.,1.2]);prior_b=np.r_[prior_gradient*50,prior_z*1.2]
    for _ in range(5):
        fit=np.linalg.lstsq(np.vstack([a*w[:,None],prior_a]),np.r_[z*w,prior_b],rcond=None)[0];res=z-a@fit;w=base*np.minimum(1,.055/np.maximum(abs(res),1e-7))
    return float(fit[2])
# Interpolate a regular grade grid rather than switching nearest-neighbour sets at
# arbitrary mesh vertices (that can create millimetre cliffs along narrow rails).
gx=np.arange(-78,79,2.);gy=np.arange(-76,77,2.)
grid=np.array([[local_fit(x,y) for x in gx] for y in gy])
@lru_cache(maxsize=None)
def height(e,n):
    ix=max(0,min(len(gx)-2,int(np.floor((e-gx[0])/2))));iy=max(0,min(len(gy)-2,int(np.floor((n-gy[0])/2))))
    tx=(e-gx[ix])/2;ty=(n-gy[iy])/2
    if tx+ty<=1:return float(grid[iy,ix]*(1-tx-ty)+grid[iy,ix+1]*tx+grid[iy+1,ix]*ty)
    return float(grid[iy+1,ix+1]*(tx+ty-1)+grid[iy+1,ix]*(1-tx)+grid[iy,ix+1]*(1-ty))
def z_at(e,n):return height(e-CENTER[0],n-CENTER[1])
def polygons(g):return [p for p in (g.geoms if hasattr(g,'geoms') else [g]) if p.geom_type=='Polygon' and p.area>1e-8]
def surface(g,dz=0):
    out=[]
    if g.is_empty:return out
    b=g.bounds
    for x in CENTER[0]+gx[:-1]:
        if x+2<b[0] or x>b[2]:continue
        for y in CENTER[1]+gy[:-1]:
            if y+2<b[1] or y>b[3]:continue
            if not g.intersects(box(x,y,x+2,y+2)):continue
            for tile in [Polygon([(x,y),(x+2,y),(x,y+2)]),Polygon([(x+2,y+2),(x,y+2),(x+2,y)])]:
                for p in polygons(g.intersection(tile)):
                    for t in constrained_delaunay_triangles(p).geoms:
                        coords=[[e-ORIGIN[0],n-ORIGIN[1],z_at(e,n)+dz-ORIGIN[2]] for e,n in list(t.exterior.coords)[:3]]
                        if np.cross(np.array(coords[1])-coords[0],np.array(coords[2])-coords[0])[2]<0:coords.reverse()
                        out.append(coords)
    return out
rails=json.loads((ROOT/'sources/features/vbz/strecke_schienen.geojson').read_text())['features']
rail_lines=[{'id':f['id'],'g':shape(f['geometry']).intersection(road)} for f in rails if shape(f['geometry']).intersects(road)]
rail_lines=[r for r in rail_lines if r['g'].length>.04]
heads=unary_union([r['g'].buffer(.0325,cap_style=2,join_style=2) for r in rail_lines]).intersection(road)
channels=unary_union([r['g'].buffer(.0825,cap_style=2,join_style=2) for r in rail_lines]).intersection(road)
pieces=[]
for r in regions:pieces.append({'id':r['id'],'triangles':surface(r['polygon'].difference(channels)),'kind':'road_asphalt'})
pieces.extend([{'id':'VBZ_rail_head_union','triangles':surface(heads,.003),'kind':'rail_steel'}, {'id':'VBZ_rail_channel_floor','triangles':surface(channels.difference(heads),-.035),'kind':'groove_floor'}])
# Actual vertical groove walls, not a black road decal. Profile is a reconstruction.
walls=[]
for g in [channels,heads]:
    for p in polygons(g):
        for ring in [p.exterior,*p.interiors]:
            coords=list(ring.coords)
            for a,b in zip(coords,coords[1:]):
                za=z_at(*a)-400;zb=z_at(*b)-400
                v=[[a[0]-ORIGIN[0],a[1]-ORIGIN[1],za+.003],[b[0]-ORIGIN[0],b[1]-ORIGIN[1],zb+.003],[b[0]-ORIGIN[0],b[1]-ORIGIN[1],zb-.035],[a[0]-ORIGIN[0],a[1]-ORIGIN[1],za-.035]]
                walls.extend([[v[0],v[1],v[2]],[v[0],v[2],v[3]]])
pieces.append({'id':'VBZ_rail_channel_walls','triangles':walls,'kind':'groove_wall'})
residual=[z_at(p[0],p[1])-p[2] for p in samples]
report={'bounds':list(AREA.bounds),'road_area_m2':road.area,'road_source_ids':[r['id'] for r in regions],'rail_source_ids':[r['id'] for r in rail_lines],'ground_samples':len(samples),'ground_z_range_ln02':[float(zz.min()),float(zz.max())],'fit_absolute_residual_quantiles_m':np.quantile(abs(np.array(residual)),[.5,.9,.95,1]).tolist(),'height_basis':'Robust local plane from nearly horizontal photographed road-ground samples in LN02 407.3..409.2. Equal .7m sampling; 55 neighbours with regional-gradient regularisation; common piecewise-planar 2m grade grid. Inferred smoothed road grades, not engineering survey.','rail_profile_basis':'Official individual rail lines; inferred 65mm head, 165mm total recess, 35mm groove. Points, frogs and flangeway mechanical details still need reference refinement.','triangles':sum(len(p['triangles']) for p in pieces),'accepted':False}
(OUT/'road_input.json').write_text(json.dumps({'report':report,'road_mask':mapping(road),'pieces':pieces},separators=(',',':')))
report['raw_candidate_samples']=len(raw_samples);report['regional_grade_outliers_rejected']=int((~support).sum())
report['height_basis']+=' First exclude >20cm residuals from a robust quadratic regional grade to reduce flat car-roof/photogrammetric ghosts; preserve these rejected candidates in evidence. Final topology uses common piecewise-planar grade triangles, not bilinear skinny-face interpolation.'
(OUT/'road_candidates.json').write_text(json.dumps({'raw':raw_samples.tolist(),'accepted_support_mask':support.tolist(),'regional_polynomial':trend.tolist()}))
(OUT/'road_input.json').write_text(json.dumps({'report':report,'road_mask':mapping(road),'pieces':pieces},separators=(',',':')))
(OUT/'road_support.json').write_text(json.dumps(report,indent=2))
fig,ax=plt.subplots(figsize=(9,9),layout='constrained');sc=ax.scatter(xy[:,0],xy[:,1],c=zz,s=3,cmap='terrain');fig.colorbar(sc,ax=ax,label='Photo ground LN02 / m');ax.set_aspect('equal');ax.set_title('Measured photo-ground support for inferred station road grades');fig.savefig(OUT/'road_height_support.png',dpi=140)
print(json.dumps(report))
