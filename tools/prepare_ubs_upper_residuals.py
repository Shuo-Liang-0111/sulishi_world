"""Bound the diagnosed roof-scan remnants against saved, rebuilt bank geometry.

The halo contains a distorted scan, not an enlarged building. Only the front
eave belt is eligible; the rest of the roof and the neighbouring bank remain.
"""
import hashlib
import json
import numpy as np
from shapely import constrained_delaunay_triangles, union_all, STRtree
from shapely.geometry import Polygon, Point, box, mapping
from convex_prism_clip import prism, subtract_many
from workspace_paths import read_path, write_path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    root = 'derived/ubs_theaterstrasse20/'
    paths = [read_path(root+n) for n in ['build_input.json', 'r14_upper_residual_probe_with_eave.json']]
    spec, probe = [json.loads(p.read_text()) for p in paths]
    assert probe['version'] == 'G1_027r14' and not probe['native_changed']
    A, U, N = [np.asarray(spec[k]) for k in ['A', 'U', 'N']]
    polys = []
    for ob in probe['actual_rebuilt_upper_surfaces']:
        for tri in np.asarray(ob['evaluated_vertices_world'])[ob['evaluated_triangles']]:
            poly = Polygon(tri[:, :2])
            if poly.area > 1e-8:
                polys.append(poly)
    actual_roof = union_all(polys)
    # Native probe: front fragments extend to v=1.650; the real eave ends at
    # v=1.282. At the left corner the same collapsed triangle falls to z=26.917.
    # Cap the halo at the bank ends; don't sweep a buffer around other facades.
    uv_bounds = [-1.56, 21.72, -.10, 1.72]
    a, b, c, d = uv_bounds
    belt = Polygon([A+U*u+N*v for u, v in [(a,c),(b,c),(b,d),(a,d)]])
    mask = actual_roof.buffer(.40, join_style=2).intersection(belt)
    zmin, zmax = 26.84, 33.30
    assert mask.is_valid and mask.geom_type == 'Polygon' and mask.area < 43
    target, protected = [], []
    for row in probe['rays']:
        in_volume = mask.covers(Point(row['xyz'][:2])) and zmin <= row['xyz'][2] <= zmax
        if row['object'].startswith('CTX_') and in_volume:
            target.append(row)
        else:
            protected.append(row)
    assert len(target) == 4 and len(protected) == 6
    volumes = [prism(list(t.exterior.coords)[:3], zmin, zmax, 'bank_front_eave_scan')
               for t in constrained_delaunay_triangles(mask).geoms]
    index = STRtree([box(*v['bmin'][:2], *v['bmax'][:2]) for v in volumes])
    rows = []
    for ob in probe['diagnosed_current_photo_geometry']:
        changes = []
        for i, tri in enumerate(np.asarray(ob['vertices_world'])[ob['faces']]):
            lo, hi = tri.min(0), tri.max(0)
            if hi[2] < zmin or lo[2] > zmax:
                continue
            ids = sorted(index.query(box(*(lo[:2]-1e-7), *(hi[:2]+1e-7))).tolist())
            unchanged, kept, area = subtract_many(tri, [volumes[j] for j in ids])
            if not unchanged:
                changes.append(dict(source_face=i, kept_barycentric_triangles=kept, removed_area_m2=area))
        if changes:
            rows.append(dict(object=ob['object'], source_mesh_digest=ob['mesh_digest'],
                             source_matrix_world=ob['matrix_world'], source_faces=len(ob['faces']),
                             replacements=changes, removed_area_m2=sum(x['removed_area_m2'] for x in changes)))
    assert {r['object'] for r in rows} == {'CTX_I3S_33552','CTX_I3S_33436','CTX_I3S_33386'}
    output = dict(base_native_sha256=probe['native_sha256'],
                  sources=[dict(path=str(p), sha256=sha(p)) for p in paths],
                  actual_upper_objects=[dict(object=o['object'], mesh_digest=o['source_mesh_digest'])
                                        for o in probe['actual_rebuilt_upper_surfaces']],
                  actual_roof_projection=mapping(actual_roof), actual_roof_projection_area_m2=actual_roof.area,
                  mask_local=mapping(mask), mask_area_m2=mask.area,
                  inferred_scan_capture_halo_m=.40, vertical_range_m=[zmin,zmax], frame_uv_bounds=uv_bounds,
                  halo_outside_actual_roof_m2=mask.difference(actual_roof).area,
                  rows=rows, diagnosed_target_hits=target, protected_hits=protected,
                  basis='Saved r14 geometry and render rays. Bounded removal of scanned sheets overlapping the already rebuilt front eave, with a measured scan-displacement halo. Actual official roof, author eaves, facade, neighbouring building and all lower street elements are unchanged. Halo is inferred scan repair, not a physical building dimension.',
                  ready_for_native_repair=True, native_changed=False, visual_acceptance=False,
                  natural_use_verified=False)
    path = write_path(root+'upper_residual_repair_r15.json')
    assert not path.exists()
    path.write_text(json.dumps(output, separators=(',',':')), encoding='utf-8')
    print(json.dumps(dict(file=str(path), mask_area=mask.area, halo_area=output['halo_outside_actual_roof_m2'],
                          changed_objects=len(rows), changed_faces=sum(len(r['replacements']) for r in rows),
                          removed_triangle_area=sum(r['removed_area_m2'] for r in rows))), flush=True)


if __name__ == '__main__':
    main()
