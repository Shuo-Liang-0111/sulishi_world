"""Read-only snapshot of027 road and walkway supports for a bounded grade repair."""
from pathlib import Path
import json
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade'
assert bpy.context.scene['version']=='G1_027'
groups={'road': [], 'walk': [], 'bank': []}; names={k:[] for k in groups}
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
    if ob.type!='MESH' or ob.hide_render:continue
    role=ob.get('surface_role')
    kind=('road' if role in ['road_asphalt','road_concrete','road_joint','asphalt_road','asphalt_track']
          else 'walk' if role=='asphalt_walk'
          else 'bank' if ob.name.startswith(('UB_GROUND_','BP_PAVING_','LM_ASPHALT','RQ_PAVING_')) else None)
    if kind is None:continue
    v=np.array([ob.matrix_world@p.co for p in ob.data.vertices])
    if v[:,0].min()>-235 or v[:,0].max()<-320 or v[:,1].min()>175 or v[:,1].max()<95:continue
    ob.data.calc_loop_triangles();tri=v[np.array([t.vertices[:] for t in ob.data.loop_triangles])]
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    mask=(n[:,2]>.85*np.linalg.norm(n,axis=1))&(n[:,2]>1e-9)&(tri[:,:,0].max(1)>-320)&(tri[:,:,0].min(1)<-235)&(tri[:,:,1].max(1)>95)&(tri[:,:,1].min(1)<175)
    if mask.any():groups[kind].extend(tri[mask]);names[kind].append(ob.name)
np.savez_compressed(D/'027_surfaces.npz',**{k:np.array(v) for k,v in groups.items()})
(D/'027_surface_objects.json').write_text(json.dumps(names,indent=2),encoding='utf-8')
print('GRADE_REFERENCE',json.dumps({k:dict(objects=len(names[k]),triangles=len(v)) for k,v in groups.items()}))
