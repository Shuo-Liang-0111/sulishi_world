"""Read-only pixel rays through the exact bridge review camera.

Records the front layers rather than guessing whether a dark patch is source
photography, an authored face, or an overlap. Does not hide or modify objects.
"""
from pathlib import Path
import json
import bpy
from mathutils import Vector

R = Path('F:/MyWorld/ZurichWorld')
s = bpy.context.scene
assert s['version'] == 'G1_027r1'
assert Path(bpy.data.filepath).name == 'G1_027r1_bridgehead_grade_working.blend'
camera = bpy.data.objects['BD_QA_JUNCTION']
width, height = 1280, 840
assert abs(s.render.resolution_x / s.render.resolution_y - width / height) < 1e-8
frame = camera.data.view_frame(scene=s)
x0, x1 = min(p.x for p in frame), max(p.x for p in frame)
y0, y1 = min(p.y for p in frame), max(p.y for p in frame)
z = frame[0].z
deps = bpy.context.evaluated_depsgraph_get()
pixels = [(130,218),(175,214),(225,212),(175,220),(175,226),
          (300,225),(400,240),(465,221),(500,229),(525,224),
          (540,239),(485,251),(490,273),(560,500),(700,500),(200,500)]
rows = []
for x, y in pixels:
    q = Vector((x0+(x+.5)/width*(x1-x0), y1-(y+.5)/height*(y1-y0), z))
    direction = (camera.matrix_world.to_3x3() @ q).normalized()
    origin = camera.matrix_world.translation.copy()
    hits = []
    for _ in range(4):
        ok, point, normal, face, ob, matrix = s.ray_cast(deps, origin, direction, distance=180.)
        if not ok:
            break
        item = dict(object=ob.name,face=face,point=list(point),normal=list(normal),
                    source_node=ob.get('source_node'),source_id=ob.get('source_id'),
                    role=ob.get('surface_role'),distance=(point-camera.location).length)
        if 0 <= face < len(ob.data.polygons):
            poly = ob.data.polygons[face]
            item['material_index'] = poly.material_index
            item['face_vertices'] = [list(matrix @ ob.data.vertices[i].co) for i in poly.vertices]
        hits.append(item)
        origin = point + direction*.0005
    rows.append(dict(pixel=[x,y],hits=hits))
out = R/'evidence/G1_027r1/junction_pixel_rays.json'
out.write_text(json.dumps(dict(version=s['version'],camera=camera.name,
    image_size=[width,height],native_mutated=False,samples=rows),indent=2),encoding='utf-8')
print(json.dumps([dict(pixel=r['pixel'],hits=[(h['object'],h['face'],h['point']) for h in r['hits']]) for r in rows]))
