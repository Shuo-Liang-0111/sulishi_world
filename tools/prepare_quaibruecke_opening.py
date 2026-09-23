"""Resolve the old AV20735 wall crossing the new public AV39461 opening.

Keep the original plan/cap. The inferred lintel underside follows the new floor
at2.12m; no road/wall top is raised to manufacture clearance. Photo replacement
is limited to public free space and the actually rebuilt stair headroom.
"""
from pathlib import Path
import ast,hashlib,json
import numpy as np
from shapely.geometry import shape,mapping,Point,Polygon,LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/quaibruecke_connection'
P=json.loads((D/'build_input.json').read_text());old=json.loads((R/'derived/bellevue/riviera_lower/build_input.json').read_text())
O=np.array(P['origin']);under=shape(P['underpass']);route=LineString(P['route'])


def floor(x,y):return float(np.interp(route.project(Point(x,y)),P['report']['floor_profile_stations_m'],P['report']['floor_profile_ln02_m']))


def solid(poly,top,bottom):
    vertices=[];faces=[]
    for p in ([poly] if poly.geom_type=='Polygon' else getattr(poly,'geoms',[])):
        if p.geom_type!='Polygon' or p.area<1e-8:continue
        p=orient(p,1)
        for tri in constrained_delaunay_triangles(p).geoms:
            ring=list(orient(tri,1).exterior.coords)[:3]
            for fn,reverse in [(top,False),(bottom,True)]:
                off=len(vertices);vertices.extend([[x-O[0],y-O[1],fn(x,y)-400] for x,y in (ring[::-1] if reverse else ring)])
                faces.append([off,off+1,off+2])
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
                off=len(vertices);vertices.extend([[a[0]-O[0],a[1]-O[1],bottom(*a)-400],
                    [b[0]-O[0],b[1]-O[1],bottom(*b)-400],[b[0]-O[0],b[1]-O[1],top(*b)-400],
                    [a[0]-O[0],a[1]-O[1],top(*a)-400]])
                faces.append([off,off+1,off+2,off+3])
    return vertices,faces


replacements=[];gate=under.buffer(.005)
for part in old['parts']:
    if part['role']!='wall':continue
    poly=shape(part['plan']);opening=poly.intersection(gate)
    if opening.area<1e-5:continue
    # The three diagnosed old cap sections are horizontal; assert rather than
    #silently flattening a non-horizontal preceding cap.
    v=np.array(part['vertices']);tops=[v[i,2]+400 for face,label in zip(part['faces'],part['surface']) if label=='top' for i in face]
    assert np.ptp(tops)<1e-5,part['name']
    cap=float(np.mean(tops));base=float(v[:,2].min()+400)
    a,fa=solid(poly.difference(gate),lambda x,y:cap,lambda x,y:base)
    b,fb=solid(opening,lambda x,y:cap,lambda x,y:floor(x,y)+2.12)
    assert all(cap-(floor(x,y)+2.12)>.10 for x,y in opening.exterior.coords)
    faces=fa+[[i+len(a) for i in f] for f in fb]
    replacements.append(dict(name='RL_'+part['name'],vertices=a+b,faces=faces,
        source_plan_area_m2=part['area_m2'],opening_plan_m2=opening.area,cap_preserved_ln02_m=cap,
        inferred_clearance_m=2.12,source_id=part['source']))
assert len(replacements)==3
(D/'opening_input.json').write_text(json.dumps({'replacements':replacements,
    'input_sha256':hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest(),
    'fixed_plan_and_cap':True,'inferred_underside_m':2.12},separators=(',',':')))

# Actual rejected images/rays justify removing the aerial surfaces occupying
#this mapped public passage. Do not clear whole neighbouring trees or water.
volumes=[]
for part in P['parts']:
    if part['role']=='paving':
        poly=shape(part['plan']);v=np.array(part['vertices']);hi=float(v[:,2].min()+400+2.5)
        volumes.append(dict(id='PUBLIC_AIR_'+part['name'],mask=poly,lo=float(v[:,2].min()+400+.005),hi=hi,relative=False))
for item in P['treads']:
    volumes.append(dict(id=f"STAIR_HEADROOM_{item['index']}",mask=shape(item['plan']).buffer(.012),
        lo=item['z']-.01,hi=item['z']+2.12,relative=False))
for part in P['parts']:
    if part['name'].startswith('SOUTH_STAIR_LANDING'):
        z=float(np.array(part['vertices'])[:,2].max()+400)
        volumes.append(dict(id='LANDING_HEADROOM',mask=shape(part['plan']).buffer(.012),lo=z-.01,hi=z+2.12,relative=False))

helper=ast.parse((R/'tools/prepare_limmat_sidewalk_cut.py').read_text())
exec(compile(ast.Module(body=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in {'clip','fan','subtract'}],type_ignores=[]),'clip_helpers','exec'))
basepath=R/'derived/bellevue/west_context/quaibruecke_connection_cut.json';base=json.loads(basepath.read_text())
overrides={str(q['node']):q for q in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());changed=[]
for item in manifest['items']:
    m=np.array(item['mbs']);near=[v for v in volumes if Point(m[:2]).distance(v['mask'])<=m[3]]
    if not near:continue
    key=str(item['node'])
    # All public footprint nodes were already represented in the first cut.
    if key not in overrides:continue
    q=overrides[key];xyz=np.array(q['vertices']).reshape(-1,3);uv=np.array(q['uv_source_v_unflipped']).reshape(-1,2)
    vv=[];uu=[];dirty=False
    for tri,tex in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
        pieces=[np.c_[tri,tex]];bounds=Polygon(tri[:,:2])
        for vol in near:
            if bounds.distance(vol['mask'])>.001 or tri[:,2].min()>vol['hi'] or tri[:,2].max()<vol['lo']:continue
            nxt=[]
            for piece in pieces:
                out,did=subtract(piece,vol);nxt.extend(out);dirty=dirty or did
            pieces=nxt
            if not pieces:break
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        overrides[key]={**q,'vertices':vv,'uv_source_v_unflipped':uu};changed.append(key)
result={'mask_basis':base['mask_basis']+'; G1_023r1 source-defined public passage/stair headroom only after rejected images. Old AV20735 plan/cap retained with inferred public opening. No water/boats/whole-tree removal.',
        'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),
        'changed_nodes':len(overrides),'opening_changed_nodes':changed}
out=R/'derived/bellevue/west_context/quaibruecke_opening_cut.json';out.write_text(json.dumps(result,separators=(',',':')))
(D/'opening_cut_basis.json').write_text(json.dumps({'changed_nodes':changed,'volumes':[{**v,'mask':mapping(v['mask'])} for v in volumes]},indent=2))
print(json.dumps({'old_wall_openings':[{'name':q['name'],'plan_m2':q['opening_plan_m2'],'cap':q['cap_preserved_ln02_m']} for q in replacements],
                  'changed_photo_nodes':changed,'bytes':out.stat().st_size}))
