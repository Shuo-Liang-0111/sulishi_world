"""Prepare the real east Bellevue shelter, not an empty foreground cut.

Official plan/height envelope and facility points remain fixed. Published
2016 construction details support the thin eaves, centre drainage and three
mushroom columns; their exact fabrication and optical properties are inferred.
This is preparation only. No scan is removed and no native is saved.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from shapely.geometry import shape,Polygon,Point,box,mapping
from shapely.affinity import translate
from shapely import constrained_delaunay_triangles
from workspace_paths import read_path,write_path

roof_path=read_path('sources/features/bauten_dachmodell_3d.geojson')
probe_path=read_path('derived/ubs_theaterstrasse20/r8_geometry_probe.json')
bank_path=read_path('derived/ubs_theaterstrasse20/build_input.json')
fixture_path=read_path('derived/ubs_theaterstrasse20/sidewalk_review.json')
av_path=read_path('sources/features/av_bo_boflaeche_a.geojson')
data=json.loads(roof_path.read_text())
source=[f for f in data['features'] if f['properties'].get('egid')==302063028]
roof=next(f for f in source if f['properties']['type']=='RoofSurface')
underside=next(f for f in source if f['properties']['type']=='GroundSurface')
assert roof['id']=='bauten_dachmodell_3d.177510'
assert underside['id']=='bauten_dachmodell_3d.185848'
bank=json.loads(bank_path.read_text());O=np.array(bank['origin_lv95_ln02'])
A,U,N=(np.array(bank[k]) for k in ['A','U','N'])
ring=np.array(roof['geometry']['coordinates'][0][0])[:-1]-O
under_ring=np.array(underside['geometry']['coordinates'][0][0])[:-1]-O
assert np.ptp(ring[:,2])<1e-6 and np.ptp(under_ring[:,2])<1e-6
poly=Polygon(ring[:,:2]);assert poly.is_valid and abs(poly.area-89.679921)<.0001
uv=np.column_stack(((ring[:,:2]-A)@U,(ring[:,:2]-A)@N))
ends=[]
for side in [0,1]:
    xx=uv[:,0];q=uv[xx<xx.min()+3] if side==0 else uv[xx>xx.max()-3]
    solution=np.linalg.lstsq(np.c_[2*q,np.ones(len(q))],(q*q).sum(1),rcond=None)[0]
    center=solution[:2];radius=float(np.sqrt(solution[2]+center@center))
    residual=abs(np.linalg.norm(q-center,axis=1)-radius)
    assert residual.max()<.012
    ends.append(dict(center_front_uv=center.tolist(),center_local_xy=(A+U*center[0]+N*center[1]).tolist(),
                     fitted_radius_m=radius,ring_points=len(q),max_fit_residual_m=float(residual.max()),
                     basis='Circle fit to the exact surveyed rounded end; inferred column centre, not a surveyed column point.'))
start=np.array(ends[0]['center_local_xy']);end=np.array(ends[1]['center_local_xy'])
axis=end-start;length=float(np.linalg.norm(axis));unit=axis/length;side=np.array([-unit[1],unit[0]])
zmax=float(ring[0,2]);zmin=float(under_ring[0,2]);assert abs(zmax-zmin-.5)<.001
def section(point):
    t=float(np.clip((point-start)@unit/length,0,1));centre=start+axis*t
    radius=ends[0]['fitted_radius_m']*(1-t)+ends[1]['fitted_radius_m']*t
    a=float(np.clip(np.linalg.norm(point-centre)/radius,0,1));a=a*a*(3-2*a)
    return zmax-.178+.178*a,zmin+.420*a

parts={'roof_metal':[],'soffit':[],'fascia':[]};x0,y0,x1,y1=poly.bounds
for x in np.arange(np.floor(x0*2)/2,x1,.5):
    for y in np.arange(np.floor(y0*2)/2,y1,.5):
        inter=poly.intersection(box(x,y,x+.5,y+.5))
        for p in ([inter] if inter.geom_type=='Polygon' else getattr(inter,'geoms',[])):
            if p.geom_type!='Polygon' or p.area<1e-9:continue
            for tri in constrained_delaunay_triangles(p).geoms:
                xy=np.array(tri.exterior.coords)[:3,:2]
                if np.linalg.det(np.stack([xy[1]-xy[0],xy[2]-xy[0]]))<0:xy=xy[::-1]
                parts['roof_metal'].append([[*v,section(v)[0]] for v in xy])
                parts['soffit'].append([[*v,section(v)[1]] for v in xy[::-1]])
edge=poly.exterior
ss=sorted({*np.arange(0,edge.length,.25),edge.length,*[edge.project(Point(p)) for p in edge.coords]})
for a,b in zip(ss,ss[1:]):
    p,q=[np.array(edge.interpolate(t).coords[0]) for t in [a,b]]
    pt,pb=section(p);qt,qb=section(q)
    parts['fascia'] += [[[ *p,pb],[*q,qb],[*q,qt]],[[*p,pb],[*q,qt],[*p,pt]]]
assert min(v[2] for rows in parts.values() for t in rows for v in t)>=zmin-1e-7
assert max(v[2] for rows in parts.values() for t in rows for v in t)<=zmax+1e-7
triangles=np.array(parts['roof_metal'])
projected=np.abs(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])[:,2]).sum()/2
assert abs(projected-poly.area)<1e-6
seams=[]
for s in np.arange(0,edge.length,.52):
    p=np.array(edge.interpolate(s).coords[0]);fraction=np.clip((p-start)@unit/length,0,1)
    centre=start+fraction*axis;direction=p-centre;distance=np.linalg.norm(direction)
    if distance<.2:continue
    seams.append([[*(centre+direction*t),section(centre+direction*t)[0]+.004]
                  for t in np.linspace(.12/distance,.996,16)])

# Public ground under the roof is a different surface from its GroundSurface.
# Collect candidate evidence for later native ray and boundary checks. Do not
# treat top-of-bench points or a fitted plane as accepted station pavement.
probe=json.loads(probe_path.read_text());candidates=[]
for row in probe['photo_objects']:
    t=np.array(row['vertices_world'])[np.array(row['triangles'])]
    cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(cross,axis=1)
    mask=(norm>1e-8)&(cross[:,2]>.965*norm)&(t[:,:,2].min(1)>8.1)&(t[:,:,2].max(1)<8.9)
    for idx in np.flatnonzero(mask):
        centre=t[idx].mean(0)
        if poly.buffer(1.0).covers(Point(centre[:2])):
            candidates.append(dict(object=row['name'],r8_face=int(idx),centroid=centre.tolist(),
                                   triangle=t[idx].tolist(),area_m2=float(norm[idx]/2)))
facilities=json.loads(fixture_path.read_text())['official_vbz_fixtures']
nearby=[]
for row in facilities:
    g=translate(shape(row['geometry']),-O[0],-O[1])
    if poly.buffer(1.8).intersects(g):nearby.append(row)
av=[]
for f in json.loads(av_path.read_text())['features']:
    g=translate(shape(f['geometry']),-O[0],-O[1])
    if g.intersects(poly):
        area=g.intersection(poly).area
        if area>1e-6:av.append(dict(id=f['id'],type=f['properties']['art_txt'],area_m2=area,geometry_local=mapping(g)))
paths=[roof_path,probe_path,bank_path,fixture_path,av_path,
       read_path('sources/references/bellevue_shelters/Immobilia_2016_05_p76.png'),
       read_path('sources/references/ubs_theaterstrasse20/mml_1.jpg')]
out=dict(egid=302063028,vbz_shelter_id='haltestellen_wartehalle.73',origin_lv95_ln02=O.tolist(),
    source_ids=[f['id'] for f in source],roof_plan_local=mapping(poly),roof_plan_area_m2=poly.area,
    axis_start_local_xy=start.tolist(),axis_end_local_xy=end.tolist(),axis_unit_xy=unit.tolist(),side_unit_xy=side.tolist(),axis_length_m=length,
    rounded_end_fits=ends,source_height_envelope_local=[zmin,zmax],parts=parts,standing_seams=seams,
    inferred_support_centres_local_xy=[(start+axis*t).tolist() for t in [0,.5,1]],
    nearby_facilities=nearby,land_use_beneath=av,ground_candidates=candidates,
    source_files=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
    basis='Official roof plan/envelope and VBZ point identities. Two 2015 canopies described in Immobilia May2016 p76 have three in-line mushroom columns, concrete soffit, metal standing seams and central drainage. Column centres from rounded end fits/midline, actual roof section, fabrication, material wear and finishes are inference.',
    next='Reopen current main native after the secondary lease is returned. Probe existing street surfaces and surviving source under/around this canopy before authoring supports, furniture or a bounded photo replacement.',
    limits=['LOD GroundSurface is the canopy underside envelope, never a walking floor.',
            'MML bank photo is dated indirectly and used for place/reference only; it is not current traffic or platform measurement.',
            'No operational departure display or timetable is fabricated.',
            'Preparation only; no native, appearance, public interaction or boundary acceptance.'],
    native_changed=False,photography_removed=False,visual_acceptance=False)
p=write_path('derived/bellevue/bank_tram_shelter/build_input.json');p.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(dict(file=str(p),roof_area_m2=poly.area,axis_length_m=length,roof_triangles=len(parts['roof_metal']),
                     ground_candidates=len(candidates),nearby_facilities=len(nearby),land_use=[{k:f[k] for k in ['id','type','area_m2']} for f in av]),indent=2))
