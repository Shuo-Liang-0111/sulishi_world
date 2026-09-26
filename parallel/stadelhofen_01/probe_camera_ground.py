"""Actual native ground near camera coordinates; no guessed extrapolation."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
from probe_boundary import mesh_bvh
tree,labels=mesh_bvh([o for o in bpy.data.objects if o.name.startswith('SF1_REF_CTX_')],False)
rows=[]
for name in ['SF1_QA_CONTEXT','SF1_QA_APPROACH']:
    ob=bpy.data.objects[name];q=Q(ob.location)
    for du,dv in [(0,0)]+[(u,v) for radius in [.10,.25,.50,1.0,1.5,2.] for u,v in [(radius,0),(-radius,0),(0,radius),(0,-radius)]]:
        u,v=q[0]+du,q[1]+dv;top=13.;hits=[]
        for k in range(12):
            h,n,i,_=tree.ray_cast(Vector(P(u,v,top)),Vector((0,0,-1)),top-7.)
            if h is None:break
            hits.append(dict(z=float(h.z),normal=list(n),object=labels[i]));top=h.z-.002
        rows.append(dict(camera=name,offset=[du,dv],uv=[float(u),float(v)],hits=hits))
write('evidence/v02/actual_camera_ground_probe.json',dict(process_id=os.getpid(),native=bpy.data.filepath,samples=rows))
for r in rows:
    if r['offset']==[0,0] or r['hits']:print(r,flush=True)
