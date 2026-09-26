"""Read the current exported native expectation at the SF1/SF2 junction.

This diagnoses continuous building fabric and paving together. It does not
apply the rejected two-stone candidate, edit a native file or accept SF2.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from workspace_paths import read_path, write_path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


version = 'G1_027r15'
manifest_path = read_path(f'web/assets/{version}_current_r01/manifest.json')
manifest = json.loads(manifest_path.read_text())
assert manifest['status'] == 'geometry_candidate_exported_material_review_pending'
groups = [c for c in manifest['chunks'] if c['collection'] == 'SF1_AUTHOR_ENTRANCE']
assert len(groups) == 1
chunk = groups[0]
path = Path(chunk['expected_file'])
assert sha(path) == chunk['expected_sha256']
spec_path = read_path('parallel/stadelhofen_01/derived/build_input.json')
spec = json.loads(spec_path.read_text())
A, U, N = [np.asarray(spec[k], float) for k in ['A', 'U', 'N']]
surface_path = read_path('parallel/stadelhofen_02/derived/SF2_joint_interface_input_01/candidate_surface_definition.json')
candidate = json.loads(surface_path.read_text())
source = np.load(path, allow_pickle=False)


def local(world):
    out = world.copy()
    out[..., 0] = (world[..., :2] - A) @ U
    out[..., 1] = (world[..., :2] - A) @ N
    return out


triangles = {}
for row in chunk['geometry']:
    if not row['triangles']:
        continue
    key = row['key']
    matrix = source[key+'_matrix']
    xyz = source[key+'_positions'] @ matrix[:3, :3].T + matrix[:3, 3]
    triangles[row['name']] = local(xyz)[source[key+'_triangles']]


def intersections(tris, u, v):
    # Vertical line, every actual triangle hit; do not pick a high wall hit as
    # the pavement. Caller keeps the object identity and the full hit set.
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    x, y = b[:, :2]-a[:, :2], c[:, :2]-a[:, :2]
    rhs = np.array([u, v])-a[:, :2]
    det = x[:, 0]*y[:, 1]-x[:, 1]*y[:, 0]
    valid = abs(det) > 1e-12
    s = np.divide(rhs[:, 0]*y[:, 1]-rhs[:, 1]*y[:, 0], det, out=np.zeros(len(det)), where=valid)
    t = np.divide(x[:, 0]*rhs[:, 1]-x[:, 1]*rhs[:, 0], det, out=np.zeros(len(det)), where=valid)
    valid &= (s >= -1e-8) & (t >= -1e-8) & (s+t <= 1+1e-8)
    zz = a[:, 2]+s*(b[:, 2]-a[:, 2])+t*(c[:, 2]-a[:, 2])
    return sorted(set(round(float(z), 8) for z in zz[valid]))


return_names = [name for name in triangles if name.startswith(('SF1_WING_RETURN_', 'SF1_WING_CORNER_RETURN_')) and 'CAP' not in name]
return_bounds = []
projected = []
for name in return_names:
    tt = triangles[name]
    mask = (tt[:, :, 0].max(axis=1) > 12.3) & (tt[:, :, 0].min(axis=1) < 13.4)
    selected = tt[mask]
    if not len(selected):
        continue
    return_bounds.append({'object': name, 'min_uvz': selected.min(axis=(0, 1)).tolist(), 'max_uvz': selected.max(axis=(0, 1)).tolist()})
    for tri in selected:
        poly = Polygon(tri[:, :2])
        if poly.area > 1e-10:
            projected.append(poly)
return_plan = unary_union(projected)
assert not return_plan.is_empty

points = [(12.774, -.80), (12.79, -.80), (13.20, -.80), (13.20, -.71), (13.20, -.65),
          (13.20, -.50), (13.20, -.30), (13.20, -.10), (13.20, .20), (13.20, .43)]
probes = []
for u, v in points:
    hits = []
    for name, tt in triangles.items():
        if not name.startswith(('SF1_APRON_', 'SF1_CHEEK_', 'SF1_WING_')):
            continue
        values = intersections(tt, u, v)
        if values:
            hits.append({'object': name, 'vertical_hits_z': values})
    proposed = []
    for piece in candidate['support_surface_pieces']:
        if Polygon(piece['outline_uv']).buffer(1e-7).covers(Point(u, v)):
            proposed.append(float(np.dot(piece['plane_c_u_v'], [1, u, v])))
    probes.append({'u': u, 'v': v, 'within_existing_upper_wall_projection': bool(return_plan.covers(Point(u, v))),
                   'actual_native_intersections': hits, 'rejected_candidate_ground_z': proposed})

# Verify the worker's archived accepted geometry against the current native
# expectation, instead of silently assuming its old r11 diagnosis is current.
archive_path = read_path('parallel/stadelhofen_02/derived/frozen_sf1_evaluated_triangles.npz')
archive = np.load(archive_path, allow_pickle=False)
old_names = archive['object']
checks = []
for name in sorted(set(old_names.tolist())):
    old = archive['local'][old_names == name]
    assert name in triangles, ('Missing accepted SF1 object', name)
    current = triangles[name]
    assert old.shape == current.shape, ('Accepted SF1 topology differs', name)
    error = float(abs(old-current).max())
    # Archived mathutils world multiplication is float32; this expectation
    # stores float64 matrix multiplication of the original float32 vertices.
    assert error < .00002, ('Accepted SF1 positions differ', name, error)
    checks.append({'object': name, 'triangles': len(current), 'max_coordinate_difference_m': error})

report = {'version': version, 'native_sha256': manifest['native_sha256'],
          'expected_array_sha256': chunk['expected_sha256'], 'sf1_spec_sha256': sha(spec_path),
          'archived_sf1_triangles_sha256': sha(archive_path), 'rejected_candidate_sha256': sha(surface_path),
          'accepted_sf1_current_comparison': checks, 'right_return_actual_bounds': return_bounds, 'probes': probes,
          'diagnosis_scope': 'Current native expectation only. Wall projection does not by itself prove a ground-level closure.',
          'reference_actually_viewed': 'parallel/stadelhofen_01/sources/heritage_entrance_photo_1.jpg',
          'construction_hypothesis': 'Extend the already located return wall to a continuous foundation and terminate paving at its toe. Inspect actual low-level support, joints and exterior clearance before any native build.',
          'measured_lower_foundation': False, 'native_edited': False, 'sf2_accepted': False, 'ready_for_native_build': False}
output = write_path(f'derived/stadelhofen_joint/{version}/current_fabric_audit.json')
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'actual_sf1_objects_compared': len(checks), 'probes': len(probes), 'path': str(output), 'ready_for_native_build': False}))
