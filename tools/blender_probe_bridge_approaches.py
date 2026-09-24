"""Capture only existing upper approach surfaces for a measured geometric join."""
from pathlib import Path
import json
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_deck';D.mkdir(exist_ok=True)
assert bpy.context.scene['version']=='G1_026'
rows=[]
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
    if ob.type!='MESH' or not (ob.name.startswith(('UB_GROUND_','BP_PAVING_','RQ_PAVING_','LM_PAVING_'))
        or ob.get('surface_role') in ['road_asphalt','road_concrete','road_joint']):continue
    v=np.array([ob.matrix_world@p.co for p in ob.data.vertices],dtype=float)
    if not len(v) or v[:,0].min()>-260 or v[:,0].max()<-300 or v[:,1].min()>158 or v[:,1].max()<102:continue
    triangles=[]
    ob.data.calc_loop_triangles()
    for face in ob.data.loop_triangles:
        q=v[list(face.vertices)]
        if np.cross(q[1]-q[0],q[2]-q[0])[2]<=1e-8:continue
        if q[:,0].min()>-258 or q[:,0].max()<-302 or q[:,1].min()>160 or q[:,1].max()<100:continue
        triangles.append(q.tolist())
    if triangles:rows.append(dict(object=ob.name,source=ob.get('source_id'),triangles=triangles))
assert rows
(D/'existing_approaches.json').write_text(json.dumps(dict(version='G1_026',origin=[2683775,1246700,400],surfaces=rows),separators=(',',':')),encoding='utf-8')
print('EXISTING_BRIDGE_APPROACHES',len(rows),sum(len(r['triangles']) for r in rows),flush=True)
