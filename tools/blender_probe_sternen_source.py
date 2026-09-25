"""Read current photo/ground evidence around the official Theaterstrasse22 shell.

Run on the saved 027r4 base before reconstruction. No scene mutations.
"""
from pathlib import Path
import json,sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import write_path
s=bpy.context.scene;assert s['version']=='G1_027r4'
d=bpy.context.evaluated_depsgraph_get();ground=[]
for xy in [(-174,160),(-170,155),(-164.8,151.1),(-168,160),(-171,163),(-154,154),(-149,159)]:
    start=Vector((*xy,11));hits=[]
    for _ in range(4):
        hit,p,n,face,ob,m=s.ray_cast(d,start,Vector((0,0,-1)),distance=10)
        if not hit:break
        hits.append(dict(z=p.z,object=ob.name,face=face));start=p-Vector((0,0,.002))
    ground.append(dict(xy=xy,hits=hits))
rows=[]
for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
    if ob.type!='MESH' or not ob.data.polygons:continue
    corners=[ob.matrix_world@Vector(p) for p in ob.bound_box]
    lo=[min(p[i] for p in corners) for i in range(3)];hi=[max(p[i] for p in corners) for i in range(3)]
    if hi[0]<-175 or lo[0]>-146 or hi[1]<149 or lo[1]>176:continue
    me=ob.data;uv=me.uv_layers.active
    rows.append(dict(name=ob.name,vertices=[list(ob.matrix_world@v.co) for v in me.vertices],
        faces=[list(p.vertices) for p in me.polygons],
        uv_faces=[[list(uv.data[i].uv) for i in p.loop_indices] for p in me.polygons],
        image_paths=[bpy.path.abspath(n.image.filepath,library=n.image.library)
            for mat in me.materials if mat and mat.use_nodes for n in mat.node_tree.nodes
            if n.type=='TEX_IMAGE' and n.image]))
write_path('derived/sternen_grill/context_probe.json').write_text(json.dumps(dict(version=s['version'],rows=rows,ground_samples=ground)))
print('STERNEN_SOURCE_PROBE',len(rows),'scene unmodified')
