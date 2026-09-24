"""Replace only photographic counterparts of the newly authored bridge deck.

The open-day base excludes transient traffic captured in the bridge photograph.
Adjacent shore furniture/trees and the underpass below the deck are retained.
"""
from pathlib import Path
import ast,hashlib,json,struct
import numpy as np
from shapely.geometry import shape,Point,Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_deck'
P=json.loads((D/'build_input.json').read_text());B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
A=np.array(B['bridge_anchor']);T=np.array(B['bridge_along']);N=np.array(B['bridge_across']);coef=np.array(B['bridge_deck_coefficients'])
def floor(xy):
    st,d=(np.array(xy)-A)@np.array([T,N]).T
    return float(coef@[1,st,st*st,d])
bridge=shape(P['bridge']);surface=shape(P['surface'])
volumes=[dict(id='complete_bridge_top',mask=bridge.buffer(.3),lo=-.32,hi=4.4,relative=True),
         dict(id='east_ground',mask=surface.difference(bridge.buffer(.1)),lo=-.28,hi=.24,relative=True)]
for m in P['masts']:
    volumes.append(dict(id=m['id'],mask=Point(m['xy']).buffer(.4),lo=m['ground_interpreted_ln02_m']-.08,
                        hi=m['top_ln02_m']+.12,relative=False))
helper=ast.parse((R/'tools/prepare_limmat_sidewalk_cut.py').read_text())
exec(compile(ast.Module(body=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in {'clip','fan','subtract'}],type_ignores=[]),'bounded_photo_helpers','exec'))
basepath=R/'derived/bellevue/west_context/bridgehead_portal_cut.json';base=json.loads(basepath.read_text())
overrides={str(q['node']):q for q in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text());changed=[]
for item in manifest['items']:
    m=np.array(item['mbs']);near=[v for v in volumes if Point(m[:2]).distance(v['mask'])<m[3]]
    if not near:continue
    key=str(item['node']);record=overrides.get(key)
    if record is not None:
        xyz=np.array(record['vertices']).reshape(-1,3);uv=np.array(record['uv_source_v_unflipped']).reshape(-1,2)
    else:
        raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
        xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)
        uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2)
    vertices=[];texcoords=[];count=0;removed_area=0
    for tri,tex in zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2)):
        pieces=[np.c_[tri,tex]];dirty=False
        for volume in near:
            next_pieces=[]
            for piece in pieces:
                kept,did=subtract(piece,volume);next_pieces.extend(kept);dirty=dirty or did
            pieces=next_pieces
            if not pieces:break
        if dirty:
            count+=1;removed_area+=max(0,Polygon(tri[:,:2]).area-sum(Polygon(q[:,:2]).area for q in pieces))
        for piece in pieces:
            vertices.extend((piece[:,:3]-m[:3]).tolist());texcoords.extend(piece[:,3:].tolist())
    if count:
        overrides[key]=dict(node=item['node'],vertices=vertices,uv_source_v_unflipped=texcoords,source_sha256=item['geometry_sha256'])
        changed.append(dict(node=key,before=len(xyz)//3,after=len(vertices)//3,modified_faces=count,removed_projected_area_m2=removed_area))
out=R/'derived/bellevue/west_context/bridge_deck_cut.json'
result=dict(mask_basis=base['mask_basis']+'; G1_027 complete authored bridge deck/guards/masts. Replace bridge-top photo from deck-.32 to +4.4m, retaining underpass and shore; captured transient bridge traffic excluded from the static base. East approach ground only -.28..+.24m. Mast radius .4m at source XY.',
            base_cut_sha256=hashlib.sha256(basepath.read_bytes()).hexdigest(),overrides=list(overrides.values()),
            bridge_deck_changed_nodes=[q['node'] for q in changed])
out.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
(D/'photo_replacement.json').write_text(json.dumps(dict(changed=changed,source_originals_retained=True,below_deck_retained=True,
    bridge_transient_traffic_not_in_static_base=True,visual_acceptance=False),indent=2),encoding='utf-8')
print(json.dumps(dict(nodes=len(changed),modified_faces=sum(q['modified_faces'] for q in changed),output_bytes=out.stat().st_size)))
