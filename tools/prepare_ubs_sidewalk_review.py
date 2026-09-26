"""Resolve the rejected r9 entry view against cached land use and VBZ fixtures.

Read-only investigation. It does not delete a scan, move a camera or assert that
absence from one facility inventory proves absence from the real street.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from shapely.geometry import shape,Point,Polygon
from workspace_paths import ROOT,LEGACY_ROOT,read_path,write_path

d=json.loads(read_path('derived/ubs_theaterstrasse20/build_input.json').read_text())
report=json.loads(read_path('evidence/G1_027r9/ubs_build_report.json').read_text())
probe=json.loads(read_path('derived/ubs_theaterstrasse20/r8_geometry_probe.json').read_text())
O=np.array(d['origin_lv95_ln02']);A,U,N=(np.array(d[k]) for k in ['A','U','N'])
camera=next(r for r in report['cameras'] if r['name']=='UF_QA_ENTRY')
eye=np.array(camera['eye']);direction=np.array(camera['look'])-eye;direction/=np.linalg.norm(direction)
def Q(p):return np.r_[(p[:2]-A)@U,(p[:2]-A)@N,p[2]]
def P(u,v):return A+U*u+N*v+O[:2]
hits=[]
for row in probe['photo_objects']:
    t=np.array(row['vertices_world'])[np.array(row['triangles'])];e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0]
    p=np.cross(direction,e2);det=(e1*p).sum(1);valid=abs(det)>1e-10;inv=np.zeros(len(det));inv[valid]=1/det[valid]
    q=eye-t[:,0];a=(q*p).sum(1)*inv;qq=np.cross(q,e1);b=(qq*direction).sum(1)*inv;dist=(qq*e2).sum(1)*inv
    for i in np.flatnonzero(valid&(a>=0)&(b>=0)&(a+b<=1)&(dist>0)&(dist<10)):
        point=eye+dist[i]*direction
        hits.append(dict(object=row['name'],r8_face=int(i),distance=float(dist[i]),point=point.tolist(),local_uvz=Q(point).tolist(),triangle=t[i].tolist()))
hits.sort(key=lambda r:r['distance']);assert hits and hits[0]['object']=='CTX_I3S_33436'
assert hits[0]['local_uvz'][1]>1.18 # This face lies outside r9's facade replacement volume.

avpath=read_path('sources/features/av_bo_boflaeche_a.geojson');av=json.loads(avpath.read_text())['features']
land=[]
for label,p in [('camera',eye),('occluder',np.array(hits[0]['point']))]:
    for f in av:
        if shape(f['geometry']).covers(Point(p[:2]+O[:2])):land.append(dict(sample=label,id=f['id'],properties=f['properties']))
assert all(any(r['sample']==label and r['properties']['art_txt']=='befestigt.Trottoir' for r in land) for label in ['camera','occluder'])
scope=Polygon([P(u,v) for u,v in [(-.06,1.18),(d['street_width_m']+.06,1.18),(d['street_width_m']+.06,4.4),(-.06,4.4)]])
intersecting=[dict(id=f['id'],type=f['properties']['art_txt'],area_m2=shape(f['geometry']).intersection(scope).area) for f in av if shape(f['geometry']).intersects(scope)]

fixtures=[];files={}
# File-level H-first fallback; directory-level fallback would miss older layers.
for root in [LEGACY_ROOT,ROOT]:
    if root:
        for p in (root/'sources/features/vbz').glob('haltestellen_*.geojson'):files[p.name]=p
for p in files.values():
    for f in json.loads(p.read_text())['features']:
        geo=shape(f['geometry']);c=geo.centroid;v=np.array([c.x,c.y])-O[:2];u=float((v-A)@U);n=float((v-A)@N)
        if -6<u<28 and 0<n<20:
            fixtures.append(dict(layer=p.stem,id=f['id'],u=u,v=n,intersects_proposed_review=geo.intersects(scope),properties=f['properties'],geometry=f['geometry']))
roofpath=read_path('sources/features/bauten_dachmodell_3d.geojson');shelters=[]
for f in json.loads(roofpath.read_text())['features']:
    if f['properties'].get('art_txt')!='Unterstand' or f['properties']['type']!='RoofSurface':continue
    for i,poly in enumerate(f['geometry']['coordinates']):
        v=np.array(poly[0])-O;local=np.array([Q(p) for p in v]);c=local.mean(0)
        if -6<c[0]<28 and 1.15<c[1]<20 and 9<c[2]<16:
            shelters.append(dict(id=f['id'],polygon=i,egid=f['properties']['egid'],local_bounds=[local.min(0).tolist(),local.max(0).tolist()]))
out=dict(version='G1_027r9',camera=camera,original_photo_ray_hits=hits,land_use=land,proposed_review_land_use=intersecting,
    official_vbz_fixtures=fixtures,official_shelter_roofs=shelters,
    source_files=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [avpath,roofpath,*files.values()]],
    diagnostic='The entry image is occluded at0.958m by a current photo face over a measured sidewalk. The known VBZ shelter and two poster cases are around12..17m from the facade, outside this near-front review strip.',
    constraints=['Retain official shelter and fixture positions; their inventory is not proof of an empty street.',
                 'Inspect the photographed walk strip and source mesh before replacing this bounded near-front remainder.',
                 'Do not move the old entry camera to conceal the failure; compare from that same camera after repair.',
                 'UF pavement UV uses1m inr9 while adjoiningSG pavement uses2.05m; correct in the next saved revision.'],
    native_changed=False,photography_removed=False,visual_acceptance=False)
path=write_path('derived/ubs_theaterstrasse20/sidewalk_review.json');path.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(dict(file=str(path),occluder=hits[0],land_use=intersecting,near_front_known_fixtures=[r['id'] for r in fixtures if r['intersects_proposed_review']],shelters=shelters)))
