"""Clip only the photographic volumes replaced by the northern lower approach."""
from pathlib import Path
import ast
import hashlib
import json
import struct
import sys
import numpy as np
from shapely.geometry import Point, Polygon, LineString, shape, mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/riviera_lower'
p=json.loads((D/'build_input.json').read_text());context=json.loads((D/'context.json').read_text(encoding='utf-8'))
F={f['id']:f for f in context['features']}
foot=shape(p['footprint']);wall=shape(p['wall']);landing=shape(p['upper_landing'])
stairs=shape(F['av_ei_flaechenelement_a.47309']['geometry'])
outer=LineString([b['edge_xy'] for b in p['benches']])
ramp=Polygon([[2683490.118,1246892.123],[2683500.174,1246895.608],
              [2683501.248,1246892.65],[2683491.306,1246889.177]])
volumes=[{'id':'authored_low_deck','mask':foot.difference(ramp),'lo':404.45,'hi':p['floor_ln02_m']+.28,'relative':False},
         {'id':'authored_north_ramp','mask':ramp.intersection(foot),'lo':405.9,'hi':408.25,'relative':False},
         {'id':'authored_outer_benches','mask':outer.buffer(.82,cap_style='flat').intersection(foot),'lo':405.9,'hi':407.85,'relative':False},
         {'id':'authored_wall_and_guardrail','mask':wall.buffer(.08),'lo':406.1,'hi':410.00,'relative':False},
         {'id':'authored_steel_stair','mask':stairs.union(landing).buffer(.035),'lo':406.3,'hi':410.05,'relative':False}]
refine='--low-canopy' in sys.argv
tree_records=[]
if refine:
    # Actual022 rays identify60153 and122134 at7.40..10.31m local Z.
    # Extend only the already rebuilt upper trees into the now-authored lower
    # parcel; all-tree bisectors and the kiosk envelope remain protected.
    rays=json.loads((R/'evidence/G1_022/photo_residual_rays.json').read_text())
    diagnosed={}
    for ray in rays:
        if not ray['hits']:continue
        near=ray['hits'][0]['nearest_inventory_trees'][0]
        assert near['authored']
        diagnosed[near['id']]=max(diagnosed.get(near['id'],0),near['distance_m'])
    assert set(diagnosed)=={60153,122134}
    alltrees=json.loads((R/'sources/features/bauminventar.geojson').read_text(encoding='utf-8'))['features']
    lp=json.loads((R/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text())
    buildings=unary_union([shape(f['geometry']).buffer(.7) for f in json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text(encoding='utf-8'))['features']
                           if f['properties']['art_txt'].startswith('Gebaeude') and shape(f['geometry']).distance(foot)<8])
    owned=foot.union(wall.buffer(.08)).difference(buildings);volumes=[]
    for tree in lp['pits']:
        ident=tree['source']['properties']['objectid'];c=np.array(tree['source']['geometry']['coordinates'])
        radius=max(tree['inferred']['crown_radius_m'])+2.4
        radius=max(radius,diagnosed.get(ident,0)+.35)
        mask=Point(c).buffer(radius,quad_segs=56)
        for other in alltrees:
            q=np.array(other['geometry']['coordinates']);distance=np.linalg.norm(q-c)
            if distance<.01 or distance>2*radius+5:continue
            n=(q-c)/distance;mid=(q+c)/2;t=np.array([-n[1],n[0]])
            mask=mask.intersection(Polygon([mid+t*100,mid-t*100,mid-t*100-n*100,mid+t*100-n*100]))
        mask=mask.intersection(owned)
        if mask.is_empty:continue
        volumes.append({'id':tree['source']['id'],'mask':mask,'lo':p['floor_ln02_m']+.18,
                        'hi':tree['ground_ln02_m']+4.6,'relative':False})
        tree_records.append({'id':ident,'radius_m':radius,'diagnosed_max_distance_m':diagnosed.get(ident),
                             'mask_area_m2':mask.area,'already_authored':True})
helpers=ast.parse((R/'tools/prepare_limmat_sidewalk_cut.py').read_text())
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in {'clip','fan','subtract'}],type_ignores=[]),'bounded_photo_helpers','exec'))
basepath=R/'derived/bellevue/west_context'/('riviera_lower_approach_cut.json' if refine else 'riviera_tree_continuous_photo_cut.json')
base=json.loads(basepath.read_text());overrides={str(q['node']):q for q in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
changed=[];counts={v['id']:0 for v in volumes}
for item in manifest['items']:
    m=np.array(item['mbs']);near=[v for v in volumes if Point(m[:2]).distance(v['mask'])<=m[3]]
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
        for v in near:
            nextpieces=[]
            for piece in pieces:
                out,did=subtract(piece,v);nextpieces.extend(out)
                if did:dirty=True;counts[v['id']]+=1
            pieces=nextpieces
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']}
        changed.append(key)
description='; G1_022r1 actual ray diagnosis: only previously authored upper trees overhang the rebuilt AV40750/20735 lower parcel. Bound to all-tree bisectors and source parcel/building guards, LN02 lower floor+0.18 to each source root+4.6. No unknown river/boats/bridge removal.' if refine else '; G1_022 reconstructed AV40750 low deck/north ramp, AV20735 wall/rail, AV47309 steel stair and reference-guided edge benches only. AV39461 bridge underpass, river/boats and source originals retained.'
result={'mask_basis':base['mask_basis']+description,
        'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),
        'changed_nodes':len(overrides),'lower_approach_changed_nodes':changed}
out=R/'derived/bellevue/west_context'/('riviera_lower_canopy_cut.json' if refine else 'riviera_lower_approach_cut.json')
out.write_text(json.dumps(result,separators=(',',':')))
(D/('canopy_cut_basis.json' if refine else 'cut_basis.json')).write_text(json.dumps({'base_cut':str(basepath.relative_to(R)),'changed_nodes':changed,'counts':counts,'trees':tree_records,
    'volumes':[{**v,'mask':mapping(v['mask'])} for v in volumes],
    'source_originals_preserved':True,'bridge_underpass_not_removed':True,'outside_river_boats_not_removed':True},indent=2))
print(json.dumps({'changed_nodes':changed,'total_overrides':len(overrides),'bytes':out.stat().st_size,'counts':counts}))
