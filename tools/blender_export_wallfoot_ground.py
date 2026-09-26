"""Read actual nearby photographic triangles for bounded joint diagnosis."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

s=bpy.context.scene
assert s['version'] in ['G1_027r15','G1_027r16']
d=json.loads(read_path('derived/stadelhofen_joint/G1_027r16/construction.json').read_text())
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]
ob=bpy.data.objects['CTX_I3S_32639'];me=ob.data
assert not ob.modifiers
p=np.asarray([ob.matrix_world@v.co for v in me.vertices])
q=np.c_[(p[:,:2]-A)@U,(p[:,:2]-A)@N,p[:,2]]
me.calc_loop_triangles();rows=[]
for t in me.loop_triangles:
    pts=q[list(t.vertices)]
    low=pts.min(axis=0);high=pts.max(axis=0)
    if np.any(high<np.array([12.6,-1.5,10.1])) or np.any(low>np.array([14.4,.7,11.5])):continue
    rows.append({'triangle':t.index,'polygon':t.polygon_index,'vertices':list(t.vertices),
                 'uvz':pts.tolist(),'loops':list(t.loops),
                 'uv':[list(me.uv_layers.active.data[i].uv) for i in t.loops] if me.uv_layers.active else None,
                 'material_index':me.polygons[t.polygon_index].material_index})
with Path(bpy.data.filepath).open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
out={'native_sha256':digest,'process_id':os.getpid(),'object':ob.name,'mesh':mesh_digest(me),
     'frame':d['frame'],'rows':rows,'native_saved':False}
write_path('derived/stadelhofen_joint/G1_027r16/current_adjacent_ground.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('JOINT_GROUND_EXPORTED',len(rows),flush=True)
