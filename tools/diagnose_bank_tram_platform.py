"""Compare AV355 with actual saved meshes before choosing its walking surface.

This is a read-only geometric diagnosis. Source normal direction does not
decide whether terrain exists, and no fitted plane is accepted as a floor.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from shapely import STRtree
from shapely.geometry import Point, Polygon, shape
from shapely.geometry.polygon import orient
from shapely.affinity import translate
from workspace_paths import read_path, write_path


class Layers:
    def __init__(self, rows):
        self.triangles, self.labels, self.faces, self.categories = [], [], [], []
        for row in rows:
            vertices = np.asarray(row['vertices_world'])
            for index, face in enumerate(row['faces']):
                for i in range(1, len(face) - 1):
                    tri = vertices[[face[0], face[i], face[i + 1]]]
                    normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
                    area = np.linalg.norm(normal)
                    if (area < 1e-10 or abs(normal[2]) < .92 * area or
                            tri[:, 2].min() < 7.8 or tri[:, 2].max() > 9.3):
                        continue
                    self.triangles.append(tri)
                    self.labels.append(row['name'])
                    self.faces.append(index)
                    self.categories.append('photo' if row['kind'] == 'retained_photo'
                                           else 'terrain' if row['name'] == 'SURVEY_TERRAIN'
                                           else 'authored')
        self.triangles = np.asarray(self.triangles)
        self.polys = [Polygon(t[:, :2]) for t in self.triangles]
        self.tree = STRtree(self.polys)

    def hits(self, xy):
        p = Point(xy)
        records = []
        for i in self.tree.query(p, predicate='intersects'):
            tri = self.triangles[i]
            w = np.linalg.solve((tri[1:, :2] - tri[0, :2]).T, np.asarray(xy) - tri[0, :2])
            records.append(dict(object=self.labels[i], category=self.categories[i],
                                face=self.faces[i], z=float(tri[0, 2] + w @ (tri[1:, 2] - tri[0, 2]))))
        return sorted(records, key=lambda r: -r['z'])


def main():
    specpath = read_path('derived/bellevue/bank_tram_shelter/build_input.json')
    probepath = read_path('derived/bellevue/bank_tram_shelter/native_probe_G1_027r10.json')
    spec, probe = [json.loads(p.read_text()) for p in (specpath, probepath)]
    av = next(r for r in spec['land_use_beneath'] if r['id'] == 'av_bo_boflaeche_a.355')
    poly = orient(shape(av['geometry_local']), 1)
    roof = shape(spec['roof_plan_local'])
    surface = Layers(probe['objects'])
    ring = poly.exterior
    stations = sorted({*np.arange(0, ring.length, .5),
                       *[ring.project(Point(p)) for p in ring.coords]})
    boundary = []
    for s in stations:
        xy = np.asarray(ring.interpolate(s).coords[0])
        tangent = (np.asarray(ring.interpolate((s + .025) % ring.length).coords[0]) -
                   np.asarray(ring.interpolate((s - .025) % ring.length).coords[0]))
        tangent /= np.linalg.norm(tangent)
        inward = np.array([-tangent[1], tangent[0]])
        boundary.append(dict(station_m=float(s), xy=xy.tolist(), inward=inward.tolist(),
                             inside=surface.hits(xy + inward * .06),
                             outside=surface.hits(xy - inward * .06)))
    crosspath = read_path('sources/features/tbl_routennetz.geojson')
    origin = np.asarray(spec['origin_lv95_ln02'])
    crossings = []
    for f in json.loads(crosspath.read_text())['features']:
        g = translate(shape(f['geometry']), -origin[0], -origin[1])
        if not g.intersects(poly):
            continue
        cross = g.intersection(ring)
        points = [cross] if cross.geom_type == 'Point' else list(getattr(cross, 'geoms', []))
        for p in points:
            if p.geom_type != 'Point':
                continue
            crossings.append(dict(source_id=f['id'], source_properties=f['properties'],
                                  xy=list(p.coords[0]), station_m=ring.project(p),
                                  hits=surface.hits(p.coords[0])))
    points = []
    lo = np.floor(np.array(poly.bounds[:2]) * 2) / 2
    for x in np.arange(lo[0], poly.bounds[2], .5):
        for y in np.arange(lo[1], poly.bounds[3], .5):
            if poly.covers(Point(x, y)):
                points.append(dict(xy=[float(x), float(y)], hits=surface.hits([x, y])))
    report = dict(native_sha256=probe['native_sha256'], version=probe['version'],
                  probe_sha256=hashlib.sha256(probepath.read_bytes()).hexdigest(),
                  spec_sha256=hashlib.sha256(specpath.read_bytes()).hexdigest(),
                  route_sha256=hashlib.sha256(crosspath.read_bytes()).hexdigest(),
                  platform_id=av['id'], platform_area_m2=poly.area,
                  support_triangles=len(surface.triangles), boundary_pairs=boundary,
                  official_walking_intersections=crossings, interior_samples=points,
                  source_normals_can_be_downward=True, floor_selected=False,
                  limits=['Terrain is an approximate reference, not surveyed curb or threshold height.',
                          'The current probe selected objects near the roof, not every tile along the full AV355 perimeter. Missing photo support outside that selection is inconclusive.',
                          'Photographic horizontal triangles can still include equipment tops.',
                          'Empty hit lists are not replaced by an unrecorded extrapolation.',
                          'Pedestrian routes indicate connection locations, not measured ramp profiles.'])
    out = write_path('derived/bellevue/bank_tram_shelter/platform_diagnosis_G1_027r10.json')
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 9), layout='constrained')
    for ax, category in zip(axes, ('photo', 'authored', 'terrain')):
        for g, color in ((poly, 'black'), (roof, '#dc6e24')):
            xy = np.asarray(g.exterior.coords)
            ax.plot(*xy.T, color=color, lw=1)
        samples = [[*p['xy'], h['z']] for p in points for h in p['hits'] if h['category'] == category]
        if samples:
            ss = np.asarray(samples)
            im = ax.scatter(ss[:, 0], ss[:, 1], c=ss[:, 2], s=6, vmin=8.2, vmax=8.9, cmap='viridis')
            fig.colorbar(im, ax=ax, shrink=.5, label='Local height [m]')
        for r in crossings:
            ax.scatter(*r['xy'], color='red', marker='x', s=40)
        ax.set_aspect('equal')
        ax.set_title(category + ' / saved r10 mesh')
    fig.suptitle('AV355 support diagnosis — not an accepted walking floor')
    fig.savefig(write_path('derived/bellevue/bank_tram_shelter/platform_diagnosis_G1_027r10.png'), dpi=135)
    summary = dict(file=str(out), area_m2=poly.area, samples=len(points), boundary_pairs=len(boundary),
                   crossings=[dict(id=r['source_id'], xy=r['xy'], station=r['station_m']) for r in crossings],
                   interior_supported={c:sum(any(h['category'] == c for h in p['hits']) for p in points)
                                       for c in ('photo', 'authored', 'terrain')}, floor_selected=False)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
