"""Read-only current-scene frontage/ground probes for Theaterstrasse 20.

Keep all ray intersections: the highest scanned canopy/vehicle is not pavement.
Run only on the saved r8 scene, after other Blender processes have exited.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import runpy
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path, validate_native

scene = bpy.context.scene
assert scene['version'] == 'G1_027r8'
native = validate_native(bpy.data.filepath)
original_stat = native.stat()
with native.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
checkpoint = json.loads(read_path('evidence/G1_027r8/checkpoint.json').read_text())
assert checkpoint['native_sha256'] == digest
bpy.context.view_layer.update()

# The first review batch accidentally imported the door script as <run_path>.
# Its author checks and visible motion were real, but those did not establish a
# fresh-process numeric check. Execute the guarded main entry point explicitly.
runpy.run_path(str(Path(__file__).with_name('blender_check_sternen_doors.py')), run_name='__main__')
door = json.loads(read_path('evidence/G1_027r8/door_fresh_checks.json').read_text())
assert door['process_id'] == os.getpid() and door['native_sha256'] == digest

data = json.loads(read_path('derived/ubs_theaterstrasse20/site_constraints.json').read_text())
A, U, N = [np.array(data[key]) for key in ['A', 'U', 'N']]
W = data['street_width_m']


def P(u, v, z):
    return Vector((*list(A+U*u+N*v), z))


deps = bpy.context.evaluated_depsgraph_get()
probes = []
# The short return towards Sternen is sampled separately from the main road.
for side, samples in [('street', [(u, v) for u in np.linspace(.4, W-.4, 12)
                                  for v in [.25, .65, 1.15, 2.1, 3.5]]),
                      ('sternen_side', [(u, v) for u in [-.35, -.8, -1.5]
                                        for v in np.linspace(-15, -.7, 10)])]:
    for u, v in samples:
        start = P(u, v, 12.)
        intersections = []
        for _ in range(16):
            hit, point, normal, face, ob, matrix = scene.ray_cast(
                deps, start, Vector((0, 0, -1)), distance=max(.001, start.z-5.5))
            if not hit:
                break
            intersections.append(dict(object=ob.name, face=face, point=list(point),
                                      normal=list(normal), source_node=ob.get('source_node'),
                                      upward=bool(normal.z > .80)))
            start = point-Vector((0, 0, .002))
            if start.z < 5.5:
                break
        probes.append(dict(side=side, u=float(u), v=float(v), intersections=intersections))

# Persist all current photo geometry intersecting a bounded real footprint.
# This is an input for exact clipping, never a recommendation to delete blocks.
ring = np.array(data['footprint_local'])
lo, hi = ring.min(0)-4, ring.max(0)+4
objects = []
for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
    if ob.type != 'MESH' or not ob.data.polygons:
        continue
    world_corners = np.array([list(ob.matrix_world @ Vector(p)) for p in ob.bound_box])
    if np.any(world_corners[:, :2].max(0) < lo) or np.any(world_corners[:, :2].min(0) > hi):
        continue
    mesh = ob.data
    coordinates = np.empty(len(mesh.vertices)*3, dtype=np.float32)
    mesh.vertices.foreach_get('co', coordinates)
    coordinates = coordinates.reshape(-1, 3)
    matrix = np.array(ob.matrix_world)
    world = coordinates @ matrix[:3, :3].T+matrix[:3, 3]
    loops = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', loops)
    counts = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get('loop_total', counts)
    assert (counts == 3).all(), ob.name
    uv = np.empty(len(mesh.loops)*2, dtype=np.float32)
    assert mesh.uv_layers.active is not None, ob.name
    mesh.uv_layers.active.data.foreach_get('uv', uv)
    state_hash = hashlib.sha256(coordinates.tobytes()+loops.tobytes()+uv.tobytes()).hexdigest()
    objects.append(dict(name=ob.name, source_node=str(ob['source_node']),
                        vertex_loop_uv_sha256=state_hash, matrix_world=matrix.tolist(),
                        vertices_world=world.tolist(), triangles=loops.reshape(-1, 3).tolist(),
                        loop_uv=uv.reshape(-1, 2).tolist(), materials=[m.name if m else None for m in mesh.materials]))

assert native.stat().st_size == original_stat.st_size
assert native.stat().st_mtime_ns == original_stat.st_mtime_ns
report = dict(version=scene['version'], native=str(native), native_sha256=digest,
              checked_utc=datetime.now(timezone.utc).isoformat(), process_id=os.getpid(),
              local_frame={key: data[key] for key in ['A', 'U', 'N']},
              rays=probes, photo_objects=objects, floor_level_selected=False,
              whole_scene_unmodified=True, photo_removal_performed=False,
              fresh_door_check_same_process=True)
target = write_path('derived/ubs_theaterstrasse20/r8_geometry_probe.json')
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('UBS_FRONTAGE_PROBED', json.dumps(dict(file=str(target), rays=len(probes),
                                         photo_objects=len(objects), native_unmodified=True,
                                         fresh_door_check=True)), flush=True)

if '--render-threshold' in sys.argv:
    # A required ground-level close view; the earlier entry/corner framing cuts
    # off the new threshold. Reuse all geometry and the exact saved camera.
    scene.cycles.device = 'CPU'
    scene.cycles.use_denoising = True
    if hasattr(scene.cycles, 'denoising_use_gpu'):
        scene.cycles.denoising_use_gpu = False
    from blender_render_memory import prepare_review_memory
    prepare_review_memory('SG_QA_THRESHOLD')
    runpy.run_path(str(Path(__file__).with_name('blender_render_bellevue.py')),
                  init_globals={'REVIEW_CAMERA': 'SG_QA_THRESHOLD', 'REVIEW_DEVICE': 'CPU',
                                'REVIEW_SAMPLES': 24, 'REVIEW_RESOLUTION': (1280, 840)})
    assert native.stat().st_size == original_stat.st_size
    assert native.stat().st_mtime_ns == original_stat.st_mtime_ns
    print('STERNEN_THRESHOLD_REVIEW_COMPLETE', flush=True)
