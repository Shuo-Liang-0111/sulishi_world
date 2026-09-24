"""Replace rebuilt AV36232 ground, wall and twelve individually built trees.

Unbuilt shelters, stairs, other walls, neighboring trees and boats are protected.
This is source-object-constrained authoring, not automatic semantic segmentation.
"""
from pathlib import Path
import ast,hashlib,json,struct
import numpy as np
from shapely.geometry import shape,Point,Polygon,mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridgehead_bank'
P=json.loads((D/'build_input.json').read_text(encoding='utf-8'))
context=json.loads((D/'context.json').read_text(encoding='utf-8'));foot=shape(P['source']['geometry'])
ns={'__file__':str(R/'tools/prepare_bridgehead_bank.py')}
exec(compile((R/'tools/prepare_bridgehead_bank.py').read_text(encoding='utf-8').split('# Spatial tiles')[0],'bank_grade','exec'),ns)
ground=ns['ground']
def floor(xy):return ground(round(float(xy[0]),6),round(float(xy[1]),6))

inventory=json.loads((R/'sources/features/bauminventar.geojson').read_text(encoding='utf-8'))['features']
av=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text(encoding='utf-8'))['features']
buildings=unary_union([shape(f['geometry']).buffer(.30) for f in av if f['properties']['art_txt'].startswith('Gebaeude') and shape(f['geometry']).distance(foot)<30])
guards=unary_union([shape(P['guard']),buildings,*[shape(f['geometry']).buffer(.13) for f in context['adjacent_structures']
    if f['properties'].get('art_txt')=='Mauer.Mauer' and not f['id'].endswith('.15891')]])
# Actual rejected-view rays identify the same AV15891 wall photographed up
# to about two metres outside its true footprint. Replace that displaced
# surface only where both upper/lower surroundings already exist as solids.
rebuilt_context=unary_union([foot,shape(P['cap']),ns['corridor'],ns['stair'],
                            shape(ns['B']['retaining'])])
wall_replacement=shape(P['cap']).buffer(2.1).intersection(rebuilt_context.buffer(.10)).difference(guards)
volumes=[dict(id='upper_ground',mask=foot.difference(guards),lo=-.22,hi=.22,relative=True),
         dict(id='rebuilt_retaining_and_guardrail',mask=wall_replacement,lo=-3.2,hi=1.40,relative=True)]
tree_records=[]
for entry in P['trees']:
    c=np.array(entry['source']['geometry']['coordinates'])[:2];rad=max(entry['inferred']['crown_radius_m'])+2.5
    region=Point(c).buffer(rad,quad_segs=48)
    for f in inventory:
        q=np.array(f['geometry']['coordinates'])[:2];distance=np.linalg.norm(q-c)
        if distance<.01 or distance>2*rad+6:continue
        normal=(q-c)/distance;middle=(q+c)/2;side=np.array([-normal[1],normal[0]])
        region=region.intersection(Polygon([middle+side*100,middle-side*100,middle-side*100-normal*100,middle+side*100-normal*100]))
    region=region.difference(buildings);ident=entry['source']['id'];z=entry['ground_ln02_m']
    low=region.intersection(rebuilt_context).difference(guards)
    trunk=Point(c).buffer(entry['radius_m_inferred']+.10).intersection(foot).difference(guards)
    volumes.extend([dict(id=ident+'_crown',mask=region,lo=z+3.2,hi=z+entry['height_m']+1.3,relative=False),
        dict(id=ident+'_low_fragment',mask=low,lo=1.15,hi=3.4,relative=True),
        dict(id=ident+'_trunk',mask=trunk,lo=-.10,hi=3.4,relative=True)])
    tree_records.append(dict(id=ident,mask=mapping(region),lower=z+3.2,upper=z+entry['height_m']+1.3))
helper=ast.parse((R/'tools/prepare_limmat_sidewalk_cut.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in {'clip','fan','subtract'}],type_ignores=[]),'bank_bounded_cut','exec'))
basepath=R/'derived/bellevue/west_context/quaibruecke_water_structure_cut.json'
base=json.loads(basepath.read_text(encoding='utf-8'));overrides={str(q['node']):q for q in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text(encoding='utf-8'))
changed=[];counts=[]
for item in manifest['items']:
    m=np.array(item['mbs']);near=[q for q in volumes if Point(m[:2]).distance(q['mask'])<=m[3]]
    if not near:continue
    key=str(item['node'])
    if key in overrides:
        rec=overrides[key];xyz=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2)
    else:
        raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
        xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)
        uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2)
    vv=[];uu=[];dirty=False
    for tri,tex in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
        poly=Polygon(tri[:,:2]);pieces=[np.c_[tri,tex]]
        for vol in near:
            if poly.distance(vol['mask'])>.001:continue
            if not vol['relative'] and (tri[:,2].min()>=vol['hi'] or tri[:,2].max()<=vol['lo']):continue
            nxt=[]
            for piece in pieces:
                out,did=subtract(piece,vol);nxt.extend(out);dirty=dirty or did
            pieces=nxt
            if not pieces:break
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        overrides[key]=dict(node=item['node'],vertices=vv,uv_source_v_unflipped=uu,source_sha256=item['geometry_sha256'])
        changed.append(key);counts.append(dict(node=key,before=len(xyz)//3,after=len(vv)//3))
        print('BANK_PHOTO_NODE',key,flush=True)
out=R/'derived/bellevue/west_context/bridgehead_bank_cut.json'
out.write_text(json.dumps(dict(mask_basis=base['mask_basis']+'; G1_025 AV36232 upper ground, actual wall15891 and12 source-positioned planes; other structures and neighbor tree partitions protected. Source photography retained.',
    base_cut_sha256=hashlib.sha256(basepath.read_bytes()).hexdigest(),overrides=list(overrides.values()),changed_nodes=len(overrides),bank_changed_nodes=changed),separators=(',',':')),encoding='utf-8')
(D/'cut_basis.json').write_text(json.dumps(dict(changed_nodes=counts,trees=tree_records,guards=mapping(guards),
    volumes=[{**q,'mask':mapping(q['mask'])} for q in volumes],source_originals_retained=True,visual_review_required=True),indent=2),encoding='utf-8')
print(json.dumps(dict(changed=len(changed),output_bytes=out.stat().st_size)),flush=True)
