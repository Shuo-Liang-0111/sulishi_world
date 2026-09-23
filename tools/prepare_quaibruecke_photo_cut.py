"""Replace only rebuilt trough/approach/beam volumes in working photo copies."""
from pathlib import Path
import ast
import hashlib
import json
import struct
import numpy as np
from shapely.geometry import Point, Polygon, LineString, shape, mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1]
D=R/'derived/bellevue/quaibruecke_connection'
P=json.loads((D/'build_input.json').read_text())
parts=P['parts']
corridor=shape(P['corridor'])
under=shape(P['underpass'])
stair=shape(P['south_stair'])
volumes=[]
# Subdivide the volume by the authored slabs. A whole-box deletion would erase
#the separate bridge road and the higher lake promenade/trees.
for part in parts:
    if part['role']=='paving':
        v=np.array(part['vertices'])
        volumes.append({'id':part['name'],'mask':shape(part['plan']),
                        'lo':float(v[:,2].min()+400-.02),'hi':float(v[:,2].max()+400+1.05),
                        'relative':False})
    elif part['role'] in ['blue_lining','concrete','abutment']:
        v=np.array(part['vertices'])
        volumes.append({'id':part['name'],'mask':shape(part['plan']).buffer(.04),
                        'lo':float(v[:,2].min()+400-.03),'hi':float(v[:,2].max()+400+.02),
                        'relative':False})
volumes.append({'id':'source_south_steel_stair','mask':stair.buffer(.06),
                'lo':P['report']['south_stair_low_ln02_m']-.10,
                'hi':P['report']['south_stair_top_terrain_interpreted_ln02_m']+1.10,'relative':False})
# The eastern bay's road surface remains photographic. Only the independently
#rebuilt slab underside/steel envelope is replaced.
for part in parts:
    if part['name'].startswith('BRIDGE_SLAB_'):
        v=np.array(part['vertices'])
        poly=shape(part['plan'])
        lower=[q[4] for girder in P['girders'] for q in girder['stations']
               if poly.distance(Point(q[1:3]))<.30]
        assert lower,part['name']
        volumes.append({'id':'BEAMS_'+part['name'],'mask':shape(part['plan']),
                        'lo':float(min(lower)-.04),'hi':float(v[:,2].min()+400+.04),'relative':False})

helpers=ast.parse((R/'tools/prepare_limmat_sidewalk_cut.py').read_text())
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef)
                             and n.name in {'clip','fan','subtract'}],type_ignores=[]),'bounded_photo_helpers','exec'))
basepath=R/'derived/bellevue/west_context/riviera_lower_object_cut.json'
base=json.loads(basepath.read_text())
overrides={str(q['node']):q for q in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
changed=[];counts={};summary=[]
for item in manifest['items']:
    m=np.array(item['mbs'])
    near=[v for v in volumes if Point(m[:2]).distance(v['mask'])<=m[3]]
    if not near:continue
    key=str(item['node'])
    if key in overrides:
        q=overrides[key];xyz=np.asarray(q['vertices']).reshape(-1,3);uv=np.asarray(q['uv_source_v_unflipped']).reshape(-1,2)
    else:
        raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
        xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)
        uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2)
    vv=[];uu=[];dirty=False
    for tri,tex in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
        pieces=[np.c_[tri,tex]]
        bbox=Polygon(tri[:,:2])
        for vol in near:
            if bbox.distance(vol['mask'])>.001 or tri[:,2].min()>vol['hi'] or tri[:,2].max()<vol['lo']:continue
            nxt=[]
            for piece in pieces:
                out,did=subtract(piece,vol);nxt.extend(out)
                if did:dirty=True;counts[vol['id']]=counts.get(vol['id'],0)+1
            pieces=nxt
            if not pieces:break
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']}
        changed.append(key);summary.append({'node':key,'before_triangles':len(xyz)//3,'after_triangles':len(vv)//3})
out=R/'derived/bellevue/west_context/quaibruecke_connection_cut.json'
result={'mask_basis':base['mask_basis']+'; G1_023 source-shaped underpass/actual south steel stair/lake approach and eastern bridge underside only. Road top, source originals, other trees/water/boats retained.',
        'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),
        'changed_nodes':len(overrides),'quaibruecke_changed_nodes':changed}
out.write_text(json.dumps(result,separators=(',',':')))
(D/'cut_basis.json').write_text(json.dumps({'base_cut':basepath.relative_to(R).as_posix(),'changed_nodes':changed,
    'counts':counts,'summary':summary,'volumes':[{**v,'mask':mapping(v['mask'])} for v in volumes],
    'source_originals_preserved':True,'unbuilt_neighbour_objects_retained':True},indent=2))
print(json.dumps({'changed_nodes':changed,'total_overrides':len(overrides),'bytes':out.stat().st_size}))
