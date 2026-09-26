"""Fresh r14 topology, normal continuity and actual attachment seating checks."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path

s = bpy.context.scene
assert s['version'] in ['G1_027r14','G1_027r15']
version = s['version']
cp = json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == cp['native_sha256']
source = json.loads(read_path('derived/bellevue/bank_tram_shelter/build_input.json').read_text())
ring = np.asarray(source['roof_plan_local']['coordinates'][0])
a, b = ring[:-1], ring[1:]
zmin, zmax = source['source_height_envelope_local']
rows = []
for sign, name in [(1, 'BST_CANOPY_ROOF_METAL'), (-1, 'BST_CANOPY_SOFFIT')]:
    ob = bpy.data.objects[name]
    me = ob.data
    verts = np.array([ob.matrix_world @ v.co for v in me.vertices])
    faces = np.array([list(p.vertices) for p in me.polygons])
    assert faces.shape[1] == 3 and len(faces) > 50000
    assert len(verts) == len(np.unique(verts, axis=0)), 'Coincident disconnected vertices remain'
    assert all(p.use_smooth for p in me.polygons) and me.has_custom_normals
    tri = verts[faces]
    cross = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    assert np.all(sign*cross[:, 2] > 0)
    area = float(np.abs(cross[:, 2]).sum()/2)
    assert abs(area-source['roof_plan_area_m2']) < .001
    assert verts[:, 2].min() >= zmin-1e-5 and verts[:, 2].max() <= zmax+1e-5
    max_edge = max(float(np.linalg.norm(tri[:, j]-tri[:, (j+1) % 3], axis=1).max()) for j in range(3))
    assert max_edge < .105
    edge_faces = {}
    for face in faces:
        for u, v in zip(face, np.roll(face, -1)):
            edge_faces.setdefault(tuple(sorted((int(u), int(v)))), 0)
            edge_faces[tuple(sorted((int(u), int(v))))] += 1
    assert max(edge_faces.values()) == 2
    assert len(verts)-len(edge_faces)+len(faces) == 1, 'Curved skin is not a connected disk'
    boundary_vertices = sorted({v for e, count in edge_faces.items() if count == 1 for v in e})
    xy = verts[boundary_vertices, :2]
    t = np.clip(((xy[:, None]-a) * (b-a)).sum(axis=2) / ((b-a)**2).sum(axis=1), 0, 1)
    gap = np.linalg.norm(xy[:, None]-(a+t[..., None]*(b-a)), axis=2).min(axis=1)
    assert float(gap.max()) < .00006, 'Roof outline changed'
    shared = {}
    mismatch = 0.
    for loop, normal in zip(me.loops, me.corner_normals):
        n = np.asarray(normal.vector)
        assert n[2]*sign > .8
        if loop.vertex_index in shared:
            mismatch = max(mismatch, float(np.linalg.norm(n-shared[loop.vertex_index])))
        else:
            shared[loop.vertex_index] = n
    assert mismatch < .0002, 'Normals still split across shared curved vertices'
    rows.append(dict(object=name, vertices=len(verts), faces=len(faces), plan_area_m2=area,
                     shared_edges=sum(c == 2 for c in edge_faces.values()),
                     boundary_vertices=len(boundary_vertices), max_boundary_deviation_m=float(gap.max()),
                     max_triangle_edge_m=max_edge, max_shared_normal_disagreement=mismatch))

soffit = bpy.data.objects['BST_CANOPY_SOFFIT']
tree = BVHTree.FromPolygons([soffit.matrix_world @ v.co for v in soffit.data.vertices],
                           [list(p.vertices) for p in soffit.data.polygons], all_triangles=True)
seatings = []
for name in ['BST_RECESSED_LIGHT_TRIM', 'BST_RECESSED_LIGHT_LENS']:
    ob = bpy.data.objects[name]
    gaps = []
    for v in ob.data.vertices:
        q = ob.matrix_world @ v.co
        p, _, _, _ = tree.ray_cast(Vector((q.x, q.y, 13.1)), Vector((0, 0, -1)), 1.5)
        assert p is not None
        gap = q.z-p.z
        assert -.018 < gap < .012
        if name.endswith('LENS'):
            assert gap < -.009, 'Light lens hidden inside curved concrete'
        gaps.append(gap)
    seatings.append(dict(object=name, actual_points=len(gaps), min_gap_m=min(gaps), max_gap_m=max(gaps)))

report = dict(version=s['version'], native_sha256=cp['native_sha256'], process_id=os.getpid(), passed=True,
              actual_curved_skins=rows, actual_light_seating=seatings,
              column_seating='Separately checked using actual 192 head points by bank shelter checks in this process.',
              visual_acceptance=False, natural_use_verified=False)
write_path(f'evidence/{version}/curvature_fresh_checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BANK_CURVATURE_CHECKED', json.dumps(dict(skins=len(rows), attachment_points=sum(r['actual_points'] for r in seatings))), flush=True)
