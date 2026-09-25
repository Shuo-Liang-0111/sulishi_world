"""Identify photographed artifacts in the actual 027r2 review views.

Read-only, finite pixel samples; do not change visibility or the source meshes.
The receipt keeps face/position/source identity for bounded reconstruction.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import write_path


def connected_face_components(vertices, faces):
    """Deterministic diagnostic weld at 1 mm; does not modify source geometry."""
    import numpy as np
    vertices=np.asarray(vertices,dtype=float)
    faces=np.asarray(faces,dtype=int)
    unique,inverse=np.unique(np.round(vertices,3),axis=0,return_inverse=True)
    parent=list(range(len(unique)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    welded=inverse[faces]
    for face in welded:
        for a,b in zip(face,face[1:]):
            ra,rb=root(int(a)),root(int(b))
            parent[max(ra,rb)]=min(ra,rb)
    groups={}
    for i,face in enumerate(welded):groups.setdefault(root(int(face[0])),[]).append(i)
    rows=[]
    for component,key in enumerate(sorted(groups)):
        ids=groups[key];points=vertices[faces[ids].ravel()]
        rows.append(dict(component=component,faces=len(ids),face_ids=ids,
                         min=np.round(points.min(axis=0),3).tolist(),max=np.round(points.max(axis=0),3).tolist()))
    return rows

scene = bpy.context.scene
assert scene['version'] == 'G1_027r2'
width, height = 1280, 840
assert abs(scene.render.resolution_x / scene.render.resolution_y - width / height) < 1e-8
deps = bpy.context.evaluated_depsgraph_get()
rows = []
for camera_name, pixels in {
    'BD_QA_EAST': [(97,234),(148,362),(240,232),(297,316),(706,311),
                   (867,325),(901,51),(974,78),(1010,125),(520,352)],
    'QB_QA_SOUTH': [(384,249),(162,257),(639,260)],
}.items():
    camera = bpy.data.objects[camera_name]
    frame = camera.data.view_frame(scene=scene)
    x0, x1 = min(p.x for p in frame), max(p.x for p in frame)
    y0, y1 = min(p.y for p in frame), max(p.y for p in frame)
    for x, y in pixels:
        q = Vector((x0 + (x+.5)/width*(x1-x0), y1-(y+.5)/height*(y1-y0), frame[0].z))
        direction = (camera.matrix_world.to_3x3() @ q).normalized()
        start = camera.matrix_world.translation.copy()
        hits = []
        for _ in range(3):
            hit, point, normal, face, ob, matrix = scene.ray_cast(deps, start, direction, distance=210.)
            if not hit:
                break
            hits.append(dict(object=ob.name, face=face, local_point=list(point),
                source_node=ob.get('source_node'), source_id=ob.get('source_id'),
                hide_render=ob.hide_render, collections=[c.name for c in ob.users_collection],
                material=ob.data.materials[ob.data.polygons[face].material_index].name
                    if 0 <= face < len(ob.data.polygons) and ob.data.materials else None))
            start = point + direction*.002
        rows.append(dict(camera=camera_name,pixel=[x,y],hits=hits))
report=dict(version=scene['version'], native=bpy.data.filepath, native_mutated=False,
    image_size=[width,height], samples=rows)
write_path('evidence/G1_027r2/context_pixel_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for node in ['34256','34261','34383','37174']:
    ob=bpy.data.objects['CTX_I3S_'+node];mesh=ob.data;uv=mesh.uv_layers.active
    exported=dict(object=ob.name,source_node=node,
        vertices=[list(ob.matrix_world@v.co) for v in mesh.vertices],
        faces=[list(p.vertices) for p in mesh.polygons],
        uv_faces=[[list(uv.data[i].uv) for i in p.loop_indices] for p in mesh.polygons],
        materials=[m.name for m in mesh.materials])
    write_path('derived/bridge_context/'+ob.name+'.json').write_text(json.dumps(exported,separators=(',',':')),encoding='utf-8')
    components=connected_face_components(exported['vertices'],exported['faces'])
    write_path('derived/bridge_context/'+ob.name+'_components.json').write_text(json.dumps(components,indent=2),encoding='utf-8')
print(json.dumps(dict(version=scene['version'],sample_count=len(rows),exported_nodes=4,native_mutated=False)))
