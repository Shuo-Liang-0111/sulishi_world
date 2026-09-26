"""Independent current-main checks of the reviewed SF1 incremental assembly."""
from pathlib import Path
import hashlib
import json
import math
import os
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def bvh(objects, ground_filter=False):
    vertices, faces = [], []
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        if ob.type != 'MESH':
            continue
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        for tri in me.loop_triangles:
            points = [ev.matrix_world @ me.vertices[i].co for i in tri.vertices]
            n = (points[1] - points[0]).cross(points[2] - points[0])
            n.normalize()
            # A wall-foot scan ramp is not walking support. v05's apparently
            # supported plinth still met a roughly 27-degree scan artefact.
            # The 15-degree candidate cutoff is a scan-layer filter, not an
            # accessibility criterion. The rebuilt west interface is checked
            # separately against its much flatter ground and standing space.
            if ground_filter and (abs(n.z) < .965 or min(p.z for p in points) > 11.3 or max(p.z for p in points) < 9.8):
                continue
            base = len(vertices)
            vertices.extend(points)
            faces.append([base, base + 1, base + 2])
        ev.to_mesh_clear()
    assert faces, 'Selected boundary support is empty'
    return BVHTree.FromPolygons(vertices, faces, all_triangles=True)


s = bpy.context.scene
assert s['version'] == 'G1_027r11'
version = s['version']
cp = json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
assert sha(bpy.data.filepath) == cp['native_sha256']
r = json.loads(read_path(f'evidence/{version}/sf1_merge_report.json').read_text())
package = ROOT / 'parallel/stadelhofen_01'
assert sha(package / 'derived/build_input.json') == r['package_spec_sha256']
d = json.loads((package / 'derived/build_input.json').read_text())
tag = d['version'].split('_')[-1]
assert s['sf1_version'] == d['version'] == r['package_version']
assert sha(package / f'evidence/{tag}/actual_boundary_probe.json') == r['package_boundary_receipt_sha256']
for name, expected in r['author_states'].items():
    assert object_state(bpy.data.objects[name]) == expected, name
for name, expected in r['author_meshes'].items():
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[name].data))) == expected, name
for name, expected in r['old_cameras'].items():
    o = bpy.data.objects[name]
    assert dict(matrix=[list(v) for v in o.matrix_world], lens=o.data.lens, sensor_width=o.data.sensor_width) == expected
for name, expected in r['camera_states'].items():
    assert object_state(bpy.data.objects[name]) == expected
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects) == r['source_objects_unchanged'] == 2039
for row in r['import_report']['bounded_cuts']:
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['object']].data))) == row['after']
A, U, N = [np.asarray(d[k]) for k in ['A', 'U', 'N']]
def P(u, v, z): return Vector((*list(A + U * u + N * v), z))
author = bpy.data.collections[d['import_collection']]
ground_roles = {'walk_surface', 'walk_support', 'step_support', 'step_surface', 'plinth'}
ground = bvh([o for o in author.objects if o.get('sf1_role') in ground_roles or
              (o.get('sf1_role') == 'closed_interior' and 'FLOOR' in o.name)])
inventory = json.loads((package / 'derived/native_context_inventory.json').read_text())
photo_objects = [bpy.data.objects[row['original_name']] for row in inventory['objects']
                 if row['original_name'].startswith('CTX_')]
context = bvh(photo_objects, True)
reference = json.loads((package / f'evidence/{tag}/actual_boundary_probe.json').read_text())
seams = []
for sample in reference['samples']:
    inside, outside, middle = [np.asarray(sample[k]) for k in ['inside_uv', 'outside_uv', 'boundary_uv']]
    hit, normal, _, _ = ground.ray_cast(P(*inside, 12.0), Vector((0, 0, -1)), 2.25)
    outside_hits = []
    z = 11.3
    for _ in range(12):
        ph, pn, _, _ = context.ray_cast(P(*outside, z), Vector((0, 0, -1)), z - 9.75)
        if ph is None:
            break
        expected = d['ground_plane_coefficients'][0] + d['ground_plane_coefficients'][1] * outside[0] + d['ground_plane_coefficients'][2] * outside[1]
        threshold = next((e.get('minimum_normal_abs_z', .965) for e in d['ground_edge_profiles']
                          if e['edge'] == sample['edge']), .965)
        if abs(ph.z - expected) < .35 and abs(pn.z) >= threshold:
            outside_hits.append((ph, pn))
        z = ph.z - .002
        if z <= 9.75:
            break
    assert hit is not None and outside_hits, ('Missing current-main edge support', sample['edge'], middle.tolist())
    outside_hits.sort(key=lambda row: abs(row[0].z - expected))
    ph, pn = outside_hits[0]
    assert all(abs(q[0].z - ph.z) <= .03 for q in outside_hits), 'Ambiguous current-main ground layers'
    def to_edge(p, n, uv):
        delta = U * (middle[0] - uv[0]) + N * (middle[1] - uv[1])
        return float(p.z - np.dot(np.array(n)[:2], delta) / n.z)
    gap = to_edge(hit, normal, inside) - to_edge(ph, pn, outside)
    assert abs(gap) <= .020, (sample['edge'], gap)
    seams.append(dict(edge=sample['edge'], uv=middle.tolist(), current_main_gap_m=gap))
sys.path.insert(0, str(package))
from check_supports import check
contacts = check(author, ground, bvh)
assert contacts['passed'], contacts['errors']
from check_returns import check as check_returns
returns = check_returns(author, bvh)
assert returns['passed'], 'Side masonry return still has a ray-visible gap'
from check_foundations import check as check_foundations
foundations = check_foundations(author, bvh)
assert foundations['passed'], 'Cheek foundation is not supported by the actual ground bed'
from check_left_interface import wall_join_check
wall_corner = wall_join_check(author, bvh)
assert wall_corner['passed'], 'The visible v06 wall-foot/plinth corner opening remains'
assert d.get('left_interface_ground'), 'The v05 visible scan-ramp repair must be present'
floor_with_context = bvh([o for o in author.objects if o.get('sf1_role') in ground_roles] + photo_objects)
solid_with_context = bvh(list(author.objects) + photo_objects)
left_plane = d['left_interface_ground']['coefficients']
left_standing = []
for u in np.linspace(-3.44, -1.29, 23):
    for v in np.linspace(-.35, 1.46, 20):
        hit, normal, _, _ = floor_with_context.ray_cast(P(u, v, 11.35), Vector((0, 0, -1)), 1.2)
        expected = left_plane[0] + left_plane[1] * u + left_plane[2] * v
        assert hit is not None and normal.z >= .98 and abs(hit.z - expected) < .022, ('Left ground', u, v)
        obstruction, _, _, _ = solid_with_context.ray_cast(hit + Vector((0, 0, .075)), Vector((0, 0, 1)), 1.875)
        assert obstruction is None, ('Left standing band obstructed', u, v)
        left_standing.append(dict(uv=[float(u), float(v)], actual_z=float(hit.z),
                                  normal_z=float(normal.z), plane_delta_m=float(hit.z - expected)))
left_wall = bvh([bpy.data.objects['SF1_LEFT_WALL_FOOT_CONNECTION']])
raw_context = bvh(photo_objects)
bed = bvh([bpy.data.objects['SF1_APRON_CONTINUOUS_SUBBASE']])
left_wall_joins = []
for u in np.linspace(-3.49, -1.31, 45):
    origin, direction = P(u, -.30, 11.403), Vector((*(-N), 0))
    hit, _, _, _ = left_wall.ray_cast(origin, direction, 1.4)
    retained, _, _, _ = raw_context.ray_cast(origin, direction, 1.4)
    assert hit is not None and retained is not None, ('Left wall return missing', u)
    overlap = float(np.dot(np.asarray(hit)[:2] - np.asarray(retained)[:2], N))
    assert -.002 <= overlap < .022, ('Left wall return gap', u, overlap)
    bottom, _, _, _ = left_wall.ray_cast(P(u, -.80, 9.8), Vector((0, 0, 1)), 1.5)
    support, _, _, _ = bed.ray_cast(P(u, -.80, 11.3), Vector((0, 0, -1)), 1.5)
    assert bottom is not None and support is not None and bottom.z - support.z <= .004
    left_wall_joins.append(dict(u=float(u), author_minus_retained_v_m=overlap,
                               bottom_minus_bed_m=float(bottom.z - support.z)))
control = bpy.data.objects['SF1_DOOR_CENTRE_CONTROL']
assert not control.get('public_runtime_enabled', False)
door_states = []
for fraction in [0., .25, .5, .75, 1., 0.]:
    control['open_fraction'] = fraction
    control.update_tag()
    s.frame_set(s.frame_current)
    bpy.context.view_layer.update()
    angles = [bpy.data.objects['SF1_BAY2_' + label + '_PIVOT'].rotation_euler.z for label in ['LEFT', 'RIGHT']]
    assert all(abs(a - e) < 1e-5 for a, e in zip(angles, [-fraction * math.radians(95), fraction * math.radians(95)]))
    door_states.append(dict(fraction=fraction, actual_angles=angles))
assert sha(bpy.data.filepath) == cp['native_sha256']
result = dict(version=version, package_version=d['version'], process_id=os.getpid(),
              native_sha256=cp['native_sha256'], authored_meshes=len(r['author_meshes']),
              source_objects_preserved=2039, original_cameras_preserved=len(r['old_cameras']),
              independent_current_main_seams=seams, seam_max_m=max(abs(v['current_main_gap_m']) for v in seams),
              contacts_and_sweep=contacts, side_masonry_returns=returns,
              plinth_foundations=foundations, imported_driver_states=door_states, passed=True,
              current_main_west_standing=left_standing, current_main_west_wall_joins=left_wall_joins,
              current_main_west_corner=wall_corner,
              visual_acceptance=False, runtime_verified=False, natural_use_verified=False,
              limits=['Door movement is an editable local mechanism. The closed shallow recess is not a station concourse.',
                      'Construction support and bounded door separation do not establish full human or robot collision traversal.',
                      'The surrounding station, upper storeys and wings remain outside this increment.'])
write_path(f'evidence/{version}/sf1_fresh_checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('SF1_CURRENT_MAIN_CHECKED', json.dumps({k:result[k] for k in ['package_version', 'authored_meshes', 'seam_max_m', 'passed']}), flush=True)
