"""Measure exact-topology leaf instancing opportunities without altering trees.

Native geometry, leaf identity and morphology remain authoritative. Fit residuals
and shading errors are reported separately; a position fit is not visual proof.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import write_path,validate_native

s=bpy.context.scene;native=validate_native(bpy.data.filepath)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
names=['BE_TREE_69773_LEAVES','UB_TREE_2038_LEAVES']
for prefix in ['LM_TREE_','RQ_TREE_']:
    options=sorted(o.name for o in s.objects if o.type=='MESH' and o.name.startswith(prefix) and o.name.endswith('_LEAVES'))
    assert options,prefix
    names.append(options[0])
rows=[]
for name in names:
    ob=bpy.data.objects[name];mesh=ob.data
    row=dict(object=name,vertices=len(mesh.vertices),polygons=len(mesh.polygons),geometry_modified=False)
    counts=np.empty(len(mesh.polygons),dtype=np.int32);mesh.polygons.foreach_get('loop_total',counts)
    if not np.all(counts==3):
        row.update(eligible=False,reason='Non-triangle leaf topology requires separate handling');rows.append(row);continue
    loops=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loops);faces=loops.reshape(-1,3)
    changes=np.flatnonzero(faces[:,0]!=faces[0,0])
    if not len(changes):
        row.update(eligible=False,reason='No repeated fan groups');rows.append(row);continue
    fcount=int(changes[0]);vcount=int(faces[fcount].min());count=len(mesh.vertices)//vcount
    if not (len(mesh.vertices)==count*vcount and len(faces)==count*fcount):
        row.update(eligible=False,reason='Mixed component sizes');rows.append(row);continue
    pattern=faces[:fcount]
    expected=pattern[None,:,:]+np.arange(count)[:,None,None]*vcount
    if not np.array_equal(faces.reshape(count,fcount,3),expected):
        row.update(eligible=False,reason='Per-leaf topology differs');rows.append(row);continue
    vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',vertices)
    leaves=vertices.astype(np.float64).reshape(count,vcount,3)
    centers=leaves.mean(1);centered=leaves-centers[:,None,:];reference=centered[0]
    if np.linalg.matrix_rank(reference)<3:
        row.update(eligible=False,reason='Planar leaf basis needs a separate surface-normal parameter');rows.append(row);continue
    transforms=np.einsum('iv,nvj->nij',np.linalg.pinv(reference),centered)
    reconstructed=np.einsum('vi,nij->nvj',reference,transforms)
    residual=np.linalg.norm(centered-reconstructed,axis=2)
    uv=np.empty(len(mesh.loops)*2,dtype=np.float32);mesh.uv_layers.active.data.foreach_get('uv',uv)
    uv=uv.reshape(count,fcount*3,2)
    uv_error=float(np.max(abs(uv-uv[:1])))
    colors=mesh.color_attributes.get('LeafColor');color_error=None
    if colors and colors.domain=='POINT':
        values=np.empty(len(colors.data)*4,dtype=np.float32);colors.data.foreach_get('color',values)
        values=values.reshape(count,vcount,4).astype(np.float64)
        if (values[0,0,:3]>0).all():
            pattern_color=values[0,:,:3]/values[0,0,:3]
            color_error=float(np.max(abs(values[:,:,:3]-values[:,0,None,:3]*pattern_color[None,:,:])))
    normals=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('normal',normals)
    normals=normals.reshape(count,vcount,3).astype(np.float64)
    normal_error=None
    determinants=np.linalg.det(transforms)
    if (abs(determinants)>1e-9).all() and (np.linalg.norm(normals,axis=2)>.9).all():
        transformed=np.einsum('vi,nij->nvj',normals[0],np.linalg.inv(transforms).transpose(0,2,1))
        transformed/=np.linalg.norm(transformed,axis=2)[:,:,None]
        cosine=np.clip(np.sum(transformed*normals,axis=2),-1,1)
        angles=np.degrees(np.arccos(cosine));normal_error=dict(max=float(angles.max()),p99=float(np.percentile(angles,99)))
    max_error=float(residual.max())
    row.update(eligible=max_error<.0001 and uv_error<1e-6 and color_error is not None and color_error<1e-6,
        leaves=count,vertices_per_leaf=vcount,triangles_per_leaf=fcount,
        max_affine_position_error_m=max_error,p99_affine_position_error_m=float(np.percentile(residual,99)),
        uv_template_error=uv_error,color_factor_error=color_error,normal_error_degrees=normal_error,
        native_attribute_bytes_estimate=len(mesh.vertices)*48+len(faces)*12,
        affine_instance_bytes_estimate=count*(12*4+3*4)+vcount*48+fcount*12,
        note='Affine position/color fit only. Runtime normal handling, finite precision, rendering and draw cost still require actual validation.')
    rows.append(row)
report=dict(version=s['version'],native=str(native),native_sha256=digest,examples=rows,
    native_unmodified=True,instanced_assets_created=False,visual_equivalence_verified=False,
    runtime_performance_measured=False)
target=write_path(f'evidence/{s["version"]}/leaf_instancing_profile.json')
target.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('LEAF_INSTANCING_PROFILE',json.dumps(report),flush=True)
