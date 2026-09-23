"""Remove diagnosed old crown surfaces as faces, not new parcel-sliced volumes.

Only the ray-identified, already rebuilt tree60153 is affected here. Atlas color
is supporting evidence within its spatial ownership, never a global delete mask.
The separately diagnosed steel-stair fringe has its own narrow geometry mask.
"""
from pathlib import Path
from collections import defaultdict
import ast, hashlib, json
import numpy as np
from shapely.geometry import Point, Polygon, shape, mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from scipy.spatial import cKDTree
from probe_riviera_canopy_surface import surface_arrays, manifest

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'derived/bellevue/riviera_lower'
basepath=ROOT/'derived/bellevue/west_context/riviera_lower_canopy_cut.json'
base=json.loads(basepath.read_text())
override={str(q['node']):q for q in base['overrides']}
plan=json.loads((DATA/'build_input.json').read_text())
context=json.loads((DATA/'context.json').read_text(encoding='utf-8'))
features={q['id']:q for q in context['features']}
foot=shape(plan['footprint'])
inventory=json.loads((ROOT/'sources/features/bauminventar.geojson').read_text())['features']
tree_xy=np.array([t['geometry']['coordinates'] for t in inventory])
tree_ids=np.array([t['properties']['objectid'] for t in inventory])
tree_index=cKDTree(tree_xy)
rays=json.loads((ROOT/'evidence/G1_022r1/photo_residual_rays.json').read_text())
diagnosis=json.loads((ROOT/'evidence/G1_022r1/canopy_surface_diagnosis.json').read_text())
assert all(q['nearest_tree']['authored'] for q in diagnosis)
canopy_hits=[q for q in diagnosis if q['nearest_tree']['id']==60153]
assert len(canopy_hits)==6
radius=max(q['nearest_tree']['distance_m'] for q in canopy_hits)+1.5
root=next(t for t in json.loads((ROOT/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text())['pits']
          if t['source']['properties']['objectid']==60153)['ground_ln02_m']
buildings=unary_union([shape(q['geometry']).buffer(.3) for q in json.loads(
    (ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
    if q['properties']['art_txt'].startswith('Gebaeude') and shape(q['geometry']).distance(foot)<10])
records=[]
for node in sorted({q['node'] for q in canopy_hits}):
    xyz,uv,green,rgb=surface_arrays(node)
    centers=xyz.mean(axis=1)
    distance,nearest=tree_index.query(centers[:,:2])
    eligible=(tree_ids[nearest]==60153)&(distance<radius)&(centers[:,2]>405.25)&(centers[:,2]<root+4.7)
    for i in np.flatnonzero(eligible):
        p=Point(centers[i,:2])
        eligible[i]=foot.distance(p)<2.0 and not buildings.covers(p)
    seeds={q['face'] for q in canopy_hits if q['node']==node}
    assert all(eligible[i] for i in seeds)
    chosen=set(np.flatnonzero(eligible&(green>=.20)))|seeds
    # Use real shared vertices of the existing triangles. Two rings can retain
    # the shaded edge of the confirmed crown without flood-filling waterfront.
    links=defaultdict(set)
    for i in np.flatnonzero(eligible):
        for v in xyz[i]:
            links[tuple(np.round(v*200).astype(np.int64))].add(int(i))
    weak=eligible&(rgb[:,1]>rgb[:,0]*1.01)&(rgb[:,1]>=rgb[:,2]*.97)&(centers[:,2]>406.8)
    frontier=set(chosen)
    for _ in range(2):
        added=set()
        for i in frontier:
            for v in xyz[i]:
                added.update(j for j in links[tuple(np.round(v*200).astype(np.int64))]
                             if weak[j] and j not in chosen)
        chosen.update(added);frontier=added
    assert seeds<=chosen
    rec=override[node]
    keep=np.ones(len(xyz),dtype=bool);keep[list(chosen)]=False
    local=np.array(rec['vertices']).reshape(-1,3,3)
    areas=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)*.5
    records.append({'node':node,'source_owner_tree':60153,'removed_faces':[int(i) for i in sorted(chosen)],
                    'ray_seed_faces':sorted(seeds),'removed_area_m2':float(areas[list(chosen)].sum()),
                    'original_face_count':len(xyz),'new_face_count':int(keep.sum()),
                    'bounds_lv95':[xyz[list(chosen)].min((0,1)).tolist(),xyz[list(chosen)].max((0,1)).tolist()]})
    override[node]={**rec,'vertices':local[keep].reshape(-1,3).tolist(),
                    'uv_source_v_unflipped':uv[keep].reshape(-1,2).tolist()}

# The grey point at the stair is111mm outside the cadastral stair footprint,
# within the old blurred steel stringer. It is not labelled a tree remnant.
stair=shape(features['av_ei_flaechenelement_a.47309']['geometry'])
stair_guard=stair.buffer(.22).intersection(foot.union(stair))
volume={'mask':stair_guard,'lo':plan['floor_ln02_m']+.10,'hi':plan['stair_top_ln02_m']+1.12,'relative':False}
helpers=ast.parse((ROOT/'tools/prepare_limmat_sidewalk_cut.py').read_text())
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef)
                            and n.name in {'clip','fan','subtract'}],type_ignores=[]),'photo_clip_helpers','exec'))
stair_changed=[]
for node,rec in list(override.items()):
    m=np.array(manifest[node]['mbs'])
    if Point(m[:2]).distance(stair_guard)>m[3]:continue
    xyz=np.array(rec['vertices']).reshape(-1,3,3)+m[:3]
    tex=np.array(rec['uv_source_v_unflipped']).reshape(-1,3,2)
    vv=[];uu=[];dirty=False
    for tri,uv in zip(xyz,tex):
        pieces,did=subtract(np.c_[tri,uv],volume);dirty|=did
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        override[node]={**rec,'vertices':vv,'uv_source_v_unflipped':uu};stair_changed.append(node)
changed=sorted({q['node'] for q in records}|set(stair_changed))
result={'mask_basis':base['mask_basis']+'; G1_022r2: ray-attributed60153 lower photographic overhang removed as complete atlas-supported triangles plus two bounded shaded-neighbor rings, retaining original source. Separately replace old steel-stair fringe within220mm of surveyed stair, over already-built approach. No blanket river/boat/bridge clearance.',
        'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),
        'overrides':list(override.values()),'changed_nodes':len(override),
        'object_completion_changed_nodes':changed}
out=ROOT/'derived/bellevue/west_context/riviera_lower_object_cut.json'
result_text=json.dumps(result,separators=(',',':'))
basis_text=json.dumps({'canopy':records,'stair_changed_nodes':stair_changed,
    'stair_mask_lv95':mapping(stair_guard),'stair_height_band':[volume['lo'],volume['hi']],
    'diagnosed_tree_radius_m':radius,'color_is_supporting_evidence_only':True,
    'base_cut_sha256':result['base_cut_sha256'],'source_originals_preserved':True},indent=2)
out.write_text(result_text)
(DATA/'object_cut_basis.json').write_text(basis_text)
print(json.dumps({'changed_nodes':changed,'canopy':[{k:v for k,v in q.items() if k!='removed_faces'} for q in records],
                  'stair_changed':stair_changed,'bytes':out.stat().st_size},indent=2))
