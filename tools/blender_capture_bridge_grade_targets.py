"""Capture actual027 editable road geometry; no scene mutation."""
from pathlib import Path
import json,sys
import bpy
import numpy as np
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade'
sys.path.insert(0,str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest
assert bpy.context.scene['version']=='G1_027'
roles={'road_asphalt','road_concrete','road_joint','rail_steel','groove_floor','groove_wall','crossing_paint',
       'asphalt_road','asphalt_track','asphalt_walk','rail','drain','curb','paint','guard','foundation','mast'}
rows=[];arrays={}
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
    if ob.type!='MESH' or ob.hide_render or ob.get('surface_role') not in roles:continue
    if not ob.name.startswith(('BE_ROAD_','BE_PAVING_','BE_CROSSING_','BD_')):continue
    if ob.name.startswith('BD_MAST_') and ob.name.removeprefix('BD_MAST_').isdigit():continue
    v=np.array([ob.matrix_world@p.co for p in ob.data.vertices])
    if v[:,0].min()>-254 or v[:,0].max()<-297 or v[:,1].min()>155 or v[:,1].max()<110:continue
    assert not ob.data.library and ob.data.users==1,ob.name
    assert np.allclose(np.array(ob.matrix_world),np.eye(4),atol=1e-10),ob.name
    key='mesh_'+str(len(rows));arrays[key]=v
    ob.data.calc_loop_triangles()
    arrays[key+'_triangles']=np.array([t.vertices[:] for t in ob.data.loop_triangles],dtype=np.int32)
    rows.append(dict(name=ob.name,key=key,role=ob['surface_role'],before_fingerprint=mesh_digest(ob.data),source=ob.get('source_id')))
np.savez_compressed(D/'027_target_vertices.npz',**arrays)
(D/'027_target_objects.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('GRADE_TARGETS',len(rows),sum(len(arrays[r['key']]) for r in rows))
