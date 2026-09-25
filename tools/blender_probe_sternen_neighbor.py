"""Locate the remaining visible neighbor/foreground scan before replacement."""
from pathlib import Path
import ast,json,sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

s=bpy.context.scene;assert s['version']=='G1_027r8'
deps=bpy.context.evaluated_depsgraph_get();camera=bpy.data.objects['SG_QA_CORNER']
frame=camera.data.view_frame(scene=s)
x0,x1=min(p.x for p in frame),max(p.x for p in frame)
y0,y1=min(p.y for p in frame),max(p.y for p in frame)
pixels=[]
for x,y in [(958,808),(1147,793),(1114,498),(738,803),(1000,260),(1150,360)]:
    q=Vector((x0+(x+.5)/1280*(x1-x0),y1-(y+.5)/840*(y1-y0),frame[0].z))
    direction=(camera.matrix_world.to_3x3()@q).normalized()
    hit,p,n,face,ob,m=s.ray_cast(deps,camera.matrix_world.translation,direction,distance=150)
    pixels.append(dict(pixel=[x,y],object=ob.name if hit else None,face=face if hit else None,
                       point=list(p) if hit else None,normal=list(n) if hit else None))
tree=ast.parse(read_path('tools/blender_probe_bridge_context.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='connected_face_components')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'components_only','exec'),ns)
objects=[]
for name in sorted({p['object'] for p in pixels if p['object'] and p['object'].startswith('CTX_I3S_')}):
    ob=bpy.data.objects[name];vertices=[list(ob.matrix_world@v.co) for v in ob.data.vertices]
    faces=[list(p.vertices) for p in ob.data.polygons]
    objects.append(dict(object=name,source_node=str(ob['source_node']),mesh_digest=mesh_digest(ob.data),
        vertices=vertices,faces=faces,components=ns['connected_face_components'](vertices,faces)))
report=dict(version=s['version'],camera=camera.name,pixels=pixels,objects=objects,
            scene_modified=False,interpretation='Pixel identity only; not permission to remove a building, vehicle or awning.')
write_path('derived/sternen_neighbor/r8_pixel_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STERNEN_NEIGHBOR_PROBE',json.dumps(dict(pixels=pixels,objects=[o['object'] for o in objects])),flush=True)
