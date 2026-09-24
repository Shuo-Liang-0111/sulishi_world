"""Remove diagnosed leaf-textured remnants of the twelve already built trees.

This is a local, reference-reviewed replacement heuristic, not a general scene
segmentation model. Whole triangles avoid introducing another horizontal cut
band. Neighbour-tree ownership, unbuilt structures and low outside-bank objects
remain protected. The original photography and025 input stay unchanged.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
from shapely.geometry import shape,Point,Polygon
from shapely.ops import unary_union

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridgehead_bank'
P=json.loads((D/'build_input.json').read_text(encoding='utf-8'))
context=json.loads((D/'cut_basis.json').read_text(encoding='utf-8'))
guards=shape(context['guards'])
B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
rebuilt=unary_union([shape(P['source']['geometry']),shape(B['corridor']),shape(B['south_stair']),shape(P['cap'])])
av=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
buildings=unary_union([shape(f['geometry']).buffer(.30) for f in av
    if f.get('geometry') and f['properties']['art_txt'].startswith('Gebaeude')
    and shape(f['geometry']).distance(rebuilt)<30])
inventory=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
coords=np.array([f['geometry']['coordinates'] for f in inventory])
selected={t['source']['id']:t for t in P['trees']}
selected_indexes={i for i,f in enumerate(inventory) if f['id'] in selected}
basepath=R/'derived/bellevue/west_context/bridgehead_bank_cut.json'
base=json.loads(basepath.read_text());nodes={str(n) for n in base['bank_changed_nodes']}
manifest={str(q['node']):q for q in json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())['items']}
probes=json.loads((D/'rejected_face_atlas_input.json').read_text())
seed_faces={(q['node'],q['face']) for q in probes}
weights=np.array([[1-(i+.33)/5-(j+.33)/5,(i+.33)/5,(j+.33)/5]
                  for i in range(5) for j in range(5-i)])
spatial=np.array([[1/3]*3,[.9,.05,.05],[.05,.9,.05],[.05,.05,.9],
                  [.48,.48,.04],[.04,.48,.48],[.48,.04,.48]])
changed=[];decisions=[];seed_report=[]
for rec in base['overrides']:
    node=str(rec['node'])
    if node not in nodes:continue
    item=manifest[node];v=np.array(rec['vertices']).reshape(-1,3,3)
    tex=np.array(rec['uv_source_v_unflipped']).reshape(-1,3,2)
    rgb=np.array(Image.open(item['texture']).convert('RGB'),dtype=np.float64)
    h,w,_=rgb.shape;keep=[];removed=[]
    for i,(tri,uv) in enumerate(zip(v+np.array(item['mbs'][:3]),tex)):
        samples=weights@uv
        px=np.clip((samples[:,0]*w).astype(int),0,w-1);py=np.clip((samples[:,1]*h).astype(int),0,h-1)
        colors=rgb[py,px];red,green,blue=colors.T
        lit_leaf=(green>red*1.04)&(green>blue*1.10)&(green-red>3)&(green-blue>5)
        # The inspected atlas faces include blue daylight in deep leaf shadow,
        # e.g. RGB(47,65,75). Pure green-only selection leaves false walls.
        shaded_leaf=(green>red*1.12)&(green>blue*.72)&(green-red>7)&(colors.max(axis=1)<105)
        green_fraction=float(np.mean(lit_leaf|shaded_leaf))
        reason='not_leaf_texture';remove=False;owners=[]
        if green_fraction>=.50:
            points=spatial@tri
            nearest=np.linalg.norm(points[:,:2,None]-coords.T[None,:,:],axis=1).argmin(axis=1)
            owners=[inventory[j]['id'] for j in nearest]
            if all(j in selected_indexes for j in nearest):
                reason='height_or_extent_protection';valid=True
                for p,j in zip(points,nearest):
                    tree=selected[inventory[j]['id']];distance=np.linalg.norm(p[:2]-coords[j])
                    low=tree['ground_ln02_m']+.16 if rebuilt.covers(Point(p[:2])) else tree['ground_ln02_m']+3.4
                    if not (low<p[2]<tree['ground_ln02_m']+tree['height_m']+1.5 and distance<max(12.,tree['height_m']*.70)):
                        valid=False;break
                if valid:
                    plan=Polygon(tri[:,:2]);reason='unbuilt_structure_protection'
                    def overlaps(mask):
                        return (plan.intersection(mask).area>max(1e-6,plan.area*.02)) if plan.is_valid and plan.area>1e-8 else mask.covers(Point(tri[:,:2].mean(0)))
                    high_crown=all(p[2]>selected[inventory[j]['id']]['ground_ln02_m']+6.5 for p,j in zip(points,nearest))
                    # Buildings retain full-height protection. The small quay
                    # walls, stairs and shelters do not own foliage >6.5m above
                    # the tree bases; that conservative height is inferred.
                    protected=overlaps(buildings) or (overlaps(guards) and not high_crown)
                    if not protected:remove=True;reason='leaf_texture_and_built_tree_ownership'
            else:reason='neighbour_tree_protection'
        row=dict(node=node,face=i,green_fraction=green_fraction,owners=sorted(set(owners)),decision=reason)
        if (node,i) in seed_faces:seed_report.append(row)
        if remove:
            removed.append(i);decisions.append(row)
        else:keep.append(i)
    if removed:
        rec['vertices']=v[keep].reshape(-1,3).tolist();rec['uv_source_v_unflipped']=tex[keep].reshape(-1,2).tolist()
        changed.append(dict(node=node,before=len(v),after=len(keep),removed=len(removed)))
out=R/'derived/bellevue/west_context/bridgehead_bank_tree_remnants_cut.json'
base.update(base_cut_sha256=hashlib.sha256(basepath.read_bytes()).hexdigest(),
    mask_basis=base['mask_basis']+'; G1_025r1 actual upper-bank rays plus original image-atlas leaf samples: remove whole triangles owned by rebuilt inventory trees; protect other structures and unbuilt neighboring trees. Local heuristic, not semantic ground truth.',
    bank_remnant_changed_nodes=[r['node'] for r in changed])
out.write_text(json.dumps(base,separators=(',',':')),encoding='utf-8')
report=dict(version='G1_025r1',base_cut=basepath.relative_to(R).as_posix(),base_cut_sha256=base['base_cut_sha256'],
    changed=changed,removed_faces=decisions,diagnosed_seed_faces=seed_report,
    bounds_and_colour_are_reviewed_heuristic=True,originals_retained=True,visual_acceptance=False)
(D/'tree_remnant_replacement.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='removed_faces'},indent=2))
