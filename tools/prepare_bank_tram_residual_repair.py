"""Prepare r13 only inside the actually rebuilt island waiting area.

The failed r12 images and a fresh native pixel/mesh probe determine this scope.
The original roof outline stays fixed; a distorted scan does not define it.
"""
import hashlib
import json
import numpy as np
from shapely import STRtree, constrained_delaunay_triangles, union_all
from shapely.geometry import shape, mapping, Polygon, Point, box
from convex_prism_clip import prism, subtract_many
from workspace_paths import read_path, write_path


def source(path):
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    root = 'derived/bellevue/bank_tram_shelter/'
    paths = [read_path(root+n) for n in ['build_input.json','platform_input.json','fixtures_input.json',
              'native_probe_G1_027r12_platform_full.json']]
    paths.append(read_path('evidence/G1_027r12/visible_scan_residual_probe.json'))
    spec,platform,fixtures,probe,pixels = [json.loads(p.read_text()) for p in paths]
    assert probe['version'] == 'G1_027r12' and not probe['native_changed']
    assert pixels['native_sha256'] == probe['native_sha256'] and not pixels['native_changed']
    A,U,N = [np.asarray(spec[k]) for k in ['axis_start_local_xy','axis_unit_xy','side_unit_xy']]
    island = shape(platform['geometry_local'])
    # The observed near fragments occupy u=-2.633..24.602. Keep the adjacent
    # northern light pole (u about -17) and the rest of the island untouched.
    along_range = [-4.,26.]
    band = Polygon([A+U*u+N*v for u,v in [(-4,-20),(26,-20),(26,20),(-4,20)]])
    mask = island.intersection(band)
    assert mask.is_valid and mask.geom_type == 'Polygon'
    assert mask.difference(island).area < 1e-8
    surfaces = []
    for ob in probe['objects']:
        if ob['name'] not in ['BST_PLATFORM_ASPHALT','BST_PLATFORM_CURB_TOP','BST_PLATFORM_CURB_JOINT']:continue
        for tri in np.asarray(ob['vertices_world'])[ob['faces']]:
            poly = Polygon(tri[:,:2])
            if poly.area > 1e-10:surfaces.append(poly)
    assert surfaces
    actual_cover = union_all(surfaces)
    unsupported_area = mask.difference(actual_cover).area
    assert unsupported_area < .002, ('Unbuilt support below proposed removal',unsupported_area)
    target_hits,protected_hits = [],[]
    for r in pixels['rays']:
        if not r['hit'] or not r['object'].startswith('CTX_'):continue
        q = Point(r['xyz'][:2])
        if mask.covers(q) and 8.0 <= r['xyz'][2] <= 12.7:
            target_hits.append(r)
        else:
            protected_hits.append(r)
    assert len(target_hits) >= 18 and protected_hits
    volumes = [prism(list(t.exterior.coords)[:3],8.0,12.70,'rebuilt_waiting_area')
               for t in constrained_delaunay_triangles(mask).geoms]
    index = STRtree([box(*v['bmin'][:2],*v['bmax'][:2]) for v in volumes])
    rows = []
    upper_crossings = []
    for ob in probe['objects']:
        if ob['kind'] != 'retained_photo':continue
        triangles = np.asarray(ob['vertices_world'])[ob['faces']]
        replacements = []
        for i,tri in enumerate(triangles):
            lo,hi = tri[:,:2].min(0),tri[:,:2].max(0)
            candidates = sorted(index.query(box(*(lo-1e-7),*(hi+1e-7))).tolist())
            if not candidates:continue
            # Do not sever an unidentified tall structure just to hide a scan.
            if tri[:,2].max()>13.0 and tri[:,2].min()<12.7:
                if mask.intersection(Polygon(tri[:,:2])).area > 1e-5:
                    upper_crossings.append(dict(object=ob['name'],face=i))
            unchanged,kept,area = subtract_many(tri,[volumes[j] for j in candidates])
            if not unchanged:
                replacements.append(dict(source_face=i,kept_barycentric_triangles=kept,removed_area_m2=area))
        if replacements:
            rows.append(dict(object=ob['name'],source_mesh_digest=ob['mesh_digest'],
                             source_matrix_world=ob['matrix_world'],source_faces=len(ob['faces']),
                             replacements=replacements,
                             removed_area_m2=sum(r['removed_area_m2'] for r in replacements)))
    assert not upper_crossings, ('Unresolved tall source structure crossing removal',upper_crossings)
    assert rows
    out = dict(base_native_sha256=probe['native_sha256'],sources=[source(p) for p in paths],
               rows=rows,mask_local=mapping(mask),mask_area_m2=mask.area,
               shelter_along_range_m=along_range,vertical_range_m=[8.0,12.70],
               actual_native_floor_coverage_gap_m2=unsupported_area,
               diagnosed_target_hits=target_hits,protected_hits=protected_hits,
               existing_author_facilities=[f['source_id'] for key in ['ads','benches'] for f in fixtures[key]]+
                 [fixtures['ticket']['source_id'],fixtures['ticket']['nearby_info']['source_id']],
               upper_source_structure_crossings=upper_crossings,
               basis='Current r12 render pixels and actual native scan triangles. Remove only unreliable scan over already rebuilt station waiting-area floor, bounded by the real concave island. All diagnosed near fragments fall inside; northern tall pole is outside. No roof, road, platform, facility or building position changes.',
               ready_for_native_repair=True,native_changed=False,visual_acceptance=False,natural_use_verified=False)
    path = write_path(root+'residual_repair_r13.json')
    assert not path.exists(), 'Preserve reviewed preparation instead of silently replacing it.'
    path.write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(file=str(path),area=mask.area,unsupported_area=unsupported_area,
                         changed_objects=len(rows),changed_faces=sum(len(r['replacements']) for r in rows),
                         target_pixels=len(target_hits),protected_pixels=len(protected_hits))),flush=True)


if __name__ == '__main__':main()
