"""Restore actual evaluated matrices in a separate glTF review representation.

The raw GLB and lossless packages remain untouched. Buffer/image/animation
payloads are shared, byte-identical. Native parenting remains represented;
local matrices are solved in float64 from the captured native world matrices.
"""
from pathlib import Path
import copy,hashlib,itertools,json
import numpy as np
from inspect_glb import GLB
from workspace_paths import read_path,write_path

version='G1_027r15';folder=read_path(f'web/assets/{version}_current_r01')
raw_manifest=json.loads((folder/'manifest.json').read_text())
package=json.loads((folder/'runtime_manifest.json').read_text())
anchor_path=read_path(f'evidence/{version}/current_author_native_matrices.json');anchors=json.loads(anchor_path.read_text())
assert anchors['native_sha256']==raw_manifest['native_sha256']==package['native_sha256']
assert package['status']=='geometry_packaged_material_review_pending'
native={r['name']:r for r in anchors['objects']}
C=np.eye(4);C[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]
out=copy.deepcopy(package);out['chunks']=[];out['native_matrix_reference_sha256']=hashlib.sha256(anchor_path.read_bytes()).hexdigest()
out['native_matrix_restored']=True;out['raw_geometry_roundtrip_passed']=False;out['geometry_roundtrip_pending']=True
rows=[]
for chunk in package['chunks']:
    original=folder/chunk['file'];assert hashlib.sha256(original.read_bytes()).hexdigest()==chunk['sha256']
    source=GLB(original);doc=copy.deepcopy(source.doc)
    for animation in doc.get('animations',[]):
        assert all(channel['target']['path']=='weights' for channel in animation['channels']),'TRS animation requires an explicit matrix/animation adapter'
    worlds={};errors=[];bounds=[]
    for i,node in enumerate(doc['nodes']):
        name=node.get('extras',{}).get('native_object');assert name in native
        worlds[i]=C@np.asarray(native[name]['matrix_world'],float)@C.T
    for i,node in enumerate(doc['nodes']):
        name=node['extras']['native_object'];actual=source.world(i)
        if i in source.parents:
            parent=source.parents[i];assert doc['nodes'][parent]['extras']['native_object']==native[name]['parent']
            local=np.linalg.solve(worlds[parent],worlds[i])
        else:local=worlds[i]
        for field in ['translation','rotation','scale']:node.pop(field,None)
        node['matrix']=local.T.ravel().tolist();node['extras']['native_matrix_restored']=True
        displacement=0.
        if 'mesh' in node:
            for prim in doc['meshes'][node['mesh']]['primitives']:
                acc=doc['accessors'][prim['attributes']['POSITION']]
                corners=np.array(list(itertools.product(*zip(acc['min'],acc['max']))),float)
                old=corners@actual[:3,:3].T+actual[:3,3];new=corners@worlds[i][:3,:3].T+worlds[i][:3,3]
                displacement=max(displacement,float(np.max(np.linalg.norm(new-old,axis=1))))
                bounds.append(new)
        assert displacement<.005,('Unexpected large transform change',name,displacement)
        if displacement>1e-7:errors.append({'name':name,'maximum_bbox_corner_correction_m':displacement})
    assert {k:v for k,v in doc.items() if k!='nodes'}=={k:v for k,v in source.doc.items() if k!='nodes'}
    target=original.with_name(original.stem+'_native_matrix.gltf');assert not target.exists()
    target.write_text(json.dumps(doc,indent=2),encoding='utf-8');source.close()
    check=GLB(target)
    for i in worlds:assert np.max(abs(check.world(i)-worlds[i]))<1e-10
    assert {k:v for k,v in check.doc.items() if k!='nodes'}=={k:v for k,v in doc.items() if k!='nodes'}
    check.close();xyz=np.concatenate(bounds) if bounds else np.empty((0,3))
    entry={**chunk,'file':str(target.relative_to(folder)).replace('\\','/'),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
       'original_package_file':chunk['file'],'original_package_sha256':chunk['sha256'],'native_matrix_restored':True,
       'bounds_yup':[xyz.min(0).tolist(),xyz.max(0).tolist()] if len(xyz) else None}
    out['chunks'].append(entry);rows.append({'file':entry['file'],'node_matrices_checked':len(worlds),'corrections':errors})
    print('NATIVE_MATRIX_RESTORED',target.name,len(worlds),max((r['maximum_bbox_corner_correction_m'] for r in errors),default=0),flush=True)
(folder/'runtime_native_matrix_manifest.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
write_path(f'evidence/{version}/native_matrix_restoration.json').write_text(json.dumps({'version':version,'native_sha256':anchors['native_sha256'],
 'native_matrix_reference_sha256':out['native_matrix_reference_sha256'],'chunks':rows,'raw_glb_unchanged':True,'geometry_image_animation_buffers_changed':False,
 'full_surface_comparison_pending':True},indent=2),encoding='utf-8')
