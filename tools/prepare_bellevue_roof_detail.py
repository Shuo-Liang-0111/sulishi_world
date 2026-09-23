"""Resolve coarse roof artefacts against original aerial pixels and source heights."""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Point,Polygon,LineString
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
O=np.array(data['origin']);C=np.array(data['center_lv95']);outline=shape(data['roof_outline'])
top=np.array(next(x for x in data['source_parts'] if x['id'].endswith('.153133'))['triangles'])+O
def roof_z(point):
    a=top[:,0,:2];b=top[:,1,:2]-a;c=top[:,2,:2]-a;v=point-a;d=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    ok=abs(d)>1e-8;d=np.where(ok,d,1);u=(v[:,0]*c[:,1]-v[:,1]*c[:,0])/d;w=(b[:,0]*v[:,1]-b[:,1]*v[:,0])/d
    hit=ok&(u>=-1e-6)&(w>=-1e-6)&(u+w<=1.000001)
    z=top[:,0,2]+u*(top[:,1,2]-top[:,0,2])+w*(top[:,2,2]-top[:,0,2])
    return float(np.max(z[hit])) if hit.any() else None

heights=json.loads((ROOT/'derived/bellevue/roof_cap_heights.json').read_text())
plates=[]
for cap,raw in zip(data['supports'],heights):
    center=np.array(cap['center_lv95']);r=math.sqrt(cap['cap_area_m2']/math.pi);z=float(np.median(raw['photo_z']))+.012
    ring=Point(center).buffer(r,quad_segs=24)
    holes=[]
    for a in [90,210,330]:
        xy=center+.68*np.array([math.cos(math.radians(a)),math.sin(math.radians(a))]);holes.append(Point(xy).buffer(.155,quad_segs=12))
    for h in holes:ring=ring.difference(h)
    tri=[]
    for t in constrained_delaunay_triangles(ring).geoms:
        xy=list(t.exterior.coords)[:3]
        tri.append([[x-O[0],y-O[1],z-O[2]] for x,y in xy])
        tri.append([[x-O[0],y-O[1],z-.025-O[2]] for x,y in xy[::-1]])
    for edge in [ring.exterior,*ring.interiors]:
        xy=list(edge.coords)
        for (x,y),(xx,yy) in zip(xy,xy[1:]):
            a=[x-O[0],y-O[1],z-O[2]];b=[xx-O[0],yy-O[1],z-O[2]];aa=[*a[:2],a[2]-.025];bb=[*b[:2],b[2]-.025]
            tri.extend([[a,b,bb],[a,bb,aa]])
    plates.append({'center':center.tolist(),'triangles':tri,'z_ln02':z,
                   'basis':'Original I3S aerial shows a near-flush circular plate with three round apertures, not an open 0.5m-deep pit; height sampled from original mesh. Aperture size inferred.'})

seams=[]
for i in range(240):
    angle=2*math.pi*i/240;direction=np.array([math.cos(angle),math.sin(angle)]);segments=[];points=[]
    for distance in np.arange(7.16,29,.45):
        p=C+direction*distance
        if not outline.buffer(-.04).contains(Point(p)):break
        if any(np.linalg.norm(p-np.array(s['center_lv95']))<1.57 for s in data['supports']):
            if len(points)>1:segments.append(points)
            points=[];continue
        z=roof_z(p)
        if z is not None:points.append([p[0]-O[0],p[1]-O[1],z-O[2]+.009])
    if len(points)>1:segments.append(points)
    seams.extend(segments)
# Shorter folded-sheet seams over the annular central roof.
for i in range(120):
    a=2*math.pi*i/120;v=np.array([math.cos(a),math.sin(a)])
    seams.append([[(C+v*r)[0]-O[0],(C+v*r)[1]-O[1],413.179-O[2]+.009] for r in [3.32,7.06]])

refinements=[]
for part in data['source_parts']:
    if not part['id'].endswith(('.216390','.176359')):continue
    tris=np.array(part['triangles']).copy()
    for tri in tris:
        for p in tri:
            xy=p[:2]+O[:2];distance=outline.exterior.distance(Point(xy))
            if part['id'].endswith('.176359'):
                ztop=roof_z(xy)
                if distance<.02 and ztop is not None and p[2]+O[2]<ztop-.25:p[2]=ztop-O[2]-.16
            else:
                dcap=min(np.linalg.norm(xy-np.array(s['center_lv95'])) for s in data['supports'])
                p[2]+=.34*math.exp(-distance/1.25)*max(0,min(1,(dcap-1.5)/1.0))
    refinements.append({'id':part['id'],'triangles':tris.tolist(),
                        'basis':'Source roof top and footprint preserved; coarse 0.5m exterior fascia refined to ~0.16m lip using observed photographic slenderness. Underside delta is an explicit reconstruction inference.'})

fs=json.loads((ROOT/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features']
wall=next(f for f in fs if f['id'].endswith('.187305'));rim=[]
for poly in wall['geometry']['coordinates']:
    xyz=np.array(poly[0][:-1]);
    if xyz[:,2].min()<413.1:continue
    for i in range(1,len(xyz)-1):rim.append((xyz[[0,i,i+1]]-O).tolist())

out={'plates':plates,'seams':seams,'refinements':refinements,'skylight_rim_triangles':rim,
     'evidence':'evidence/G1_005r2/BE_SOURCE_SAME_STRUCTURE_VIEW.png; original I3S and operator ground photos',
     'inferred':'sheet seam spacing, aperture diameter, slender fascia detail; not survey measurements'}
(ROOT/'derived/bellevue/roof_detail.json').write_text(json.dumps(out,separators=(',',':')))
print(json.dumps({'plates':len(plates),'seams':len(seams),'source_skylight_rim_triangles':len(rim)}))
