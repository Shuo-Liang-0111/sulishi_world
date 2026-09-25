"""Extract the next frontage's real identity and envelope, without authoring it.

Only cached municipal geometry and the architect's reference manifest are used.
The CityGML ground plane is an envelope base, not a walkable entrance level.
No photogrammetry is removed and no native scene or runtime is modified.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path


ORIGIN = np.array([2683775., 1246700., 400.])
EGID = 2372625


def read_source(relative):
    path = read_path(relative)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return json.loads(path.read_text('utf-8')), dict(
        path=str(path), sha256=digest, bytes=path.stat().st_size)


def triangulate_surface(feature):
    """Retain surveyed 3D vertices and ring holes; audit projected triangulation."""
    assert feature['geometry']['type'] == 'MultiPolygon'
    triangles, audit = [], []
    for index, source_rings in enumerate(feature['geometry']['coordinates']):
        rings = [np.asarray(ring, float) - ORIGIN for ring in source_rings]
        assert all(np.allclose(ring[0], ring[-1], rtol=0, atol=1e-7) for ring in rings)
        outer = rings[0]
        normal = np.cross(outer[:-1], outer[1:]).sum(0)
        assert np.linalg.norm(normal) > 1e-8, (feature['id'], index)
        normal /= np.linalg.norm(normal)
        axes = [axis for axis in range(3) if axis != int(np.argmax(abs(normal)))]
        poly = Polygon(outer[:, axes], holes=[r[:, axes] for r in rings[1:]])
        assert poly.is_valid and not poly.is_empty, (feature['id'], index)
        points = np.concatenate(rings)
        triangulation = constrained_delaunay_triangles(poly)
        area = 0.
        for tri in triangulation.geoms:
            if tri.area < 1e-10:
                continue
            assert poly.covers(tri), (feature['id'], index, 'triangle left source rings')
            vertices = []
            for xy in list(tri.exterior.coords)[:3]:
                distances = np.linalg.norm(points[:, axes] - xy, axis=1)
                nearest = int(np.argmin(distances))
                assert distances[nearest] < 1e-7, 'Do not invent 3D vertices in source constraints'
                vertices.append(points[nearest].tolist())
            # Preserve the actual source face orientation as well as positions.
            a, b, c = np.array(vertices)
            if np.dot(np.cross(b-a, c-a), normal) < 0:
                vertices[1], vertices[2] = vertices[2], vertices[1]
            triangles.append(dict(source=feature['id'], polygon=index,
                                  surface_type=feature['properties']['type'], vertices=vertices))
            area += tri.area
        assert abs(area-poly.area) < 1e-6, (feature['id'], index, area, poly.area)
        audit.append(dict(source=feature['id'], polygon=index, rings=len(rings),
                          projected_area_m2=poly.area, triangles=len(triangulation.geoms),
                          max_source_plane_residual_m=float(np.max(abs((points-outer[0]) @ normal))),
                          invented_vertices=0, repaired_geometry=False))
    return triangles, audit


def main():
    av, av_meta = read_source('sources/features/av_bo_boflaeche_a.geojson')
    addresses, address_meta = read_source('sources/features/av_geb_gebaeudeadresse_t.geojson')
    model, model_meta = read_source('sources/features/bauten_dachmodell_3d.geojson')
    probe, probe_meta = read_source('derived/sternen_neighbor/r8_pixel_geometry.json')
    references, reference_meta = read_source('sources/references/ubs_theaterstrasse20/reference_manifest.json')
    building = next(f for f in av['features'] if f['id'] == 'av_bo_boflaeche_a.23105')
    assert int(building['properties']['gwr_egid']) == EGID
    entries = [f for f in addresses['features'] if int(f['properties'].get('gwr_egid') or 0) == EGID]
    assert len(entries) == 1 and entries[0]['properties']['adresse'] == 'Theaterstrasse 20'
    surfaces = [f for f in model['features'] if int(f['properties'].get('egid') or 0) == EGID]
    assert len(surfaces) == 5
    ring = np.asarray(building['geometry']['coordinates'][0]) - ORIGIN[:2]
    footprint = Polygon(ring)
    assert footprint.is_valid and 364 < footprint.area < 364.2
    # Long road-side edge, identified from the source ring and official entrance.
    # Endpoints, not an invented axis-aligned facade, determine the local frame.
    A = np.array([2683613.920, 1246848.966]) - ORIGIN[:2]
    B = np.array([2683628.236, 1246832.731]) - ORIGIN[:2]
    assert min(np.linalg.norm(ring-A, axis=1)) < 1e-6
    assert min(np.linalg.norm(ring-B, axis=1)) < 1e-6
    U = (B-A) / np.linalg.norm(B-A)
    N = np.array([U[1], -U[0]])
    center = np.array(footprint.representative_point().coords[0])
    assert np.dot(center-A, N) < 0, 'Street normal must point outside the building'
    entry_xy = np.asarray(entries[0]['geometry']['coordinates']) - ORIGIN[:2]
    entry_uv = np.array([np.dot(entry_xy-A, U), np.dot(entry_xy-A, N)])
    # Address labels are not surveyed door jambs. Keep their actual offset.
    faces, checks = [], []
    for feature in surfaces:
        if feature['properties']['type'] != 'GroundSurface':
            triangles, audit = triangulate_surface(feature)
            faces.extend(triangles)
            checks.extend(audit)
    ground_z = sorted({point[2] for f in surfaces if f['properties']['type'] == 'GroundSurface'
                       for poly in f['geometry']['coordinates'] for r in poly for point in r})
    assert ground_z == [405.103]
    data = dict(identity=dict(egid=EGID, av=building['id'], address='Theaterstrasse 20',
                              use='UBS Bellevue; ground frontage shared with other tenants'),
                origin_lv95_ln02=ORIGIN.tolist(), A=A.tolist(), U=U.tolist(), N=N.tolist(),
                street_width_m=float(np.linalg.norm(B-A)), footprint_local=ring.tolist(),
                footprint_area_m2=footprint.area, address_entry=entries[0],
                address_point_local_uv=entry_uv.tolist(), official_envelope_features=surfaces,
                envelope_triangles=faces, triangulation_audit=checks,
                official_base_plane_ln02_m=ground_z,
                entrance_floor_z=None,
                entrance_level_basis='Pending fresh support sampling. 405.103 is the envelope base, not the entrance floor.',
                references=references, source_files=[av_meta, address_meta, model_meta, probe_meta, reference_meta],
                diagnostic_camera=probe['camera'], scan_probe_file=probe_meta['path'],
                photo_crop_ready=False, native_authored=False, public_interior_selected=False,
                constraints=[
                    'Do not remove whole CTX_I3S_33552: building and foreground share welded topology.',
                    'Front canopy, panel seams, windows and rear metal cladding are visible photographic constraints.',
                    'Exact opening heights, metal profiles, optical material parameters and unobserved faces are inference.',
                    'The architect photographs accompany a 2014 renovation; their capture date is not stated.',
                    'Reference photos are not redistributed or used as scene textures.',
                    'No restaurant or bank interior is newly selected for public runtime access by this data extraction.'])
    target = write_path('derived/ubs_theaterstrasse20/site_constraints.json')
    target.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps(dict(file=str(target), egid=EGID, street_width_m=data['street_width_m'],
                         footprint_m2=footprint.area, surface_features=len(surfaces),
                         triangles=len(faces), ring_holes=sum(c['rings']-1 for c in checks),
                         max_plane_residual_m=max(c['max_source_plane_residual_m'] for c in checks),
                         entrance_level_assumed=False, native_authored=False)))


if __name__ == '__main__':
    main()
