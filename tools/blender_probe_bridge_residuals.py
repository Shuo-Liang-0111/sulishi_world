"""Read-only probe of actual residual sheets, using pixels inside their silhouettes.

Earlier sample (348,590) fell outside the large sheet and hit a distant facade.
Retain that record, but do not use it as the sheet's identity.
"""
from pathlib import Path
import json, sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import write_path
from blender_geometry_fingerprint import mesh_digest

s = bpy.context.scene
assert s['version'] == 'G1_027r4'
deps = bpy.context.evaluated_depsgraph_get()
camera = bpy.data.objects['BF_QA_FLAGS']
frame = camera.data.view_frame(scene=s)
x0,x1 = min(p.x for p in frame),max(p.x for p in frame)
y0,y1 = min(p.y for p in frame),max(p.y for p in frame)
samples=[]
for x,y in [(335,650),(401,690),(421,581),(539,603),(680,741)]:
    q=Vector((x0+(x+.5)/1280*(x1-x0),y1-(y+.5)/840*(y1-y0),frame[0].z))
    direction=(camera.matrix_world.to_3x3()@q).normalized()
    hit,p,n,face,ob,m=s.ray_cast(deps,camera.matrix_world.translation,direction,distance=220)
    assert hit
    samples.append(dict(pixel=[x,y],object=ob.name,face=face,point=list(p)))
rows=[]
for node in ['34256','34216','34261','37174']:
    ob=bpy.data.objects['CTX_I3S_'+node];me=ob.data;uv=me.uv_layers.active
    rows.append(dict(name=ob.name,mesh_digest=mesh_digest(me),
        vertices=[list(ob.matrix_world@v.co) for v in me.vertices],
        faces=[list(p.vertices) for p in me.polygons],
        uv_faces=[[list(uv.data[i].uv) for i in p.loop_indices] for p in me.polygons],
        image_paths=[bpy.path.abspath(n.image.filepath,library=n.image.library)
            for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes
            if n.type=='TEX_IMAGE' and n.image], properties=dict(ob.items())))
report=dict(version=s['version'],native=bpy.data.filepath,samples=samples,context=rows,
    scene_modified=False, earlier_pixel_correction='BF_QA_FLAGS (348,590) is outside the sheet silhouette; its distant facade hit does not locate the sheet.')
write_path('derived/bridge_residuals/source_probe.json').write_text(json.dumps(report),encoding='utf-8')
print(json.dumps(dict(samples=samples,objects=[(r['name'],len(r['faces'])) for r in rows])))
