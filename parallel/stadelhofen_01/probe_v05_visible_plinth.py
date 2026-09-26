"""Identify actual evaluated surfaces at the reviewed approach-image pixels.

This is a read-only diagnostic of v05. It does not render or save the native.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sf1_common import *

before = sha(bpy.data.filepath)
assert before == 'a51de6dd8332fb282222e8be328470a2f78862951cd08a9cd66351fd71ee9953'
scene = configure_render()
cam = bpy.data.objects['SF1_QA_APPROACH']
scene.camera = cam
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
frame = cam.data.view_frame(scene=scene)
xmin, xmax = min(v.x for v in frame), max(v.x for v in frame)
ymin, ymax = min(v.y for v in frame), max(v.y for v in frame)
pixels = [(187,644),(221,665),(255,684),(278,690),(308,688),
          (213,697),(238,692),(250,694),(250,698),(266,696),
          (279,699),(310,700),(210,703),(246,705),(290,710),
          (295,692),(296,696),(296,698),(296,700),(310,695)]
rows = []
for x, y in pixels:
    v = Vector((xmin + (x+.5)/1400*(xmax-xmin),
                ymax - (y+.5)/960*(ymax-ymin), frame[0].z))
    direction = (cam.matrix_world.to_3x3() @ v).normalized()
    hit, pos, normal, index, obj, matrix = scene.ray_cast(
        deps, cam.matrix_world.translation, direction, distance=100)
    rows.append(dict(pixel=[x,y], hit=hit, object=obj.name if hit else None,
        normal=list(normal) if hit else None,
        uvz=Q(pos).tolist() if hit else None, polygon=index if hit else None))
assert sha(bpy.data.filepath) == before
out = dict(version='SF1_v05', process_id=os.getpid(), native=bpy.data.filepath,
           native_sha256=before, saved=False, camera=cam.name,
           image_coordinates='1400x960, zero-based pixel, origin upper left',
           rays=rows)
write('evidence/v05/visible_plinth_pixel_probe.json', out)
for r in rows:
    print(r['pixel'], r['object'], r['normal'], r['uvz'])
