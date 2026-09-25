"""Prepare a continuous, locally inferred street/side-lane surface.

The retained street edge uses original scan ground where present. The occluded
lane uses the existing AV-bounded, photo-derived paving. Neither is a new survey.
The interior of the replacement is interpolated to the authored shop thresholds.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from workspace_paths import read_path, write_path

inputs = {name: read_path('derived/sternen_grill/' + name) for name in
          ['build_input.json', 'context_probe.json', 'r7_ground_probe.json']}
d = json.loads(inputs['build_input.json'].read_text())
context = json.loads(inputs['context_probe.json'].read_text())
probe = json.loads(inputs['r7_ground_probe.json'].read_text())
A, U, N = (np.array(d[k]) for k in ['A', 'U', 'N'])
W, D = d['width'], d['depth']


def local(points):
    points = np.asarray(points)
    return np.column_stack(((points[:, :2] - A) @ U,
                            (points[:, :2] - A) @ N, points[:, 2]))


def triangles(rows, photo):
    result, identities = [], []
    for row in rows:
        t = local(row['vertices'])[np.asarray(row['faces'])]
        normals = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        length = np.linalg.norm(normals, axis=1)
        valid = (length > 1e-8) & (abs(normals[:, 2]) > length * .9)
        valid &= (t[:, :, 2].min(1) > 8.20) & (t[:, :, 2].max(1) < 8.85)
        result.extend(t[valid]); identities.extend([row['name']] * int(valid.sum()))
    t = np.asarray(result)
    return t, t[:, :, :2].min(1), t[:, :, :2].max(1), identities


photo = triangles(context['rows'], True)
paving = triangles([r for r in probe['meshes'] if r['name'].startswith('BE_PAVING_')], False)


def hit(dataset, u, v):
    t, lower, upper, names = dataset
    xy = np.array([u, v])
    candidates = np.flatnonzero(((lower - 1e-7 <= xy) & (upper + 1e-7 >= xy)).all(1))
    hits = []
    for index in candidates:
        tri = t[index]
        matrix = np.column_stack((tri[1, :2] - tri[0, :2], tri[2, :2] - tri[0, :2]))
        a, b = np.linalg.solve(matrix, xy - tri[0, :2])
        if a >= -1e-6 and b >= -1e-6 and a + b <= 1.000001:
            z = tri[0, 2] + a * (tri[1, 2] - tri[0, 2]) + b * (tri[2, 2] - tri[0, 2])
            hits.append((float(z), names[index]))
    return sorted(hits)[len(hits) // 2] if hits else None


def boundary(u, v, lane=False):
    result = None if lane else hit(photo, u, v)
    basis = 'retained pre-cut photographic ground'
    sample_v = v
    extension = 0.
    if result is None:
        # The AV lane ends on an oblique boundary. A short, explicitly recorded
        # continuation of its measured slope joins the missing convex corner.
        sample_v = min(v, -.0002) if lane else v
        result = hit(paving, u, sample_v)
        if result is None and lane:
            for offset in np.arange(.05, 1.001, .05):
                sample_v = min(v, -.0002) - float(offset)
                result = hit(paving, u, sample_v)
                if result is not None:
                    break
        basis = 'existing AV-bounded, photo-derived paving'
    assert result is not None, ('unsupported outer edge', u, v, lane)
    z, name = result
    if lane and sample_v != v:
        previous = hit(paving, u, sample_v - .25)
        assert previous is not None
        slope = (z - previous[0]) / .25
        assert abs(slope) < .05
        extension = v - sample_v
        assert extension < 1.35
        z += extension * slope
    return dict(u=float(u), v=float(v), z=z, source=name, basis=basis,
                sampled_at_v=sample_v, extrapolation_length_m=extension)


inner = .345
umin, umax, vmax = -.045, W + 2.4, 4.4
us = sorted(set(np.linspace(umin, umax, 83).tolist() + [W + inner]))
vs = sorted(set(np.linspace(-D, inner, 84).tolist() + [0.]))
front_outer = [boundary(u, vmax) for u in us]
lane_outer = [boundary(umax, v, lane=True) for v in vs]
corner_z = lane_outer[-1]['z']
threshold = d['floor_z'] + .01
vertices, faces = [], []


def add_grid(xs, ys, height):
    start = len(vertices)
    for u in xs:
        for v in ys:
            vertices.append([float(u), float(v), float(height(u, v))])
    n = len(ys)
    for i in range(len(xs) - 1):
        for j in range(n - 1):
            a = start + i*n + j; b = a + n
            # The local plan frame is clockwise in world XY.
            faces.extend([[a, b+1, b], [a, a+1, b+1]])


front_z = {row['u']: row['z'] for row in front_outer}
lane_z = {row['v']: row['z'] for row in lane_outer}


def front_height(u, v):
    inner_z = threshold
    if u > W + inner:
        fraction = (u - W - inner) / (umax - W - inner)
        inner_z = threshold * (1 - fraction) + corner_z * fraction
    t = (v - inner) / (vmax - inner)
    return inner_z * (1 - t) + front_z[u] * t


def lane_height(u, v):
    t = (u - W - inner) / (umax - W - inner)
    return threshold * (1 - t) + lane_z[v] * t


add_grid(us, np.linspace(inner, vmax, 20), front_height)
add_grid([u for u in us if u >= W + inner], vs, lane_height)
verts = np.asarray(vertices)
world = np.column_stack((A + verts[:, :1]*U + verts[:, 1:2]*N, verts[:, 2]))
t = world[np.asarray(faces)]
normals = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
length = np.linalg.norm(normals, axis=1)
assert (length > 1e-9).all() and (normals[:, 2] > 0).all()
max_slope = float(np.degrees(np.arccos((normals[:, 2]/length).clip(-1, 1))).max())
assert max_slope < 6, max_slope
report = dict(version='G1_027r7', input_sha256={k: hashlib.sha256(p.read_bytes()).hexdigest() for k,p in inputs.items()},
              vertices=world.tolist(), faces=faces, local_vertices=vertices,
              front_outer=front_outer, lane_outer=lane_outer, threshold_z=threshold,
              bounds=dict(u=[umin,umax],front_v=[inner,vmax],lane_v=[-D,inner],lane_inner_u=W+inner),
              replacement_boxes=[[umin,umax,inner,vmax,8.0,8.89],[W+inner,umax,-D,inner,8.0,8.89]],
              max_surface_slope_degrees=max_slope,
              basis='Measured-position outer edges; interpolated approach to inferred8.580m shop thresholds. The covered lane uses existing paving, not new ground observations.',
              limits=['Left neighboring entrance and wider road remain separate future repairs',
                      'No claim of surveyed interior levels or completed runtime walking'])
target = write_path('derived/sternen_grill/r7_ground_input.json')
target.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'file':str(target),'vertices':len(vertices),'faces':len(faces),
                  'outer_ground_anchors':len(front_outer)+len(lane_outer),
                  'max_slope_degrees':max_slope},indent=2))
