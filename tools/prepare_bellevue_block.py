"""Prepare a surveyed pavilion block and local height evidence, without moving sources."""
import json, struct
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon, Point, shape, box, mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT=Path(__file__).resolve().parents[1]
ORIGIN=np.array([2683775,1246700,400.])
CENTER=np.array([2683575.170093618,1246838.03454272])
OUT=ROOT/'derived/bellevue';OUT.mkdir(exist_ok=True)
features=json.loads((ROOT/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features']
features=[f for f in features if f['properties'].get('egid')==2376968]
byid={f['id'].split('.')[-1]:f for f in features}

def project(f):
    return unary_union([Polygon(np.asarray(p[0])[:,:2],[np.asarray(r)[:,:2] for r in p[1:]])
                        for p in f['geometry']['coordinates']])

def triangulate(rings):
    pts=np.asarray(rings[0]); normal=np.cross(pts[:-1]-pts[0],pts[1:]-pts[0]).sum(axis=0)
    axis=int(np.argmax(np.abs(normal))); keep=[i for i in range(3) if i!=axis]
    poly=Polygon(pts[:,keep],[np.asarray(r)[:,keep] for r in rings[1:]])
    lookup={tuple(np.asarray(p)[keep]):np.asarray(p) for r in rings for p in r}
    out=[]
    if poly.area<1e-8:return out
    for t in constrained_delaunay_triangles(poly).geoms:
        tri=[]
        for xy in list(t.exterior.coords)[:3]:
            if xy in lookup:p=lookup[xy]
            else:
                p=pts[0].copy();p[keep]=xy
                p[axis]=pts[0,axis]-np.dot(normal[keep],p[keep]-pts[0,keep])/normal[axis]
            tri.append((p-ORIGIN).tolist())
        if np.dot(np.cross(np.array(tri[1])-tri[0],np.array(tri[2])-tri[0]),normal)<0:tri.reverse()
        out.append(tri)
    return out

canopy=project(byid['153133']);disk=project(byid['186629']);roof=canopy.union(disk)
cad=json.loads((ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
island_feature=next(f for f in cad if f['id']=='av_bo_boflaeche_a.106987')
island=shape(island_feature['geometry'])
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
tris=[]
for item in manifest['items']:
    m=item['mbs']
    if Point(m[:2]).distance(island)>m[3]+4:continue
    raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
    v=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+np.array(m[:3])
    tris.append(v.reshape(-1,3,3))
tris=np.concatenate(tris)
# Only hard-ground candidates in plausible LN02 band; tree/roof/vehicle surfaces are excluded.
mask=(tris[:,:,2].max(axis=1)<409.1)&(tris[:,:,2].min(axis=1)>407.4)
tris=tris[mask]
mins=tris[:,:,:2].min(axis=1);maxs=tris[:,:,:2].max(axis=1)
def photo_z(p):
    ts=tris[((mins<=p).all(axis=1))&((maxs>=p).all(axis=1))]
    if not len(ts):return None
    a=ts[:,0,:2]; b=ts[:,1,:2]-a;c=ts[:,2,:2]-a;v=p-a
    d=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=np.abs(d)>1e-8;d=np.where(valid,d,1)
    u=(v[:,0]*c[:,1]-v[:,1]*c[:,0])/d;w=(b[:,0]*v[:,1]-b[:,1]*v[:,0])/d
    ok=valid&(u>=-1e-5)&(w>=-1e-5)&(u+w<=1.00001)
    zs=ts[:,0,2]+u*(ts[:,1,2]-ts[:,0,2])+w*(ts[:,2,2]-ts[:,0,2])
    return float(np.median(zs[ok])) if ok.any() else None

exposed=island.buffer(-.45).difference(roof.buffer(.6))
samples=[]
for x in np.arange(island.bounds[0],island.bounds[2],.8):
    for y in np.arange(island.bounds[1],island.bounds[3],.8):
        if not exposed.contains(Point(x,y)):continue
        z=photo_z(np.array([x,y]))
        if z is not None:samples.append([x,y,z])
samples=np.array(samples);local=samples[:,:2]-CENTER
a=np.c_[local,np.ones(len(samples))];weights=np.ones(len(samples))
for _ in range(8):
    coeff=np.linalg.lstsq(a*weights[:,None],samples[:,2]*weights,rcond=None)[0]
    residual=samples[:,2]-a@coeff
    weights=np.minimum(1,.08/np.maximum(abs(residual),1e-8))
inliers=abs(residual)<.15
report={'center_lv95':CENTER.tolist(),'ground_plane_z_ln02':coeff.tolist(),
        'plane_formula':'a*(E-centerE)+b*(N-centerN)+c',
        'method':'Robust fit of exposed photogrammetric hard-ground candidates inside official island, outside canopy; .8m sampling. Approximation, not surveyed thresholds.',
        'samples':len(samples),'inliers_15cm':int(inliers.sum()),
        'inlier_rmse_m':float(np.sqrt(np.mean(residual[inliers]**2))),
        'all_max_abs_residual_m':float(abs(residual).max()),
        'source_ground_role':'local reconstruction support; exact door threshold remains inferred',
        'island_id':island_feature['id'],'roof_area_m2':roof.area,
        'canopy_source_ids':[byid[i]['id'] for i in ['153133','176359','216390']],
        'roof_top_source':byid['111603']['id'],'samples_file':'ground_samples.json'}
(OUT/'ground_samples.json').write_text(json.dumps(samples.tolist()))
(OUT/'ground_fit.json').write_text(json.dumps(report,indent=2))

parts=[]
for key in ['153133','176359','216390','111603']:
    f=byid[key];tri=[t for p in f['geometry']['coordinates'] for t in triangulate(p)]
    parts.append({'id':f['id'],'type':f['properties']['type'],'triangles':tri})
supports=[]
for approximate in [(-14,-4.5),(11.6,-9),(2,14.2)]:
    cap=[]; z_values=[]
    for rings in byid['216390']['geometry']['coordinates']:
        xyz=np.asarray(rings[0]);poly=Polygon(xyz[:,:2])
        if np.ptp(xyz[:,2])<1e-5 and Point(CENTER+approximate).distance(poly.centroid)<2.5:
            cap.append(poly);z_values.append(float(xyz[0,2]))
    g=unary_union(cap)
    supports.append({'center_lv95':list(g.centroid.coords[0]),'cap_z_ln02':float(np.median(z_values)),
                     'cap_area_m2':g.area,'cap_outline':mapping(g),
                     'position_basis':'constant-height circular patches in official canopy underside; support interpretation checked against photos',
                     'shaft_radius_m':.19,'shaft_radius_basis':'photo proportion, inferred; not survey diameter'})
context=box(CENTER[0]-48,CENTER[1]-45,CENTER[0]+48,CENTER[1]+45)
ground_regions=[]
for f in cad:
    g=shape(f['geometry']).intersection(context)
    if g.is_empty or g.area<.01:continue
    ground_regions.append({'id':f['id'],'properties':f['properties'],'geometry':mapping(g)})
payload={'origin':ORIGIN.tolist(),'center_lv95':CENTER.tolist(),'source_parts':parts,
         'roof_outline':mapping(roof),'core_outline':mapping(disk),'island':mapping(island),
         'ground_fit':report,'ground_regions':ground_regions,'supports':supports,
         'construction_context':mapping(context),'quality':'derived evidence; not accepted construction'}
# Surface reconstruction retains the island's ramped tips instead of flattening all samples.
footprint=island.union(disk)
def ground_height(x,y):
    p=np.array([x,y]);offset=p-CENTER;plane=float(np.r_[offset,1]@coeff)
    near=np.linalg.norm(samples[:,:2]-p,axis=1)
    order=np.argsort(near)[:9]
    local_z=float(np.median(samples[order,2]))
    # Interior below canopy is hidden from aerial capture; use the supported platform fit.
    distance=roof.distance(Point(x,y))
    blend=min(1,distance/2.0)
    return plane*(1-blend)+local_z*blend
surface=[]
for x in np.arange(np.floor(footprint.bounds[0]),footprint.bounds[2],2):
    for y in np.arange(np.floor(footprint.bounds[1]),footprint.bounds[3],2):
        g=footprint.intersection(box(x,y,x+2,y+2))
        ps=list(g.geoms) if hasattr(g,'geoms') else [g]
        for p in ps:
            if p.geom_type!='Polygon' or p.area<1e-7:continue
            for t in constrained_delaunay_triangles(p).geoms:
                coords=[[xx-ORIGIN[0],yy-ORIGIN[1],ground_height(xx,yy)-ORIGIN[2]]
                        for xx,yy in list(t.exterior.coords)[:3]]
                if np.cross(np.array(coords[1])-coords[0],np.array(coords[2])-coords[0])[2]<0:coords.reverse()
                surface.append(coords)
payload['ground_surface_triangles']=surface
payload['ground_surface_basis']='2m tessellation of exact footprint; exposed source samples smoothed locally; hidden canopy ground inferred from platform fit. Ramped tips preserved approximately; not threshold survey.'
(OUT/'block_input.json').write_text(json.dumps(payload,separators=(',',':')))

fig,(ax,bx)=plt.subplots(1,2,figsize=(14,8),layout='constrained')
for f in ground_regions:
    g=shape(f['geometry']);ps=list(g.geoms) if hasattr(g,'geoms') else [g]
    for p in ps:
        if p.geom_type!='Polygon':continue
        xy=np.asarray(p.exterior.coords)-CENTER
        ax.fill(xy[:,0],xy[:,1],color='#e4e4df',ec='#a4aaa7',lw=.7)
for axx in [ax,bx]:
    xy=np.asarray(roof.exterior.coords)-CENTER;axx.plot(xy[:,0],xy[:,1],c='#305972',lw=1.5)
    xy=np.asarray(disk.exterior.coords)-CENTER;axx.plot(xy[:,0],xy[:,1],c='#305972',lw=1)
    axx.set_aspect('equal');axx.set_xlabel('East offset / m');axx.set_ylabel('North offset / m');axx.grid(alpha=.12)
ax.scatter(local[:,0],local[:,1],c=residual,cmap='coolwarm',vmin=-.15,vmax=.15,s=5)
ax.set_title('Official island / roof + exposed surface samples')
underside=next(p for p in parts if p['id'].endswith('.216390'))
tt=np.asarray(underside['triangles'])+ORIGIN
pc=PolyCollection(tt[:,:,:2]-CENTER,array=tt[:,:,2].mean(axis=1),cmap='viridis',edgecolors='#777777',linewidths=.18)
bx.add_collection(pc);bx.autoscale();fig.colorbar(pc,ax=bx,shrink=.4,label='Official soffit LN02 / m')
bx.set_title('Surveyed underside triangles: preserve, inspect supports')
fig.savefig(OUT/'source_geometry_check.png',dpi=150)
print(json.dumps(report))
