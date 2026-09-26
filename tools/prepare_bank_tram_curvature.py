"""Refine the existing inferred canopy section inside its surveyed outline.

The current native topology is the source, not a newly imagined roof. Reproject
midpoints onto the already documented continuous section and retain its plan.
"""
import hashlib
import json
import numpy as np
from workspace_paths import read_path, write_path


def section(xy, spec):
    xy = np.asarray(xy, dtype=float)
    start = np.array(spec['axis_start_local_xy'])
    axis = np.array(spec['axis_end_local_xy']) - start
    length = np.linalg.norm(axis)
    t = np.clip((xy-start) @ (axis/length) / length, 0., 1.)
    centre = start + t[..., None]*axis
    radii = [r['fitted_radius_m'] for r in spec['rounded_end_fits']]
    radius = radii[0]*(1-t) + radii[1]*t
    a = np.clip(np.linalg.norm(xy-centre, axis=-1)/radius, 0., 1.)
    a = a*a*(3-2*a)
    zmin, zmax = spec['source_height_envelope_local']
    return np.stack([zmax-.178+.178*a, zmin+.420*a], axis=-1)


def refined(vertices, faces, passes=3):
    # The saved r13 mesh contains exactly coincident but disconnected vertices.
    # A tiny bmesh merge distance did not actually weld most of them. Deduplicate
    # exact coordinates before refinement; do not rely on another tolerance weld.
    unique, inverse = np.unique(np.asarray(vertices, dtype=float), axis=0, return_inverse=True)
    points = list(unique)
    faces = inverse[np.asarray(faces, dtype=np.int32)]
    for _ in range(passes):
        mids, new = {}, []
        def midpoint(a, b):
            key = tuple(sorted((int(a), int(b))))
            if key not in mids:
                mids[key] = len(points)
                points.append((points[a]+points[b])/2)
            return mids[key]
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new.extend([(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)])
        faces = np.asarray(new, dtype=np.int32)
    return np.asarray(points), faces


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    probe_path = read_path('derived/bellevue/bank_tram_shelter/curvature_probe_r13.json')
    source_path = read_path('derived/bellevue/bank_tram_shelter/build_input.json')
    probe, spec = [json.loads(p.read_text()) for p in [probe_path, source_path]]
    assert probe['native_sha256'] == 'bb05ad245a399bde56939d9a6e18cddc5a8092aa36f1e4badda11452dbb7b8bb'
    target = write_path('derived/bellevue/bank_tram_shelter/curvature_repair_r14.json')
    bundle = write_path('derived/bellevue/bank_tram_shelter/curvature_repair_r14.npz')
    assert not target.exists() and not bundle.exists()
    arrays, reports = {}, []
    for index, name in enumerate(['BST_CANOPY_ROOF_METAL', 'BST_CANOPY_SOFFIT']):
        row = next(r for r in probe['objects'] if r['object'] == name)
        assert row['smooth_faces'] == row['digest']['polygons']
        assert row['nonmanifold_edges'] == 0 and not row['modifiers']
        old = np.asarray(row['vertices'])
        points, faces = refined(old, row['faces'])
        original_interpolation = points[:, 2].copy()
        points[:, 2] = section(points[:, :2], spec)[:, index]
        h = .0001
        grad = np.column_stack([(section(points[:, :2]+e*h, spec)[:, index] -
                                 section(points[:, :2]-e*h, spec)[:, index])/(2*h)
                                for e in np.eye(2)])
        normals = np.c_[-grad, np.ones(len(points))] * (1 if index == 0 else -1)
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        tri = points[faces]
        face_normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
        area = np.abs(face_normals[:, 2]).sum()/2
        assert abs(area-spec['roof_plan_area_m2']) < .001
        assert np.all(face_normals[:, 2] * (1 if index == 0 else -1) > 0)
        distinct_old = np.unique(old, axis=0)
        assert np.allclose(points[:len(distinct_old), :2], distinct_old[:, :2], atol=0, rtol=0)
        assert np.max(np.abs(section(old[:, :2], spec)[:, index]-old[:, 2])) < .0001
        delta = float(np.max(np.abs(points[:, 2]-original_interpolation)))
        # Actual r13 probe measured 75.795 mm of chord error at the rounded end.
        # This is within the documented 500 mm envelope and corrects sampling of
        # the existing analytic profile, not the surveyed layout or roof height.
        assert delta < .08
        arrays[f'v{index}'], arrays[f'f{index}'], arrays[f'n{index}'] = points, faces, normals
        reports.append(dict(object=name, original_digest=row['digest'], original_vertices=len(old),
                            exact_welded_original_vertices=len(distinct_old),
                            vertices=len(points), faces=len(faces), plan_area_m2=area,
                            max_original_triangle_interpolation_error_m=delta,
                            geometry_basis='Same inferred analytic section, official footprint/envelope fixed',
                            native_matrix=row['matrix_world']))
    np.savez_compressed(bundle, **arrays)
    out = dict(base_native_sha256=probe['native_sha256'], source_files=[
        dict(path=str(p), sha256=sha(p)) for p in [probe_path, source_path]],
        arrays_path=str(bundle), arrays_sha256=sha(bundle), parts=reports,
        subdivision_passes=3, exact_section=True, survey_layout_changed=False,
        visual_acceptance=False, ready_for_native_repair=True,
        limits=['Refinement of documented inferred section, not a new measurement.',
                'Column heads and light seats must be fitted to the actual refined native surface.',
                'Independent reopen, adjacent checks and matching views required.'])
    target.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    prepare()
