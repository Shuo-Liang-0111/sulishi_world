"""Bounded photographic replacement for the nine newly authored inventory trees."""
from pathlib import Path
import ast, json, struct, hashlib, sys
import numpy as np
from shapely.geometry import Point, Polygon, shape, mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/riviera_quay'
p=json.loads((D/'tree_build_input.json').read_text())
source=json.loads((D/'build_input.json').read_text());foot=shape(source['source_plan_lv95'])
inventory=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
av=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
continuous='--continuous-ground' in sys.argv
if continuous:
    foot=unary_union([foot,shape(next(f['geometry'] for f in av if f['id']=='av_bo_boflaeche_a.24105'))])
building=unary_union([shape(f['geometry']).buffer(1.) for f in av
    if f['properties']['art_txt'].startswith('Gebaeude') and shape(f['geometry']).distance(foot)<20])
ei=json.loads((R/'sources/features/av_ei_flaechenelement_a.geojson').read_text())['features']
guard=unary_union([building,*[shape(f['geometry']).buffer(.18) for f in ei
    if shape(f['geometry']).distance(foot)<1 and f['properties']['art_txt'] in ['Mauer.Mauer','wichtige_Treppe','Landungssteg']]])
volumes=[];records=[]
for tree in p['trees']:
    c=np.array(tree['source']['geometry']['coordinates']);rad=max(tree['inferred']['crown_radius_m'])+2.4
    cell=Point(c).buffer(rad,quad_segs=48)
    for other in inventory:
        q=np.array(other['geometry']['coordinates']);distance=np.linalg.norm(q-c)
        if distance<.01 or distance>2*rad+5:continue
        normal=(q-c)/distance;middle=(q+c)/2;side=np.array([-normal[1],normal[0]])
        cell=cell.intersection(Polygon([middle+side*100,middle-side*100,middle-side*100-normal*100,middle+side*100-normal*100]))
    cell=cell.difference(building);ground=tree['ground_ln02_m'];ident=tree['source']['id']
    low=cell.intersection(foot).difference(guard)
    volumes.extend([{'id':ident+'_crown','mask':cell,'lo':ground+4.,'hi':ground+tree['height_m']+1.25,'relative':False},
                    {'id':ident+'_low_remnants','mask':low,'lo':ground+.12,'hi':ground+4.6,'relative':False}])
    records.append({'source_id':ident,'crown_mask_lv95':mapping(cell),'low_mask_lv95':mapping(low),'ground_ln02_m':ground,
                    'crown_height_band':[ground+4.,ground+tree['height_m']+1.25], 'low_height_band':[ground+.12,ground+4.6]})

# Established clipping kernel: interpolate source position AND UV at each cut.
kernel=R/'tools/prepare_limmat_sidewalk_cut.py';module=ast.parse(kernel.read_text())
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['clip','fan','subtract']],type_ignores=[]),str(kernel),'exec'))
basepath=R/'derived/bellevue/west_context'/('riviera_tree_photo_cut.json' if continuous else 'riviera_quay_photo_cut.json')
base=json.loads(basepath.read_text());overrides={str(q['node']):q for q in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());changed=[]
counts={v['id']:0 for v in volumes}
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
        for volume in near:
            keep=[]
            for piece in pieces:
                out,did=subtract(piece,volume);keep.extend(out)
                if did:dirty=True;counts[volume['id']]+=1
            pieces=keep
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']}
        changed.append(key);print('RIVIERA_TREE_PHOTO_NODE',key,flush=True)
out=R/'derived/bellevue/west_context'/('riviera_tree_continuous_photo_cut.json' if continuous else 'riviera_tree_photo_cut.json')
description='; G1_021r2 actual ray diagnosis: lower remnants of the new trees cross the AV145/AV24105 boundary. Both paving footprints and trees are authored; join their low replacement mask while retaining all neighbor bisectors, buildings, walls, stairs and landings. No river or unbuilt ground clearance.' if continuous else '; G1_021r1 nine source-ID Sophora now physically rebuilt, neighbor-tree bisectors and building guards retained. Lower remnants only above AV145, with cadastral walls/stairs/landings protected. Boats/water and original sources unchanged.'
result={'mask_basis':base['mask_basis']+description,
        'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),
        'changed_nodes':len(overrides),'riviera_tree_changed_nodes':changed}
out.write_text(json.dumps(result,separators=(',',':')))
(D/('tree_continuous_cut_basis.json' if continuous else 'tree_cut_basis.json')).write_text(json.dumps({'base_cut':str(basepath.relative_to(R)),'changed_nodes':changed,'trees':records,
       'counts':counts,'original_sources_retained':True,'guard_lv95':mapping(guard),
       'kernel_sha256':hashlib.sha256(kernel.read_bytes()).hexdigest()},indent=2))
print(json.dumps({'changed_nodes':len(changed),'total_overrides':len(overrides),'output_bytes':out.stat().st_size}),flush=True)
