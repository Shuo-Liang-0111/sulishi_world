"""Prepare a continuous AV355 pavement with photo-supported longitudinal grade.

Source photography is curved along this long platform; flattening it to a
single plane produces a 10 cm RMS mismatch. Fit a smooth, slope-constrained
profile, then connect only the real end junctions to the existing road model.
This candidate still needs current-native boundary and visual validation.
"""
from functools import lru_cache
import hashlib
import json
import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import minimize, LinearConstraint
from shapely import STRtree, constrained_delaunay_triangles
from shapely.geometry import Polygon, Point, shape, box, mapping
from shapely.geometry.polygon import orient
from shapely.ops import nearest_points, unary_union
from shapely.affinity import translate
from workspace_paths import read_path, write_path


class Road:
    def __init__(self, triangles):
        self.triangles = np.asarray(triangles)
        self.polygons = [Polygon(t[:, :2]) for t in self.triangles]
        self.tree = STRtree(self.polygons)

    def sample(self, xy):
        p = Point(xy)
        i = int(self.tree.nearest(p))
        q = np.asarray(nearest_points(self.polygons[i], p)[0].coords[0])
        t = self.triangles[i]
        w = np.linalg.solve((t[1:, :2] - t[0, :2]).T, q - t[0, :2])
        return float(t[0, 2] + w @ (t[1:, 2] - t[0, 2])), float(p.distance(self.polygons[i]))


def main():
    names = ['derived/bellevue/bank_tram_shelter/build_input.json',
             'derived/bellevue/bank_tram_shelter/complete_ground_support.json',
             'derived/bellevue/bank_tram_shelter/platform_diagnosis_G1_027r10.json',
             'derived/bellevue/transport/road_input.json',
             'sources/features/av_bo_boflaeche_a.geojson',
             'derived/bellevue/bank_tram_shelter/current_road_support.json']
    paths = [read_path(p) for p in names]
    spec, support, diagnosis, road_data, av_data, current = [json.loads(p.read_text()) for p in paths]
    assert current['version'] == 'G1_027r10' and not current['native_changed']
    assert current['current_minus_recipe_max_m'] < .0001
    platform = orient(shape(spec['land_use_beneath'][0]['geometry_local']), 1)
    assert abs(platform.area - 266.07922232276326) < 1e-7
    # Two real end noses share AV355's boundary. They are not road and must
    # not receive a curb down the middle of this continuous pedestrian island.
    end_ids = {'av_bo_boflaeche_a.456', 'av_bo_boflaeche_a.457'}
    ends = [dict(id=f['id'], geometry_local=mapping(translate(shape(f['geometry']),
                 -spec['origin_lv95_ln02'][0], -spec['origin_lv95_ln02'][1])))
            for f in av_data['features'] if f['id'] in end_ids]
    assert len(ends) == 2
    poly = orient(unary_union([platform, *[shape(f['geometry_local']) for f in ends]]), 1)
    assert poly.geom_type == 'Polygon' and poly.is_valid and not poly.interiors
    assert abs(poly.area - 285.91008671390495) < 1e-6
    # Both real end noses need their own ground evidence. Extending a spline
    # fitted only on AV355 can turn an unconstrained end into a false dip.
    assert set(support['included_end_ids']) == end_ids
    assert shape(support['geometry_local']).equals(poly)
    inner = poly.buffer(-.22)
    start = np.asarray(spec['axis_start_local_xy'])
    along, across = np.asarray(spec['axis_unit_xy']), np.asarray(spec['side_unit_xy'])
    basis = np.stack([along, across]).T
    points, areas = [], []
    for row in support['original_candidate_faces']:
        t = np.asarray(row['triangle'])
        inter = inner.intersection(Polygon(t[:, :2]))
        if inter.area < .005:
            continue
        p = np.asarray(inter.centroid.coords[0])
        w = np.linalg.solve((t[1:, :2] - t[0, :2]).T, p - t[0, :2])
        points.append([*((p - start) @ basis), float(t[0, 2] + w @ (t[1:, 2] - t[0, 2]))])
        areas.append(inter.area)
    points, areas = np.asarray(points), np.asarray(areas)
    ring_uv = (np.asarray(poly.exterior.coords) - start) @ basis
    lo = np.floor(min(points[:, 0].min(), ring_uv[:, 0].min()) / 5) * 5 - 1
    hi = np.ceil(max(points[:, 0].max(), ring_uv[:, 0].max()) / 5) * 5 + 1
    knots = np.r_[[lo] * 4, np.arange(lo + 5, hi, 5), [hi] * 4]
    count = len(knots) - 4
    splines = BSpline(knots, np.eye(count), 3)
    X = np.c_[splines(points[:, 0]), points[:, 1]]
    road = Road(current['current_road_triangles'])
    ring = poly.exterior
    edge_stations = sorted({0., ring.length, *np.arange(0, ring.length, .35),
                            *[ring.project(Point(p)) for p in ring.coords]})
    edge_xy = np.array([ring.interpolate(t).coords[0] for t in edge_stations])
    edge_uv = (edge_xy-start) @ basis
    edge_design = np.c_[splines(edge_uv[:, 0]), edge_uv[:, 1]]
    edge_road = np.array([road.sample(p)[0] for p in edge_xy])
    # Relative construction constraint, not a measured curb height: a new
    # pedestrian island must not dip below the retained road. The 7mm margin
    # allows the later smooth crossing join, whose actual threshold is +4mm.
    # This adjusts the inferred fit, not the real footprint or old road mesh.
    edge_minimum = edge_road + .007
    curvature = np.c_[np.diff(np.eye(count), n=2, axis=0), np.zeros(count - 2)]
    # The derivative of a cubic B-spline is a convex combination of these
    # control differences; bounding all of them bounds the whole profile.
    derivative = np.zeros((count - 1, count + 1))
    for i in range(count - 1):
        k = 3 / (knots[i + 4] - knots[i + 1])
        derivative[i, i:i + 2] = [-k, k]
    parameters = np.r_[np.full(count, 8.5), 0.]
    for _ in range(8):
        residual = points[:, 2] - X @ parameters
        w = np.sqrt(np.minimum(areas, 2) * np.minimum(1, .025 / np.maximum(abs(residual), 1e-9)))
        design = np.vstack([X * w[:, None], curvature * 1.5])
        target = np.r_[points[:, 2] * w, np.zeros(count - 2)]
        q = design.T @ target
        Q = design.T @ design
        result = minimize(lambda p: .5 * p @ Q @ p - q @ p, parameters,
                          jac=lambda p: Q @ p - q, method='SLSQP',
                          bounds=[(8.15, 8.85)] * count + [(-.02, .02)],
                          constraints=[LinearConstraint(derivative, -.035, .035),
                                       LinearConstraint(edge_design, edge_minimum, np.inf)],
                          options={'ftol': 1e-12, 'maxiter': 1000})
        assert result.success, result.message
        parameters = result.x
    residual = points[:, 2] - X @ parameters
    ramps, excluded = [], []
    for row in diagnosis['official_walking_intersections']:
        if row['source_id'] == 'tbl_routennetz.3806':
            excluded.append(dict(source_id=row['source_id'], xy=row['xy'],
                                 reason='A general along-platform route cuts the curved edge twice; these are not evidence for mid-platform curb ramps.'))
            continue
        # Five end-junction contacts, fixed at actual route/AV boundary hits.
        threshold = []
        for offset in np.linspace(-1.2, 1.2, 17):
            new_station = ring.project(Point(row['xy']))
            assert ring.distance(Point(row['xy'])) < .006
            xy = np.asarray(ring.interpolate((new_station + offset) % ring.length).coords[0])
            z, distance = road.sample(xy)
            assert distance < .006, (row['source_id'], distance)
            threshold.append([*xy, z + .004])
        ramps.append(dict(source_id=row['source_id'], center_xy=row['xy'],
                          inferred_width_m=2.4, inferred_grade=.035, threshold=threshold))
    segments = np.asarray([pair for r in ramps for pair in zip(r['threshold'][:-1], r['threshold'][1:])])
    sa, sv = segments[:, 0], segments[:, 1] - segments[:, 0]
    length2 = (sv[:, :2] ** 2).sum(1)

    @lru_cache(maxsize=100000)
    def floor(x, y):
        p = np.array([x, y])
        u, v = (p - start) @ basis
        z = float(splines(u) @ parameters[:count] + v * parameters[-1])
        fraction = np.clip(((p - sa[:, :2]) * sv[:, :2]).sum(1) / length2, 0, 1)
        nearest = sa + sv * fraction[:, None]
        distance = np.linalg.norm(p - nearest[:, :2], axis=1)
        upper = float(np.min(nearest[:, 2] + .035 * distance))
        lower = float(np.max(nearest[:, 2] - .035 * distance))
        # Both bounds meet the threshold at each real end junction. Elsewhere
        # the profile keeps the photo-supported curb; no blanket road offset.
        def soft_min(a, b, radius=.006):
            h = max(radius - abs(a - b), 0.) / radius
            return min(a, b) - h * h * radius * .25
        # A short smooth join avoids a grade kink turning into a steep tiny
        # triangle where the AV outline almost coincides with a grid line.
        # It shifts a threshold by at most 1.5mm, checked below independently.
        return soft_min(-soft_min(-z, -lower), upper)

    band = poly.difference(poly.buffer(-.20, join_style=2))
    masks = {'asphalt': poly.difference(band), 'curb_top': band}
    parts = {k: [] for k in masks}
    parts.update(curb_face=[], curb_joint=[])
    x0, y0, x1, y1 = poly.bounds
    for x in np.arange(np.floor(x0 * 2) / 2, x1, .5):
        for y in np.arange(np.floor(y0 * 2) / 2, y1, .5):
            for name, mask in masks.items():
                inter = mask.intersection(box(x, y, x + .5, y + .5))
                for p in ([inter] if inter.geom_type == 'Polygon' else getattr(inter, 'geoms', [])):
                    if p.geom_type != 'Polygon' or p.area < 1e-10:
                        continue
                    for t in constrained_delaunay_triangles(p).geoms:
                        xyz = np.array([[xx, yy, floor(xx, yy)] for xx, yy in list(t.exterior.coords)[:3]])
                        if np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])[2] < 0:
                            xyz = xyz[::-1]
                        parts[name].append(xyz.tolist())
    stations = sorted({0., ring.length, *np.arange(0, ring.length, .3),
                       *[ring.project(Point(p)) for p in ring.coords]})
    joins = []
    for s0, s1 in zip(stations, stations[1:]):
        if s1 - s0 < 1e-8:
            continue
        p, q = [np.asarray(ring.interpolate(s).coords[0]) for s in (s0, s1)]
        zp, zq = floor(*p), floor(*q)
        rp, dp = road.sample(p)
        rq, dq = road.sample(q)
        assert max(dp, dq) < .006, (s0, s1, dp, dq)
        # The skirt must reach the adjacent road, even where the old inferred
        # road differs from the photographic platform. Report every upstand.
        a, b = [*p, zp], [*q, zq]
        c, d = [*q, min(rq - .03, zq - .02)], [*p, min(rp - .03, zp - .02)]
        parts['curb_face'] += [[a, c, b], [a, d, c]]
        joins.append(dict(station_m=s0, xy=p.tolist(), platform_z=zp, road_z=rp,
                          upstand_m=zp - rp, nearest_road_distance_m=dp))
    for station in np.arange(.5, ring.length, 1.1):
        p = np.asarray(ring.interpolate(station).coords[0])
        t = (np.asarray(ring.interpolate(station + .02).coords[0]) -
             np.asarray(ring.interpolate(station - .02).coords[0]))
        t /= np.linalg.norm(t)
        n = np.array([-t[1], t[0]])
        corners = [p - t * .0015, p + t * .0015,
                   p + n * .199 + t * .0015, p + n * .199 - t * .0015]
        xyz = [[x, y, floor(x, y) + .001] for x, y in corners]
        parts['curb_joint'] += [[xyz[0], xyz[1], xyz[2]], [xyz[0], xyz[2], xyz[3]]]
    triangles = np.asarray(parts['asphalt'] + parts['curb_top'])
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    slopes = np.linalg.norm(normals[:, :2], axis=1) / abs(normals[:, 2])
    assert abs(normals[:, 2].sum() / 2 - poly.area) < 1e-5
    if slopes.max() >= .075:
        bad = np.flatnonzero(slopes >= .075)
        failed = dict(reason='Prepared transition exceeds construction slope bound; no candidate floor saved.',
                      maximum_slope=float(slopes.max()), count=len(bad),
                      triangles=[dict(slope=float(slopes[i]), xyz=triangles[i].tolist()) for i in bad],
                      ramps=ramps, native_changed=False)
        write_path('derived/bellevue/bank_tram_shelter/platform_slope_failure.json').write_text(
            json.dumps(failed, indent=2), encoding='utf-8')
    assert slopes.max() < .075, float(slopes.max())
    heights = np.array([r['upstand_m'] for r in joins])
    threshold_errors = [floor(*v[:2]) - v[2] for r in ramps for v in r['threshold']]
    assert max(abs(np.asarray(threshold_errors))) < .003
    report = dict(platform_id='av_bo_boflaeche_a.355', platform_area_m2=platform.area,
                  included_end_noses=ends, area_m2=poly.area,
                  plane_weighted_rms_m=support['interior_candidate_plane']['weighted_rms_m'],
                  profile_weighted_rms_m=float(np.sqrt(np.average(residual ** 2, weights=areas))),
                  profile_residual_quantiles_m=np.quantile(residual, [0, .1, .5, .9, 1]).tolist(),
                  slope_quantiles=np.quantile(slopes, [.5, .9, .99, 1]).tolist(),
                  upstand_quantiles_m=np.quantile(heights, [0, .1, .5, .9, 1]).tolist(),
                  negative_upstand_count=int((heights < -.002).sum()),
                  raw_profile_edge_minimum_m=.007,
                  current_native_road_basis=dict(version=current['version'],
                                                native_sha256=current['native_sha256'],
                                                current_road_objects=current['current_road_objects'],
                                                probe_sha256=current['probe_sha256']),
                  end_threshold_error_max_m=max(abs(np.asarray(threshold_errors))),
                  profile=dict(knots=knots.tolist(), degree=3, coefficients=parameters[:count].tolist(),
                               crossfall=float(parameters[-1]), origin_xy=start.tolist(),
                               along=along.tolist(), across=across.tolist()),
                  ramps=ramps, non_crossing_route_intersections=excluded,
                  perimeter_road_comparison=joins,
                  source_files=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
                  ground_basis='Immutable photo-supported curved profile constrained above the independently probed current road; exact AV plan. End transition widths, grades and minimum relative edge clearance are inference. Current native road geometry agrees with the old recipe within 0.001mm; neither is a new engineering survey.',
                  independent_current_native_join_checked=False, visual_acceptance=False,
                  preparation_geometric_checks_passed=bool((heights>=-.002).all() and np.sqrt(np.average(residual**2,weights=areas))<.06),
                  ready_for_native_build=bool((heights>=-.002).all() and np.sqrt(np.average(residual**2,weights=areas))<.06),
                  next_required='If all preparation checks pass, build a versioned native candidate together with the complete shelter and furniture before bounded photo replacement; then independently reopen, probe joins and review actual views. Failed preparation is not ready for construction.',
                  natural_use_verified=False,
                  limits=['A large upstand may expose an earlier road-height error; do not automatically label it a real measured curb.',
                          'Do not cut source photography until complete candidate structures exist and current-native joins are checked.',
                          'Fit residual is agreement with photography, not a claim of survey precision or accessibility certification.'])
    output = dict(report=report, geometry_local=mapping(poly), parts=parts,
                  support_centres=[dict(xy=p, floor_z=floor(*p)) for p in spec['inferred_support_centres_local_xy']])
    out = write_path('derived/bellevue/bank_tram_shelter/platform_input.json')
    out.write_text(json.dumps(output, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['area_m2', 'plane_weighted_rms_m', 'profile_weighted_rms_m',
        'slope_quantiles', 'upstand_quantiles_m', 'negative_upstand_count', 'end_threshold_error_max_m',
        'independent_current_native_join_checked']}, indent=2))


if __name__ == '__main__':
    main()
