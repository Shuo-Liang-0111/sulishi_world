"""Site-specific fixture assembly, retaining source anchors and uncertainty."""
import hashlib
import json
import math
import numpy as np
from shapely.geometry import Point, Polygon, shape, mapping
from workspace_paths import read_path, write_path


def main():
    sp = read_path('derived/bellevue/bank_tram_shelter/build_input.json')
    pp = read_path('derived/bellevue/bank_tram_shelter/platform_input.json')
    spec, platform = [json.loads(p.read_text()) for p in [sp, pp]]
    assert platform['report']['ready_for_native_build']
    origin = np.array(spec['origin_lv95_ln02'][:2])
    island = shape(platform['geometry_local'])
    triangles = np.array(platform['parts']['asphalt'] + platform['parts']['curb_top'])
    centres = triangles[:, :, :2].mean(1)

    def ground(xy):
        for idx in np.argsort(np.linalg.norm(centres - xy, axis=1))[:100]:
            t = triangles[idx]
            mat = (t[1:, :2] - t[0, :2]).T
            if abs(np.linalg.det(mat)) < 1e-12:
                continue
            w = np.linalg.solve(mat, xy - t[0, :2])
            if min(w) >= -1e-7 and w.sum() <= 1.0000001:
                return float(t[0, 2] + w @ (t[1:, 2] - t[0, 2]))
        raise AssertionError(('Facility outside actual candidate floor', xy))

    by_id = {r['id']: r for r in spec['nearby_facilities']}
    def anchor(name): return np.array(shape(by_id[name]['geometry']).centroid.coords[0]) - origin
    ad_ids = ['haltestellen_plakatstelle.1020', 'haltestellen_plakatstelle.598']
    xy = [anchor(name) for name in ad_ids]
    axis = (xy[1] - xy[0]) / np.linalg.norm(xy[1] - xy[0])
    # Normal points to the waiting side toward the central plaza, away from bank.
    normal = np.array([-axis[1], axis[0]])
    bank = json.loads(read_path('derived/ubs_theaterstrasse20/build_input.json').read_text())
    if normal @ np.array(bank['N']) < 0:
        axis, normal = -axis, -normal
    benches = []
    for ident in [562, 570, 328]:
        name = f'haltestellen_sitzgelegenheit.{ident}'
        point = anchor(name)
        if ident == 328:
            theta = math.radians(float(by_id[name]['properties']['orientierung']))
            u = np.array([math.sin(theta), math.cos(theta)])
            n = np.array([-u[1], u[0]])
            if n @ normal < 0: u, n = -u, -n
            offset, length = 0., 2.
        else:
            u, n = axis, normal
            offset, length = .46, 2.64
        centre = point + n * offset
        footprint = Polygon([centre + u * a + n * b for a, b in
                             [(-length/2, -.29), (length/2, -.29), (length/2, .29), (-length/2, .29)]])
        assert island.buffer(.003).covers(footprint), name
        supports = []
        for along in [-length * .37, length * .37]:
            for across in [-.225, .225]:
                p = centre + u * along + n * across
                supports.append(dict(along=along, across=across, xy=p.tolist(), z=ground(p)))
        benches.append(dict(source_id=name, source_anchor_xy=point.tolist(), centre_xy=centre.tolist(),
            source_properties=by_id[name]['properties'], axis=u.tolist(), front=n.tolist(),
            inferred_length_m=length, inferred_seat_offset_m=offset,
            floor_z=ground(centre), supports=supports, footprint=mapping(footprint),
            basis='Exact source anchor and interpreted orientation. Long benches are offset from shared windscreen/ad assembly anchors; length, section and fabrication are inferred from cached photographs.'))
    # The two long seats are adjacent along one row, not overlapping benches
    # independently centred on the same ad-plane geometry.
    assert shape(benches[0]['footprint']).distance(shape(benches[1]['footprint'])) > .1
    ticket_source = by_id['haltestellen_ticketautomat.577']
    corners = np.array(ticket_source['geometry']['coordinates'][0][0])[:4] - origin
    edges = np.roll(corners, -1, axis=0) - corners
    lengths = np.linalg.norm(edges, axis=1)
    u = edges[np.argmax(lengths)] / max(lengths)
    n = np.array([-u[1], u[0]])
    if n @ normal < 0: u, n = -u, -n
    center = corners.mean(0)
    ticket = dict(source_id=ticket_source['id'], source_geometry=ticket_source['geometry'],
        center_xy=center.tolist(), axis=u.tolist(), front=n.tolist(),
        width_m=float(max(lengths)), depth_m=float(min(lengths)), floor_z=ground(center),
        basis='Source footprint retained; source location quality unknown and date unspecified. Blue control face, grey casing and mechanical details photo-guided. Height and operator direction are inferred; no operational sales system.')
    info_id = 'haltestellen_infosystem.2354'
    ip = anchor(info_id)
    ticket['nearby_info'] = dict(source_id=info_id, anchor_xy=ip.tolist(),
        source_properties=by_id[info_id]['properties'], floor_z=ground(ip),
        offset_in_ticket_frame=[float((ip-center) @ u), float((ip-center) @ n)],
        basis='Public type code85 has no verified subtype description in cached records. Keep anchor/identity; any small attached information panel is an explicit inference, not a surveyed model match. Do not invent timetable values.')
    ads = [dict(source_id=name, center_xy=anchor(name).tolist(), axis=axis.tolist(), front=normal.tolist(),
        floor_z=ground(anchor(name)), inferred_width_m=1.205, inferred_height_m=1.79,
        inferred_bottom_m=.38, source_properties=by_id[name]['properties'],
        basis='Source point/orientation and photograph-guided windscreen cabinet. F200-size family used as dimensional inference; neutral original artwork, not claimed installed campaign.') for name in ad_ids]
    # This floor sample lets the construction resolve every foot, not just a
    # bench's central anchor. No geometry is created in this preparation.
    out = dict(origin_lv95_ln02=spec['origin_lv95_ln02'], egid=spec['egid'], ads=ads,
        benches=benches, ticket=ticket, sources=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [sp, pp]],
        source_identities_retained=list(by_id), native_changed=False, visual_acceptance=False,
        limits=['Information type85 subtype and exact assembly remain inference.','Fixture mechanisms and runtime state will be verified separately after construction.'])
    target = write_path('derived/bellevue/bank_tram_shelter/fixtures_input.json')
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(dict(file=str(target), ads=len(ads), benches=len(benches),
                         ticket_footprint_m=[ticket['width_m'], ticket['depth_m']],
                         adjacent_bench_gap_m=shape(benches[0]['footprint']).distance(shape(benches[1]['footprint'])),
                         info_type_unresolved=True), ensure_ascii=False))


if __name__ == '__main__': main()
