"""Attribute obstructions actually seen in the saved G1_020 eye-level renders."""
from pathlib import Path
import json
import numpy as np
import bpy
from mathutils import Vector

root = Path('F:/MyWorld/ZurichWorld')
scene = bpy.context.scene
assert scene['version'] == 'G1_020'
saved = (scene.render.resolution_x, scene.render.resolution_y)
cases = {
    'UR_QA_NORTH': [(650, 165), (680, 375), (545, 600), (1170, 350), (70, 425)],
    'UR_QA_STAFF': [(1180, 315), (35, 620)],
    'UR_QA_COUNTER': [(55, 480), (1200, 435)],
}
inventory = json.loads((root/'sources/features/bauminventar.geojson').read_text())['features']
rebuilt = {p['source']['id'] for p in json.loads((root/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text())['pits']}
records = []
try:
    scene.render.resolution_x, scene.render.resolution_y = 1280, 840
    for name, pixels in cases.items():
        camera = bpy.data.objects[name]
        frame = camera.data.view_frame(scene=scene)
        xmin, xmax = min(p.x/-p.z for p in frame), max(p.x/-p.z for p in frame)
        ymin, ymax = min(p.y/-p.z for p in frame), max(p.y/-p.z for p in frame)
        candidates = []
        for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
            corners = np.array([ob.matrix_world@Vector(p) for p in ob.bound_box])
            nearest = np.clip(np.asarray(camera.location), corners.min(0), corners.max(0))
            if np.linalg.norm(nearest-np.asarray(camera.location)) < 40:
                candidates.append((ob, ob.matrix_world.inverted()))
        for px, py in pixels:
            direction = camera.matrix_world.to_quaternion() @ Vector((xmin+(xmax-xmin)*px/1280, ymax-(ymax-ymin)*py/840, -1)).normalized()
            hits = []
            for ob, inverse in candidates:
                hit, point, normal, index = ob.ray_cast(inverse@camera.location, inverse.to_3x3()@direction)
                if not hit:
                    continue
                world = ob.matrix_world@point
                distance = (world-camera.location).length
                if distance > 35:
                    continue
                survey_xy = np.asarray(world[:2])+[2683775, 1246700]
                trees = sorted(inventory, key=lambda t:np.linalg.norm(np.asarray(t['geometry']['coordinates'])-survey_xy))[:3]
                hits.append({'object':ob.name, 'node':ob.get('source_node'), 'face':index,
                             'point_local':list(world), 'distance_m':distance,
                             'triangle_local':[list(ob.matrix_world@ob.data.vertices[i].co) for i in ob.data.polygons[index].vertices],
                             'nearby_trees':[{'id':t['id'], 'distance_xy_m':float(np.linalg.norm(np.asarray(t['geometry']['coordinates'])-survey_xy)), 'already_rebuilt':t['id'] in rebuilt} for t in trees]})
            hits.sort(key=lambda x:x['distance_m'])
            records.append({'camera':name, 'pixel':[px,py], 'hits':hits[:3]})
finally:
    scene.render.resolution_x, scene.render.resolution_y = saved
(root/'evidence/G1_020/kiosk_photo_residual_rays.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps([{'camera':r['camera'], 'pixel':r['pixel'], 'nearest':r['hits'][0] if r['hits'] else None} for r in records]))
