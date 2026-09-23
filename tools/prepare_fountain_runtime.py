"""Prepare lighting and deformation receipts in a disposable native process."""
import bpy, hashlib, json, sys
import numpy as np
from pathlib import Path

R=Path('F:/MyWorld/ZurichWorld'); s=bpy.context.scene; V=s['version']
assert V=='G1_018r3'
D=R/'derived/runtime_occlusion'/V; D.mkdir(parents=True,exist_ok=True)
E=R/'evidence'/V
assert not (D/'manifest.json').exists(),'Inspect the existing prepared charts before retrying'
previous=json.loads((R/'derived/runtime_occlusion/G1_017r1/manifest.json').read_text())
records=[dict(x) for x in previous['receivers']]
assert len(records)==562
s.frame_set(1); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
new_names=['F59_GRANITE_BASIN','F59_GRANITE_PEDESTAL','F59_MINERAL_FOOT_BEDDING']
for name in new_names:
    ob=bpy.data.objects[name]; evaluated=ob.evaluated_get(deps); me=evaluated.to_mesh()
    v=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',v)
    ids=np.empty(len(me.loops),np.int32); me.loops.foreach_get('vertex_index',ids)
    records.append({'name':name,'topology_sha256':hashlib.sha256(v.tobytes()+ids.tobytes()).hexdigest(),
                    'loops':len(ids),'vertices':len(v)//3,'uv_key':f'uv_{len(records)}'})
    evaluated.to_mesh_clear()
manifest=dict(previous); manifest.update(version=V,native=bpy.data.filepath,receivers=records)
(D/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Join/weld only an evaluated UV proxy. Native geometry and primary maps stay intact.
exec(compile((R/'tools/prepare_contiguous_light_uv.py').read_text(), 'prepare_contiguous_light_uv','exec'))

water=bpy.data.objects['F59_WATER_SURFACE']; assert not water.modifiers
assert len(water.data.shape_keys.key_blocks)==2
copy=water.data.copy()
assert copy.shape_keys and copy.shape_keys!=water.data.shape_keys
assert copy.shape_keys.animation_data and copy.shape_keys.animation_data.action
keys=water.data.shape_keys.key_blocks
points=np.asarray([p.co[:] for p in keys[0].data]); moved=np.asarray([p.co[:] for p in keys[1].data])
delta=moved-points; edge=np.linalg.norm(points[:,:2],axis=1)>1.7839
weights=[]
for frame in [1,11,21,31,41,51,61,71,81]:
    s.frame_set(frame); weights.append({'frame':frame,'weight':keys[1].value})
s.frame_set(1)
assert np.max(np.abs(delta[edge]))<1e-7
assert np.max(np.abs(delta[:,:2]))<1e-7 and 0<np.max(np.abs(delta[:,2]))<.003
record={'version':V,'source_native':bpy.data.filepath,'native_saved':False,
        'water_shape_keys_copied':True,'deformation_vertex_count':len(points),
        'max_displacement_m':float(np.max(np.abs(delta[:,2]))),'boundary_displacement_m':float(np.max(np.abs(delta[edge]))),
        'weights':weights,'fps':s.render.fps/s.render.fps_base,'native_frame_range':[s.frame_start,s.frame_end],
        'added_static_diffuse_receivers':new_names,'receiver_count':len(records),
        'water_model':'Native bounded morph approximation, not fluid simulation',
        'accepted':False}
(E/'runtime_preparation.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record),flush=True)
