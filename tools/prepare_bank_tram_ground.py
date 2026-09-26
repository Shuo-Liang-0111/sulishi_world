"""Read complete AV355 photographic support without loading another Blender.

The native probe near the roof is spatially incomplete at the platform ends.
This preparation reads all intersecting immutable source tiles and keeps them
separate from current authored pavement. No source is cut and no floor is
accepted merely because a fitted surface can be produced.
"""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np
from shapely.geometry import Point, Polygon, shape, mapping
from shapely.affinity import translate
from shapely.ops import unary_union
from workspace_paths import read_path, write_path
from diagnose_bank_tram_platform import Layers


def main():
    spec_path = read_path('derived/bellevue/bank_tram_shelter/build_input.json')
    spec = json.loads(spec_path.read_text())
    origin = np.asarray(spec['origin_lv95_ln02'])
    central = shape(next(r for r in spec['land_use_beneath'] if r['id'].endswith('.355'))['geometry_local'])
    av_path = read_path('sources/features/av_bo_boflaeche_a.geojson')
    end_ids = {'av_bo_boflaeche_a.456', 'av_bo_boflaeche_a.457'}
    ends = [translate(shape(f['geometry']), -origin[0], -origin[1])
            for f in json.loads(av_path.read_text())['features'] if f['id'] in end_ids]
    assert len(ends) == 2
    poly = unary_union([central, *ends])
    assert poly.geom_type == 'Polygon' and not poly.interiors
    assert abs(poly.area - 285.91008671390495) < 1e-6
    inner = poly.buffer(-.22)
    region = poly.buffer(2)
    manifest_path = read_path('sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json')
    manifest = json.loads(manifest_path.read_text())
    rows, records, inputs = [], [], []
    for item in manifest['items']:
        center = np.asarray(item['mbs'][:3]) - origin
        if Point(center[:2]).distance(region) > item['mbs'][3]:
            continue
        path = read_path('sources/mesh/local_GEOZ_3DMesh_2_1/assets/' + str(item['node']) + '.bin')
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['geometry_sha256'], item['node']
        count = struct.unpack_from('<I', raw)[0]
        assert count == item['vertices'] and count % 3 == 0
        tri = (np.frombuffer(raw, dtype='<f4', count=count * 3, offset=8).reshape(-1, 3) + center).reshape(-1, 3, 3)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        length = np.linalg.norm(n, axis=1)
        mask = ((length > 1e-7) & (abs(n[:, 2]) > .94 * length) &
                (tri[:, :, 2].min(1) > 8.05) & (tri[:, :, 2].max(1) < 9.0))
        for index in np.flatnonzero(mask):
            g = Polygon(tri[index, :, :2])
            if not g.intersects(region):
                continue
            centroid = tri[index].mean(0)
            records.append(dict(source_node=str(item['node']), face=int(index), triangle=tri[index].tolist(),
                                centroid=centroid.tolist(), area_m2=float(length[index] / 2),
                                interior_overlap_m2=inner.intersection(g).area,
                                normal_vertical=float(abs(n[index, 2]) / length[index])))
        if mask.any():
            selected = tri[mask]
            rows.append(dict(name='ORIGINAL_I3S_' + str(item['node']), kind='retained_photo',
                             vertices_world=selected.reshape(-1, 3).tolist(),
                             faces=np.arange(selected.size // 3).reshape(-1, 3).tolist()))
        inputs.append(dict(node=item['node'], path=str(path), sha256=item['geometry_sha256']))
    surface = Layers(rows)
    lo = np.floor(np.asarray(poly.bounds[:2]) * 2) / 2
    samples = []
    for x in np.arange(lo[0], poly.bounds[2], .5):
        for y in np.arange(lo[1], poly.bounds[3], .5):
            if poly.covers(Point(x, y)):
                samples.append(dict(xy=[float(x), float(y)], hits=surface.hits([x, y])))
    points = np.asarray([r['centroid'] for r in records if r['interior_overlap_m2'] > .001])
    areas = np.asarray([r['interior_overlap_m2'] for r in records if r['interior_overlap_m2'] > .001])
    start = np.asarray(spec['axis_start_local_xy'])
    design = np.c_[np.ones(len(points)), points[:, :2] - start]
    base_weights = np.sqrt(np.minimum(areas, 2))
    coef = np.linalg.lstsq(design * base_weights[:, None], points[:, 2] * base_weights, rcond=None)[0]
    for _ in range(12):
        residual = points[:, 2] - design @ coef
        robust = np.sqrt(np.minimum(1., .045 / np.maximum(abs(residual), 1e-9)))
        w = base_weights * robust
        coef = np.linalg.lstsq(design * w[:, None], points[:, 2] * w, rcond=None)[0]
    residual = points[:, 2] - design @ coef
    output = dict(platform_id='av_bo_boflaeche_a.355', included_end_ids=sorted(end_ids),
                  geometry_local=mapping(poly), source_files=inputs,
                  av_sha256=hashlib.sha256(av_path.read_bytes()).hexdigest(),
                  spec_sha256=hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                  manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                  original_candidate_faces=records, original_samples=samples,
                  supported_samples=sum(bool(r['hits']) for r in samples), total_samples=len(samples),
                  interior_candidate_plane=dict(origin_xy=start.tolist(), coefficients=coef.tolist(),
                                                candidate_faces=len(points),
                                                residual_quantiles_m=np.quantile(residual, [0, .1, .5, .9, 1]).tolist(),
                                                weighted_rms_m=float(np.sqrt(np.average(residual ** 2, weights=areas)))),
                  floor_selected=False, native_changed=False,
                  limits=['These are original immutable photography, not current retained geometry.',
                          'Horizontal faces can include low objects; the robust plane is a candidate only.',
                          'Current street connections and intentional curb/ramp profiles need separate checks.'])
    path = write_path('derived/bellevue/bank_tram_shelter/complete_ground_support.json')
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(dict(file=str(path), source_tiles=len(inputs), faces=len(records),
                         supported_samples=output['supported_samples'], total_samples=len(samples),
                         interior_candidate_plane=output['interior_candidate_plane'], floor_selected=False), indent=2))


if __name__ == '__main__':
    main()
