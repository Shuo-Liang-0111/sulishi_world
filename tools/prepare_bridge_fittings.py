"""Prepare photo-constrained bridge fittings; do not infer surveyed lamp models."""
from pathlib import Path
import ast, hashlib, json
import numpy as np
from workspace_paths import read_path, write_path

source_path=read_path('derived/bridge_fittings/source_probe.json')
source=json.loads(source_path.read_text())
assert source['base_version']=='G1_027r3' and len(source['lamps'])==13
tree=ast.parse(read_path('tools/blender_probe_bridge_context.py').read_text())
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='connected_face_components')
scope={}
exec(compile(ast.Module(body=[function],type_ignores=[]),'diagnostic_weld','exec'),scope)
components={o['name']:scope['connected_face_components'](o['vertices'],o['faces']) for o in source['context']}
byname={o['name']:o for o in source['context']}
removals={}
lamps=[]
for item in source['lamps']:
    feature=item['feature'];mast=item['mast'];fid=feature['properties']['objectid']
    # The extra point on 1804 has a different orientation but no readable body.
    # Preserve it as an unresolved fixture, not a guessed duplicate lamp.
    if fid==37745:continue
    xy=np.array(mast['xy'])-source['origin'][:2];photo=[];points=[]
    for name,groups in components.items():
        for group in groups:
            lo=np.array(group['min']);hi=np.array(group['max']);centre=(lo+hi)/2
            if hi[2]-lo[2]<.7 and 13<lo[2]<17 and np.linalg.norm(centre[:2]-xy)<2:
                photo.append(dict(object=name,component=group['component'],faces=group['face_ids']))
                removals.setdefault(name,set()).update(group['face_ids'])
                mesh=byname[name]
                points.extend(np.array(mesh['vertices'])[np.array(mesh['faces'])[group['face_ids']].ravel()])
    row=dict(id=str(fid),official_feature=feature,mast=mast,xy=xy.tolist(),photo_components=photo)
    if points:
        points=np.unique(np.round(points,4),axis=0)
        row['photo_bounds']=[points.min(0).tolist(),points.max(0).tolist()]
        row['head_z']=float(np.median(points[:,2]))
        delta=np.median(points[:,:2],axis=0)-xy
        row['direction']=(delta/np.linalg.norm(delta)).tolist()
        row['height_basis']='Median photographed fixture vertices; body fabrication inferred.'
    lamps.append(row)
offsets=[r['head_z']-(r['mast']['base_ln02_m']-400) for r in lamps if 'head_z' in r]
height=float(np.median(offsets))
for row in lamps:
    if 'head_z' not in row:
        row['head_z']=row['mast']['base_ln02_m']-400+height
        # Opposite sides use the observed mirrored head alignment. Raw EWZ
        # orientation is retained, not silently treated as degrees or gon.
        south=int(row['mast']['id'].split('.')[-1]) in [1804,1807,1808,1811,1812,1815]
        d=np.array([.74,.67])*(1 if south else -1)
        row['direction']=(d/np.linalg.norm(d)).tolist()
        row['height_basis']='Inferred repeated fixture using bridge photo median height above measured mast foot.'
    row['body_dimensions_m']=[1.18,.46,.18]
    row['body_basis']='Finite low-profile housing fitted to readable photo footprints; not a surveyed product model.'

# Southeast bridgehead: two complete high flag blobs and their detached shards.
# The third source flag is visible in the original tile but was already removed
# by the earlier bank/tree cut; the immutable original is still present.
for name,ids in {'CTX_I3S_34256':[4,8,10],'CTX_I3S_34216':[2,4]}.items():
    for ident in ids:
        group=next(c for c in components[name] if c['component']==ident)
        assert group['min'][2]>18 and group['max'][2]<26
        removals.setdefault(name,set()).update(group['face_ids'])
flags=[dict(id='SE_ZH_WEST',kind='ZH',xy=[-273.45,117.42],top_z=25.12,phase=.3),
       dict(id='SE_CH_MIDDLE',kind='CH',xy=[-268.12,115.97],top_z=25.12,phase=1.2),
       dict(id='SE_ZH_EAST',kind='ZH',xy=[-262.9,112.0],top_z=24.92,phase=2.0)]
for row in flags:
    row.update(rest_cloth_size_m=[4.,4.],placement_basis='Inferred pole anchor from source flag envelope and orthophoto promenade; not a surveyed point.',
               state_basis='Flagged source-scan appearance, not a claim of an everyday calendar state.',
               construction_basis='Official 3-per-corner arrangement and 4x4m flags; pole hardware and cloth pose inferred.')
spec=dict(base_version='G1_027r3',version='G1_027r4',origin=source['origin'],
    source_probe_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),lamps=lamps,flags=flags,
    unresolved_official_fixture=next(x['feature'] for x in source['lamps'] if x['feature']['properties']['objectid']==37745),
    photo_removals=[dict(object=name,face_ids=sorted(ids)) for name,ids in sorted(removals.items())],
    lamp_mount_median_height_m=height,scope='12 existing bridge masts and southeast flag group; north flag group and other corners remain pending.',
    references=['sources/features/bridge_fittings/ewz_brennstelle_p.geojson',
                'sources/references/bridge_fittings/city_flag_instructions_2016.pdf',
                'sources/references/swissimage-bellevue-west.json'],
    interaction_scope='No research task or agent. Passive physical fittings; street lights in daytime off state. Runtime collision/export pending.')
write_path('derived/bridge_fittings/build_input.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
print(json.dumps(dict(lamps=len(lamps),flags=len(flags),photo_tiles=len(removals),removed_faces=sum(map(len,removals.values())),photo_height_median=height,unresolved_extra_fixture=37745)))
