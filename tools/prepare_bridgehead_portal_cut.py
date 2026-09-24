"""Replace bounded photographic AV16002 surfaces after rebuilding both levels.

Whole faces are selected against the complete built bridgehead, not the camera
view. Source originals and all unaffected working faces/UVs remain unchanged.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from shapely.geometry import shape,Point,Polygon,mapping,LineString
from shapely.ops import unary_union

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridgehead_portal'
P=json.loads((D/'build_input.json').read_text());B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
U=json.loads((R/'derived/bellevue/bridgehead_bank/build_input.json').read_text())
Q=json.loads((R/'derived/bellevue/quaibruecke_water/build_input.json').read_text())
wall=shape(P['source']['geometry']);deck=shape(P['deck'])
built=unary_union([shape(U['source']['geometry']),shape(B['corridor']),shape(B['retaining']),shape(Q['bridge'])])
# The diagnosed lower ribbon belongs to the already built lake fascia,
# displaced about0.20m by the photography. Include those complete edge parts,
# rather than retaining a vertical sliver at the upper/lower cadastral boundary.
fascia=[p for p in B['parts'] if p['name'].startswith('LAKE_EDGE_FASCIA') and shape(p['plan']).distance(wall)<3]
edge=unary_union([shape(p['plan']) for p in fascia]).buffer(.45)
edge_bottom=min(np.array(p['vertices'])[:,2].min()+400 for p in fascia)-.10
domain=unary_union([unary_union([deck,wall.buffer(1.)]).intersection(built.buffer(.12)),edge])
envelope=domain.buffer(.35)
route=LineString(B['route']);capfit=P['report']['cap_fit']
def bottom(p):
    if edge.buffer(.35).covers(Point(p)):return edge_bottom
    return float(np.interp(route.project(Point(p)),B['report']['floor_profile_stations_m'],B['report']['floor_profile_ln02_m']))-.20
def top(p):return float(np.array(capfit['coefficients'])@np.r_[1,np.array(p)-capfit['center']])+.35
basepath=R/'derived/bellevue/west_context/bridgehead_bank_tree_remnants_cut.json'
base=json.loads(basepath.read_text());manifest={str(i['node']):i for i in json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())['items']}
changed=[];removed=[]
for rec in base['overrides']:
    key=str(rec['node']);item=manifest[key]
    if Point(item['mbs'][:2]).distance(domain)>item['mbs'][3]:continue
    v=np.array(rec['vertices']).reshape(-1,3,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,3,2)
    keep=[];count=0
    for i,tri in enumerate(v+item['mbs'][:3]):
        poly=Polygon(tri[:,:2]);center=tri[:,:2].mean(0)
        near=domain.covers(Point(center))
        covered=(poly.intersection(envelope).area/poly.area>.995) if poly.area>1e-8 else all(envelope.covers(Point(q)) for q in tri[:,:2])
        height=all(bottom(q[:2])<q[2]<top(q[:2]) for q in tri)
        if near and covered and height:
            count+=1;removed.append(dict(node=key,face=i,center_lv95=tri.mean(0).tolist()))
        else:keep.append(i)
    if count:
        rec['vertices']=v[keep].reshape(-1,3).tolist();rec['uv_source_v_unflipped']=uv[keep].reshape(-1,2).tolist()
        changed.append(dict(node=key,removed_faces=count,before=len(v),after=len(keep)))
base.update(base_cut_sha256=hashlib.sha256(basepath.read_bytes()).hexdigest(),
    mask_basis=base['mask_basis']+'; G1_026 source-shaped upper portal deck and AV16002 wall now rebuilt: whole faces inside bounded replacement envelope; underlying public route stays open.',
    portal_changed_nodes=[q['node'] for q in changed])
out=R/'derived/bellevue/west_context/bridgehead_portal_cut.json'
out.write_text(json.dumps(base,separators=(',',':')),encoding='utf-8')
probes=json.loads((R/'evidence/G1_025r1/retained_bank_probes.json').read_text())['pixels']
removed_ids={(q['node'],q['face']) for q in removed};seeds=[]
for q in probes:
    if q['camera']!='QB_QA_SOUTH' or not q['hits']:continue
    hit=q['hits'][0];seeds.append(dict(pixel=q['pixel'],node=hit['node'],face=hit['face'],removed=(hit['node'],hit['face']) in removed_ids))
report=dict(version='G1_026',domain=mapping(domain),envelope=mapping(envelope),changed=changed,removed_faces=removed,
    replaced_existing_fascia=[p['name'] for p in fascia],edge_bottom_ln02_m=edge_bottom,
    original_sources_retained=True,diagnosed_portal_seeds=seeds,visual_acceptance=False)
(D/'photo_replacement.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(changed=changed,seeds=seeds,output_bytes=out.stat().st_size),indent=2))
