"""Prepare exact per-face barycentric cuts from current r10/r11 working meshes.

No native or source texture is modified. Replaying requires exact current mesh
and evaluated transform fingerprints, so unrelated later edits cannot be lost.
"""
import hashlib
import json
import numpy as np
from shapely import STRtree, constrained_delaunay_triangles
from shapely.geometry import shape, box
from convex_prism_clip import prism, subtract_many
from workspace_paths import read_path, write_path


def main():
    paths = [read_path('derived/bellevue/bank_tram_shelter/' + n) for n in
             ['build_input.json', 'platform_input.json', 'fixtures_input.json', 'native_probe_G1_027r10_platform_full.json']]
    spec, platform, fixtures, probe = [json.loads(p.read_text()) for p in paths]
    assert platform['report']['ready_for_native_build'] and not probe['native_changed']
    volumes = []
    # The island is not convex: triangulate its actual outline, never use its
    # convex hull (which would incorrectly erase 119m2 of adjoining roadway).
    for geometry, z0, z1, role in [(platform['geometry_local'], 8.0, 8.98, 'ground_only'),
                                 (spec['roof_plan_local'], 8.0, 12.70, 'shelter')]:
        for tri in constrained_delaunay_triangles(shape(geometry)).geoms:
            volumes.append(prism(list(tri.exterior.coords)[:3], z0, z1, role))
    # Only the standalone bench lies outside the roof mask. The source point
    # and finite bench footprint, not a large visual-cleanup box, bound its cut.
    bench = next(b for b in fixtures['benches'] if b['source_id'].endswith('.328'))
    mask = shape(bench['footprint']).buffer(.10, join_style=2)
    for tri in constrained_delaunay_triangles(mask).geoms:
        volumes.append(prism(list(tri.exterior.coords)[:3], bench['floor_z']-.08,
                             bench['floor_z']+1.05, 'standalone_bench'))
    tree = STRtree([box(*v['bmin'][:2], *v['bmax'][:2]) for v in volumes])
    rows = []
    for ob in probe['objects']:
        if ob['kind'] != 'retained_photo': continue
        triangles = np.array(ob['vertices_world'])[ob['faces']]
        replacements = []
        for index, tri in enumerate(triangles):
            lo, hi = tri[:, :2].min(0), tri[:, :2].max(0)
            candidates = sorted(tree.query(box(*(lo-1e-7), *(hi+1e-7))).tolist())
            if not candidates: continue
            unchanged, kept, area = subtract_many(tri, [volumes[i] for i in candidates])
            if not unchanged:
                replacements.append(dict(source_face=index, kept_barycentric_triangles=kept, removed_area_m2=area))
        if replacements:
            rows.append(dict(object=ob['name'], source_mesh_digest=ob['mesh_digest'],
                             source_matrix_world=ob['matrix_world'], source_faces=len(ob['faces']),
                             replacements=replacements,
                             removed_area_m2=sum(r['removed_area_m2'] for r in replacements)))
        print(ob['name'], 'prepared changed faces', len(replacements), flush=True)
    out = dict(base_native_sha256=probe['native_sha256'], probe_version=probe['version'],
               rows=rows, preparation_inputs=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
               volume_count=len(volumes), roof_vertical_range=[8., 12.70],
               ground_vertical_range=[8., 8.98], ground_face_min_abs_normal_z=.965,
               masks_basis='Exact concave AV355/456/457 plan for low near-horizontal ground; exact roof plan for complete shelter; source-located standalone bench. Original sources and unrelated working geometry remain.',
               native_changed=False, visual_acceptance=False)
    target = write_path('derived/bellevue/bank_tram_shelter/photo_replacement.json')
    target.write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
    print(json.dumps(dict(file=str(target), objects=len(rows), changed_faces=sum(len(r['replacements']) for r in rows),
                          retained_triangles=sum(len(f['kept_barycentric_triangles']) for r in rows for f in r['replacements']),
                          bytes=target.stat().st_size)))


if __name__ == '__main__': main()
