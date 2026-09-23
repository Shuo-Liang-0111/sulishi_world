"""Triangulate source geometry without moving its world coordinates or inventing detail."""
from pathlib import Path
import json
from collections import defaultdict, Counter
import numpy as np
from shapely.geometry import Polygon, shape, box
from shapely import constrained_delaunay_triangles
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'derived';OUT.mkdir(exist_ok=True)
ORIGIN=np.array([2683775,1246700,400],dtype=float)
scope=shape(json.loads((ROOT/'planning/g1_scope.geojson').read_text())['features'][0]['geometry'])
context=box(2683420,1246300,2684200,1247110)
DUPLICATE_TRIANGLES=0

def triangulate_rings(rings):
    pts=np.array(rings[0],dtype=float)
    if len(pts)<4:return []
    normal=np.cross(pts[:-1]-pts[0],pts[1:]-pts[0]).sum(axis=0)
    axis=int(np.argmax(np.abs(normal)));keep=[i for i in range(3) if i!=axis]
    lookup={tuple(np.array(p)[keep]):p for ring in rings for p in ring}
    poly=Polygon(np.array(rings[0])[:,keep],[np.array(r)[:,keep] for r in rings[1:]])
    if poly.area<1e-8:return []
    if not poly.is_valid:poly=poly.buffer(0)
    out=[]
    for t in constrained_delaunay_triangles(poly).geoms:
        tri=[]
        for xy in list(t.exterior.coords)[:3]:
            if xy in lookup:p=np.array(lookup[xy])
            else:
                p=pts[0].copy();p[keep]=xy
                p[axis]=pts[0,axis]-np.dot(normal[keep],p[keep]-pts[0,keep])/normal[axis]
            tri.append((p-ORIGIN).tolist())
        if np.dot(np.cross(np.array(tri[1])-tri[0],np.array(tri[2])-tri[0]),normal)<0:tri.reverse()
        out.append(tri)
    return out

def arrays(triangles):
    global DUPLICATE_TRIANGLES
    vertices=[];faces=[];lookup={};seen_faces=set()
    for tri in triangles:
        face=[]
        for p in tri:
            key=tuple(round(float(v),6) for v in p)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(key)
            face.append(lookup[key])
        if len(set(face))==3:
            key=tuple(sorted(face))
            if key in seen_faces:DUPLICATE_TRIANGLES+=1
            else:faces.append(face);seen_faces.add(key)
    return vertices,faces

tin={}
for p in (ROOT/'sources/terrain').glob('*.geojson'):
    for f in json.loads(p.read_text())['features']:
        tin[f['id']]=f
tri=[];terrain_polygons=[]
for f in tin.values():
    g=shape(f['geometry'])
    if context.intersects(g):
        clipped=g.intersection(context)
        geoms=list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
        for poly in geoms:
            if poly.geom_type!='Polygon' or poly.area<1e-8:continue
            terrain_polygons.append(poly)
            tri.extend(triangulate_rings([list(poly.exterior.coords)]+[list(r.coords) for r in poly.interiors]))
coverage=unary_union(terrain_polygons)
uncovered=scope.difference(coverage)
vertices,faces=arrays(tri)
objects=[{'id':'SURVEY_TERRAIN','kind':'terrain_reference','source':'geo_digitales_terrainmodell__tin_',
          'vertices':vertices,'faces':faces,'triangles':len(faces),'role':'survey_reference_not_finished_ground'}]
buildings=defaultdict(lambda:defaultdict(list));props={};source_ids=defaultdict(list);invalid=[]
roof=json.loads((ROOT/'sources/features/bauten_dachmodell_3d.geojson').read_text())
for f in roof['features']:
    p=f['properties']
    key=('EGID_'+str(p['egid'])) if p.get('egid') else ('GID_'+str(p['gid']) if p.get('gid') else 'SOURCE_'+f['id'])
    props[key]=p
    source_ids[key].append(f['id'])
    for rings in f['geometry']['coordinates']:
        try:buildings[key][p['type']].extend(triangulate_rings(rings))
        except Exception as e:invalid.append({'id':f['id'],'type':p['type'],'error':str(e)})
for key,parts in buildings.items():
    total=[t for ts in parts.values() for t in ts]
    if not total:continue
    vv=np.array(total).reshape(-1,3)+ORIGIN
    xy=box(vv[:,0].min(),vv[:,1].min(),vv[:,0].max(),vv[:,1].max())
    if not context.intersects(xy):continue
    core=scope.intersects(xy)
    v=[];f=[];materials=[]
    for typ,ts in parts.items():
        vs,fs=arrays(ts);offset=len(v);v.extend(vs);f.extend([[i+offset for i in t] for t in fs])
        materials.extend([{'RoofSurface':0,'WallSurface':1,'GroundSurface':2}[typ]]*len(fs))
    objects.append({'id':key,'kind':'survey_building','source':'bauten_dachmodell_3d',
                    'source_feature_ids':source_ids[key],
                    'source_properties':props[key],'in_scope':core,'vertices':v,'faces':f,
                    'materials':materials,'role':'lod2_reference_not_finished_facade',
                    'floor_warning':'Dataset bottom is sunk; do not use it as an entrance floor.'})
payload={'origin':ORIGIN.tolist(),'objects':objects,'errors':invalid,
         'terrain_unique_features':len(tin),'total_triangles':sum(len(o['faces']) for o in objects)}
target=OUT/'G1_geo_base.json';target.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
report={'objects':len(objects),'terrain_triangles':len(faces),'terrain_unique_features':len(tin),
        'scope_without_terrain_m2':uncovered.area,
        'context_without_terrain_m2':context.difference(coverage).area,
        'exact_duplicate_triangles_removed':DUPLICATE_TRIANGLES,
        'total_triangles':payload['total_triangles'],'conversion_errors':invalid,'output_bytes':target.stat().st_size}
(OUT/'G1_geo_base_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
if invalid:raise RuntimeError('Source conversion errors need review before import')
