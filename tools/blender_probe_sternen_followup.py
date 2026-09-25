"""Probe visible remaining fragments and the ground just outside the new facade.

Read-only on027r5 after its multi-view review. Keep samples even if they hit a
legitimate object; a pixel hit is not authorization to remove that object.
"""
from pathlib import Path
import ast,json,sys
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest
s=bpy.context.scene;assert s['version']=='G1_027r5'
d=json.loads(read_path('derived/sternen_grill/build_input.json').read_text())
deps=bpy.context.evaluated_depsgraph_get();pixels=[]
for cam_name,points in {'BF_QA_FLAGS':[(282,609),(300,636)],
                       'SG_QA_FRONT':[(885,602),(850,670)],
                       'SG_QA_CORNER':[(636,680),(565,658),(737,804)]}.items():
    camera=bpy.data.objects[cam_name];frame=camera.data.view_frame(scene=s)
    x0,x1=min(p.x for p in frame),max(p.x for p in frame);y0,y1=min(p.y for p in frame),max(p.y for p in frame)
    for x,y in points:
        q=Vector((x0+(x+.5)/1280*(x1-x0),y1-(y+.5)/840*(y1-y0),frame[0].z))
        direction=(camera.matrix_world.to_3x3()@q).normalized()
        hit,p,n,face,ob,m=s.ray_cast(deps,camera.matrix_world.translation,direction,distance=230)
        pixels.append(dict(camera=cam_name,pixel=[x,y],object=ob.name if hit else None,
            face=face if hit else None,point=list(p) if hit else None))
A=np.array(d['A']);U=np.array(d['U']);N=np.array(d['N']);ground=[]
for u in np.linspace(.8,d['width']-.8,8):
    for v in [.5,1.0,1.6,2.2]:
        xy=A+U*u+N*v
        hit,p,n,face,ob,m=s.ray_cast(deps,Vector((*xy,9.3)),Vector((0,0,-1)),distance=2)
        ground.append(dict(u=float(u),v=v,xy=xy.tolist(),object=ob.name if hit else None,
            height=float(p.z) if hit else None,normal=list(n) if hit else None))
report=dict(version=s['version'],pixels=pixels,ground=ground,
    note='Finite ground samples check for accidental removal near the new threshold. They are not a complete walk/collision test.',scene_modified=False)
write_path('evidence/G1_027r5/followup_probe.json').write_text(json.dumps(report,indent=2))
# Isolate the pure topology helper. Importing its original executable module
# would run a different-version probe as a side effect.
tree=ast.parse(read_path('tools/blender_probe_bridge_context.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='connected_face_components')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'components_only','exec'),ns)
ob=bpy.data.objects['CTX_I3S_34267']
verts=[list(ob.matrix_world@v.co) for v in ob.data.vertices]
faces=[list(f.vertices) for f in ob.data.polygons]
write_path('derived/sternen_grill/remaining_bridge_fragment.json').write_text(json.dumps(dict(
    object=ob.name,vertices=verts,faces=faces,mesh_digest=mesh_digest(ob.data),
    components=ns['connected_face_components'](verts,faces))))
print('STERNEN_FOLLOWUP',json.dumps(dict(pixels=pixels,ground_missing=[r for r in ground if r['height'] is None])),flush=True)
