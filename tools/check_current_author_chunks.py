"""Independently compare actual exported surfaces with saved-native expectations.

Every triangle is checked, with winding, split normals and exported UV channels.
Passing geometry is not material equivalence, interaction or full-world approval.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
import numpy as np
from scipy.spatial import cKDTree
from inspect_glb import GLB
from workspace_paths import read_path,write_path

p=argparse.ArgumentParser();p.add_argument('version');p.add_argument('--attempt',default='r01');p.add_argument('--partial',action='store_true')
p.add_argument('--resume-verified',action='store_true',help='Reuse the previously checked immutable static prefix, with its source/report fingerprints and strict measured errors.')
p.add_argument('--native-matrices',action='store_true',help='Check the actual external glTF representation with captured native matrices restored.')
args=p.parse_args()
folder=read_path(f'web/assets/{args.version}_current_{args.attempt}')
manifest=json.loads((folder/'manifest.json').read_text())
representation='native_matrix' if args.native_matrices else 'raw_glb'
report_stem=f'current_author_{args.attempt}'+('_native_matrix' if args.native_matrices else '')
runtime_chunks={}
if args.native_matrices:
    runtime_manifest=json.loads((folder/'runtime_native_matrix_manifest.json').read_text())
    assert runtime_manifest['native_sha256']==manifest['native_sha256'] and runtime_manifest['native_matrix_restored']
    runtime_chunks={c['source_sha256']:c for c in runtime_manifest['chunks']}
assert manifest['version']==args.version
if not args.partial:assert manifest['status']=='geometry_candidate_exported_material_review_pending'
R=np.array([[1.,0.,0.],[0.,0.,1.],[0.,-1.,0.]])


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def unit(a):
    lengths=np.linalg.norm(a,axis=-1,keepdims=True)
    return np.divide(a,lengths,out=np.zeros_like(a),where=lengths>1e-12)


def compare_surface(actual,expected):
    ap,an,au,am=actual;ep,en,eu,em,native_normals=expected
    assert ap.shape==ep.shape and len(au)==len(eu)
    if not len(ep):return dict(triangles=0)
    ed=np.linalg.norm(np.cross(ep[:,1]-ep[:,0],ep[:,2]-ep[:,0]),axis=1)==0
    ad=np.linalg.norm(np.cross(ap[:,1]-ap[:,0],ap[:,2]-ap[:,0]),axis=1)==0
    assert int(ed.sum())==int(ad.sum()),'Degenerate triangle count changed'
    # Exact zero-area native faces have no defined surface normal. Preserve
    # their geometry/UV/material and report them; never suppress real faces.
    en=en.copy();an=an.copy();en[ed]=0;an[ad]=0
    tree=cKDTree(ap.mean(axis=1));distance,nearest=tree.query(ep.mean(axis=1))
    assert np.max(distance)<.00015,('Missing surface',float(np.max(distance)))
    # Large meshes normally have unique centres. Vectorize this common path,
    # then explicitly disambiguate coincident triangles, without dropping any.
    choices=np.full(len(ep),-1,np.int32);errors=[]
    for shift in range(3):
        pos=np.max(abs(np.roll(ap[nearest],shift,axis=1)-ep),axis=(1,2))
        norm=np.max(abs(np.roll(an[nearest],shift,axis=1)-en),axis=(1,2))
        uv=np.zeros(len(ep))
        for aa,ee in zip(au,eu):uv=np.maximum(uv,np.max(abs(np.roll(aa[nearest],shift,axis=1)-ee),axis=(1,2)))
        ok=(pos<.0001)&(norm<.000002)&(uv<.000002)&(am[nearest]==em)
        choices[(choices<0)&ok]=shift;errors.append((pos,norm,uv))
    used=set();fallback=0;augmentations=0
    matched=np.full(len(ep),-1,np.int32);matched_shift=np.empty(len(ep),np.int8)
    owner=np.full(len(ap),-1,np.int32);candidate_cache={}
    def valid_candidates(i):
        if i not in candidate_cache:
            edges=[]
            for j in tree.query_ball_point(ep[i].mean(0),.00015):
                if am[j]!=em[i]:continue
                for shift in range(3):
                    pe=float(np.max(abs(np.roll(ap[j],shift,axis=0)-ep[i])))
                    if pe>=.0001:continue
                    ne=float(np.max(abs(np.roll(an[j],shift,axis=0)-en[i])))
                    ue=max((float(np.max(abs(np.roll(aa[j],shift,axis=0)-ee[i]))) for aa,ee in zip(au,eu)),default=0.)
                    if ne<.000002 and ue<.000002:edges.append((pe/.0001+ne/.000002+ue/.000002,int(j),shift))
            candidate_cache[i]=sorted(edges)
        return candidate_cache[i]
    def augment(start):
        # Coincident source triangles can have almost identical UVs. Greedy
        # tolerance matching can consume another triangle's sole valid match.
        # Find an augmenting path using the same strict full-corner criteria;
        # no triangle is dropped and no tolerance is widened.
        queue=[start];seen={start};parent={};cursor=0
        while cursor<len(queue):
            current=queue[cursor];cursor+=1
            for _,target,rotation in valid_candidates(current):
                previous=int(owner[target])
                if previous<0:
                    while True:
                        matched[current]=target;matched_shift[current]=rotation;owner[target]=current;used.add(target)
                        if current==start:return True
                        current,target,rotation=parent[current]
                elif previous not in seen:
                    seen.add(previous);parent[previous]=(current,target,rotation);queue.append(previous)
        return False
    for i in range(len(ep)):
        j=int(nearest[i]);shift=int(choices[i])
        if shift>=0 and j not in used:
            pe,ne,ue=(float(e[i]) for e in errors[shift])
        else:
            fallback+=1;found=False
            for _,j,shift in valid_candidates(i):
                if j not in used:found=True;break
            if not found and augment(i):
                augmentations+=1;continue
            if not found:
                candidates=[]
                for candidate in tree.query_ball_point(ep[i].mean(0),.00015)[:30]:
                    candidates.append({'triangle':int(candidate),'already_used':candidate in used,
                      'position':ap[candidate].tolist(),'normal':an[candidate].tolist(),
                      'uv':[x[candidate].tolist() for x in au],'material_slot':int(am[candidate])})
                raise AssertionError({'reason':'Triangle/winding/normal/UV/material mismatch','triangle':i,
                  'expected_position':ep[i].tolist(),'expected_normal':en[i].tolist(),'expected_uv':[x[i].tolist() for x in eu],
                  'expected_material_slot':int(em[i]),'candidates':candidates})
        used.add(j);matched[i]=j;matched_shift[i]=shift;owner[j]=i
    assert len(used)==len(ap)
    maxima=[0.,0.,0.];mapped=an[matched].copy()
    for shift in range(3):
        mask=matched_shift==shift
        if not np.any(mask):continue
        ids=matched[mask];mapped[mask]=np.roll(an[ids],shift,axis=1)
        pe=float(np.max(abs(np.roll(ap[ids],shift,axis=1)-ep[mask])))
        ne=float(np.max(abs(mapped[mask]-en[mask])))
        ue=max((float(np.max(abs(np.roll(aa[ids],shift,axis=1)-ee[mask]))) for aa,ee in zip(au,eu)),default=0.)
        maxima=[max(a,b) for a,b in zip(maxima,[pe,ne,ue])]
    assert maxima[0]<.0001 and maxima[1]<.000002 and maxima[2]<.000002
    defined=np.linalg.norm(native_normals,axis=-1)>1e-12
    valid=(~ed[:,None])&defined
    dots=np.clip(np.sum(mapped*native_normals,axis=-1)[valid],-1,1)
    native_angle=float(np.degrees(np.arccos(dots)).max()) if dots.size else 0.
    return dict(triangles=len(ep),native_zero_area_triangles=int(ed.sum()),max_world_position_error_m=maxima[0],
                native_undefined_normal_triangles=int(np.any(~defined,axis=1).sum()),
                max_exporter_normal_component_error=maxima[1],max_native_normal_angle_error_degrees=native_angle,
                native_normal_difference_requires_review=native_angle>.05,max_uv_error=maxima[2],coincident_or_ambiguous_triangles=fallback,
                coincident_matching_augmentations=augmentations)


report={'version':args.version,'attempt':args.attempt,'representation':representation,'native_sha256':manifest['native_sha256'],'chunks':[],
        'normal_reference':'Blender 4.5.13 glTF rounds local corner normals to four decimals, normalizes, then converts axes. Native angular loss is separately reported.',
        'full_export_finished':manifest['status']=='geometry_candidate_exported_material_review_pending',
        'materials_fully_converted':False,'full_runtime_published':False,'natural_use_verified':False}
previous_chunks={}
if args.resume_verified:
    previous_path=read_path(f'evidence/{args.version}/{report_stem}_roundtrip.json')
    previous=json.loads(previous_path.read_text())
    assert previous['native_sha256']==manifest['native_sha256'] and previous['version']==args.version and previous['attempt']==args.attempt
    assert previous['normal_reference']==report['normal_reference']
    assert previous.get('representation','raw_glb')==representation
    # Static results remain applicable: the revised branch below only changes
    # shape-key normal provenance. Do not reuse an already checked morph chunk.
    previous_chunks={c['file']:c for c in previous['chunks']}
    report['reused_static_checkpoint_sha256']=sha(previous_path)
    report['reused_static_chunks']=[]
started=time.time()
for chunk in manifest['chunks']:
    representation_row=runtime_chunks[chunk['sha256']] if args.native_matrices else chunk
    if chunk['file'] in previous_chunks and not chunk['contains_native_water_animation']:
        cached=previous_chunks[chunk['file']]
        assert cached['sha256']==representation_row['sha256'] and cached['nodes']==len(chunk['native_objects'])
        assert {r['name'] for r in cached['checks']}=={r['name'] for r in chunk['geometry'] if r['triangles']}
        assert sum(r['triangles'] for r in cached['checks'])==sum(r['triangles'] for r in chunk['geometry'])
        for check in cached['checks']:
            assert check['max_world_position_error_m']<.0001 and check['max_exporter_normal_component_error']<.000002 and check['max_uv_error']<.000002
            assert 'native_undefined_normal_triangles' in check
        assert (folder/chunk['file']).stat().st_size==chunk['bytes']
        if args.native_matrices:assert sha(folder/representation_row['file'])==representation_row['sha256']
        assert sha(Path(chunk['expected_file']))==chunk['expected_sha256']
        report['chunks'].append(cached);report['reused_static_chunks'].append(chunk['file'])
        print('CURRENT_STATIC_CHECK_REUSED',chunk['file'],flush=True)
        continue
    path=folder/representation_row['file'];assert sha(path)==representation_row['sha256']
    expected_path=Path(chunk['expected_file']);assert sha(expected_path)==chunk['expected_sha256']
    glb=GLB(path);doc=glb.doc;source=np.load(expected_path,allow_pickle=False)
    nodes={n['extras']['native_object']:(i,n) for i,n in enumerate(doc['nodes']) if 'native_object' in n.get('extras',{})}
    assert set(nodes)==set(chunk['native_objects']),('Node coverage',chunk['collection'],set(chunk['native_objects'])-set(nodes))
    geometry_names={r['name'] for r in chunk['geometry'] if r['triangles']}
    assert {name for name,(_,node) in nodes.items() if 'mesh' in node}==geometry_names
    checks=[]
    for row in chunk['geometry']:
        if not row['triangles']:continue
        index,node=nodes[row['name']];assert node['extras']['construction_version']==args.version
        matrix=glb.world(index);normal_matrix=np.linalg.inv(matrix[:3,:3]).T
        key=row['key'];xyz=source[key+'_positions'];tri=source[key+'_triangles'];loops=source[key+'_triangle_loops']
        wm=source[key+'_matrix'];ep=((xyz@wm[:3,:3].T+wm[:3,3])@R.T)[tri]
        native_n=source[key+'_corner_normals'];full_normal=unit(native_n@np.linalg.inv(wm[:3,:3])@R.T)[loops]
        # Verified against the installed io_scene_gltf2/primitive_extract.py
        # and constants.py (ROUNDING_DIGIT=4). Do not loosen a raw tolerance
        # to hide this export behaviour: reproduce it, and report native loss.
        export_basis=native_n
        if chunk['contains_native_water_animation'] and row['name']=='F59_WATER_SURFACE':
            if key+'_export_basis_normals' in source:
                export_basis=source[key+'_export_basis_normals']
            else:
                # The sealed first attempt archived Mesh.corner_normals. The
                # exporter instead calls Basis.normals_split_get for morphs.
                # Use a separately read same-native reference, never rewrite
                # the original expected arrays or widen the error tolerance.
                ref=json.loads(read_path(f'evidence/{args.version}/current_water_key_normals.json').read_text())
                assert ref['native_sha256']==manifest['native_sha256'] and ref['object']==row['name']
                assert hashlib.sha256(xyz.tobytes()).hexdigest()==ref['mesh_positions_sha256']
                loop_vertices=np.full(ref['loops'],-1,np.int32);loop_vertices[loops.ravel()]=tri.ravel()
                assert (loop_vertices>=0).all() and hashlib.sha256(loop_vertices.tobytes()).hexdigest()==ref['loop_vertex_indices_sha256']
                norm_path=Path(ref['array_file']);assert sha(norm_path)==ref['array_sha256']
                with np.load(norm_path,allow_pickle=False) as norm_data:export_basis=norm_data['basis_loop_normals'].copy()
            assert export_basis.shape==native_n.shape
        exported_n=np.round(export_basis,4);exported_n=unit(exported_n)
        exported_n[np.all(exported_n==0,axis=1),2]=1
        en=unit(exported_n@np.linalg.inv(wm[:3,:3])@R.T)[loops]
        em=source[key+'_triangle_materials']
        ap=[];an=[];au=[];am=[];uv_channels=None
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            assert primitive.get('mode',4)==4
            attrs=primitive['attributes'];ids=glb.accessor(primitive['indices']).ravel()
            assert len(ids)%3==0
            pos=glb.accessor(attrs['POSITION']);normal=glb.accessor(attrs['NORMAL'])
            ap.append((pos@matrix[:3,:3].T+matrix[:3,3])[ids].reshape(-1,3,3))
            an.append(unit(normal@normal_matrix.T)[ids].reshape(-1,3,3))
            channels=sorted(k for k in attrs if k.startswith('TEXCOORD_'))
            if uv_channels is None:uv_channels=channels;au=[[] for _ in channels]
            assert channels==uv_channels,('Per-primitive UV channels need explicit routing',row['name'])
            for parts,channel in zip(au,channels):parts.append(glb.accessor(attrs[channel])[ids].reshape(-1,3,2))
            if 'material' in primitive:
                name=doc['materials'][primitive['material']]['name'];assert name in row['materials'],(row['name'],name,row['materials'])
                material_index=row['materials'].index(name)
            else:material_index=0;assert not row['materials'] or row['materials']==[None]
            am.append(np.full(len(ids)//3,material_index,np.int32))
        # Blender flips the image V coordinate at export. Current meshes use
        # native layer order; unexpected channel routing fails instead of guessing.
        eu=[];uv_conversion_loss=0.
        for channel in uv_channels:
            uv_index=int(channel.split('_')[-1]);native_uv=source[key+f'_uv{uv_index}']
            precise_uv=native_uv.astype(np.float64).copy();precise_uv[:,1]=1-precise_uv[:,1]
            # V flipping is stored in a float32 glTF accessor. Quantify that
            # representation loss instead of comparing to an impossible f64
            # result or relaxing the surface/UV matching threshold.
            uv=precise_uv.astype(np.float32).astype(np.float64)
            uv_conversion_loss=max(uv_conversion_loss,float(abs(uv-precise_uv).max()))
            eu.append(uv[loops])
        try:
            result=compare_surface((np.concatenate(ap),np.concatenate(an),[np.concatenate(x) for x in au],np.concatenate(am)),(ep,en,eu,em,full_normal))
        except AssertionError as error:
            failure={'version':args.version,'file':chunk['file'],'object':row['name'],'detail':error.args,'accepted':False}
            write_path(f'evidence/{args.version}/{report_stem}_surface_failure.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
            raise AssertionError((chunk['file'],row['name'],error.args[0].get('reason') if isinstance(error.args[0],dict) else error.args)) from None
        checks.append(dict(name=row['name'],uv_channels=uv_channels,max_native_uv_float32_conversion_loss=uv_conversion_loss,**result))
    glb.close();source.close()
    report['chunks'].append({'collection':chunk['collection'],'file':chunk['file'],'representation_file':representation_row['file'],'sha256':representation_row['sha256'],'nodes':len(nodes),'checks':checks})
    report['elapsed_seconds']=time.time()-started
    write_path(f'evidence/{args.version}/{report_stem}_roundtrip.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CURRENT_CHUNK_ROUNDTRIP',chunk['file'],len(checks),sum(r['triangles'] for r in checks),flush=True)
report['all_available_chunks_passed']=True
report['geometry_nodes_checked']=sum(len(c['checks']) for c in report['chunks'])
report['triangles_checked']=sum(r['triangles'] for c in report['chunks'] for r in c['checks'])
report['native_normal_loss_review_objects']=[r['name'] for c in report['chunks'] for r in c['checks'] if r.get('native_normal_difference_requires_review')]
report['native_undefined_normal_objects']=[{'name':r['name'],'triangles':r['native_undefined_normal_triangles']} for c in report['chunks'] for r in c['checks'] if r.get('native_undefined_normal_triangles')]
write_path(f'evidence/{args.version}/{report_stem}_roundtrip.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='chunks'}),flush=True)
