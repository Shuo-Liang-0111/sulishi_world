"""Drop only exactly collinear, zero-area triangles after float32 refinement.

All positions and retained per-corner UVs are bit-identical. No visible area is
removed; genuinely small but nonzero faces are never discarded by this helper.
"""
import bpy
import numpy as np

def strip_zero_faces(mesh):
    bad=[p.index for p in mesh.polygons if p.area<1e-11]
    if not bad:return mesh,[]
    v=np.array([q.co[:] for q in mesh.vertices],dtype=np.float32)
    for i in bad:
        p=mesh.polygons[i];assert len(p.vertices)==3
        t=v[list(p.vertices)].astype(float)
        assert np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))==0,(mesh.name,i,'nonzero face must be reconstructed')
    keep=[p for p in mesh.polygons if p.index not in set(bad)]
    clean=bpy.data.meshes.new(mesh.name+'_CLEAN')
    clean.from_pydata(v.tolist(),[],[list(p.vertices) for p in keep]);clean.update()
    for m in mesh.materials:clean.materials.append(m)
    clean.polygons.foreach_set('material_index',np.array([p.material_index for p in keep],np.int32))
    clean.polygons.foreach_set('use_smooth',np.array([p.use_smooth for p in keep],np.bool_))
    corners=np.array([i for p in keep for i in p.loop_indices],np.int32)
    for layer in mesh.uv_layers:
        uv=np.empty(len(layer.data)*2,np.float32);layer.data.foreach_get('uv',uv)
        new=clean.uv_layers.new(name=layer.name);new.data.foreach_set('uv',uv.reshape(-1,2)[corners].ravel())
    assert not clean.validate(clean_customdata=False)
    assert all(p.area>1e-11 for p in clean.polygons)
    return clean,bad

if __name__=='__main__':
    from pathlib import Path
    import json,sys
    R=Path('F:/MyWorld/ZurichWorld');sys.path.insert(0,str(R/'tools'))
    from blender_geometry_fingerprint import mesh_digest
    assert bpy.context.scene['version']=='G1_027r2'
    path=R/'evidence/G1_027r2/construction.json';record=json.loads(path.read_text())
    cleanup=[]
    for row in record['after_fingerprints']:
        ob=bpy.data.objects[row['name']]
        assert json.loads(json.dumps(mesh_digest(ob.data)))==row['mesh_fingerprint']
        prior=ob.data;clean,bad=strip_zero_faces(prior)
        if bad:
            ob.data=clean
            if prior.users==0:bpy.data.meshes.remove(prior)
            cleanup.append(dict(name=ob.name,zero_area_faces=bad))
            row['mesh_fingerprint']=mesh_digest(ob.data)
    record['zero_area_cleanup']=cleanup
    path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('EXACT_ZERO_AREA_FACES_REMOVED',sum(len(q['zero_area_faces']) for q in cleanup),flush=True)
