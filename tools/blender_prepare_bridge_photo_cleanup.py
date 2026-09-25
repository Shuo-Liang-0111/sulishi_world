"""Bound a bridge-edge photo cleanup to three verified source components.

027r2 pixel rays and source meshes identify folded deck remnants. Every removed
face is recorded; the separate flags, lamps, water and source originals remain.
"""
import json
import sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path
from blender_geometry_fingerprint import mesh_digest

assert bpy.context.scene['version'] == 'G1_027r2'
vertices, faces, owners = [], [], []
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH' or not ob.name.startswith(('QB_DECK_', 'QB_BRIDGE_SLAB_', 'QB_GIRDER_')):
        continue
    start = len(vertices)
    vertices.extend(ob.matrix_world @ v.co for v in ob.data.vertices)
    faces.extend([[start+i for i in face.vertices] for face in ob.data.polygons])
    owners.extend([ob.name]*len(ob.data.polygons))
tree = BVHTree.FromPolygons(vertices, faces)
rows = []
for node in ['34256','34261','34383']:
    name = 'CTX_I3S_'+node
    ob = bpy.data.objects[name]
    exported = json.loads(read_path('derived/bridge_context/'+name+'.json').read_text())
    components = json.loads(read_path('derived/bridge_context/'+name+'_components.json').read_text())
    # Component 0 in each independently welded source tile is the folded deck
    # edge seen in QB_QA_SOUTH. All other components are explicitly out of scope.
    component = next(c for c in components if c['component']==0)
    ids = component['face_ids']
    assert len(ids) == {'34256':12,'34261':43,'34383':69}[node]
    distances = []
    for index in ids:
        poly = ob.data.polygons[index]
        world = [ob.matrix_world @ ob.data.vertices[i].co for i in poly.vertices]
        assert np.allclose(world, np.array(exported['vertices'])[exported['faces'][index]], atol=1e-5)
        for point in world + [sum(world,Vector())/len(world)]:
            near, normal, face, distance = tree.find_nearest(point)
            assert near is not None
            distances.append(dict(point=list(point),distance=float(distance),replacement=owners[face]))
    rows.append(dict(object=name, source_node=node, before_fingerprint=mesh_digest(ob.data),
        removed_faces=ids, bounds=[component['min'],component['max']],
        closest_authored_surface_max_m=max(p['distance'] for p in distances),
        closest_authored_surface_p95_m=float(np.quantile([p['distance'] for p in distances],.95)),
        distances=distances))
report = dict(base_version='G1_027r2',candidate_version='G1_027r3',
    basis='Source-component identification from same-native QB_QA_SOUTH rays; bounded folded bridge-deck remnants only. Existing AV/KUBA/photo-supported physical deck remains unchanged.',
    source_originals_preserved=True, flags_lamps_water_untouched=True, objects=rows)
write_path('derived/bridge_context/027r3_cleanup_input.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps([{k:r[k] for k in ['object','bounds','closest_authored_surface_max_m','closest_authored_surface_p95_m']} for r in rows]))
