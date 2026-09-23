"""Source-shaped underpass, lake approach and eastern bridge-bay input.

XY and identities come from cached AV/KUBA. The hidden floor, lining build-up,
steel sections and floor drainage are declared interpretations, not surveyed
as-built measurements. Actual bridge deck photo heights are used independently
of the city's simplified two-metre extrusion.
"""
from pathlib import Path
from functools import lru_cache
import hashlib
import json
import math
import numpy as np
from shapely.geometry import shape, mapping, Polygon, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, nearest_points
from shapely import constrained_delaunay_triangles, STRtree

R = Path(__file__).resolve().parents[1]
D = R/'derived/bellevue/quaibruecke_connection'
ctx = json.loads((D/'context.json').read_text())
F = {f['id']: f for f in ctx['known_features']+ctx['nearby_features']}
O = np.array(ctx['origin'])
under = shape(F['av_ei_flaechenelement_a.39461']['geometry'])
whole = shape(F['view_kuba_flaechen.477']['geometry'])
north = shape(F['av_bo_boflaeche_a.40750']['geometry'])
lake_wall = shape(F['av_ei_flaechenelement_a.15891']['geometry'])
south_stair = shape(F['av_ei_flaechenelement_a.6191']['geometry'])
low = json.loads((R/'derived/bellevue/riviera_lower/build_input.json').read_text())['floor_ln02_m']
terrain = np.load(D/'survey_terrain_context.npz')['triangles']
tp = [Polygon(q[:, :2]) for q in terrain]
tidx = STRtree(tp)


@lru_cache(maxsize=25000)
def ground(x, y):
    p = Point(x, y)
    i = int(tidx.nearest(p))
    q = np.array(nearest_points(tp[i], p)[0].coords[0])
    tr = terrain[i]
    w = np.linalg.solve((tr[1:, :2]-tr[0, :2]).T, q-tr[0, :2])
    return float(tr[0, 2]+w@(tr[1:, 2]-tr[0, 2]))


# Keep the current north joint level; the central hidden profile is interpreted
# from the below-water trough and visible beam/slab relation. No claim that the
# selected405.45 datum or resulting ramps are a measured accessibility profile.
route_xy = np.array([
    [2683489.1455, 1246847.886], [2683481.1198, 1246838.7392],
    [2683487.5001, 1246816.1526], [2683493.4978, 1246815.068],
    [2683503.7065, 1246810.6655], [2683507.79, 1246807.0287],
    [2683514.2981, 1246796.3735], [2683521.74, 1246779.23],
])
route = LineString(route_xy)
stations = np.r_[0., np.cumsum(np.linalg.norm(np.diff(route_xy, axis=0), axis=1))]
floor_z = np.array([low, 405.45, 405.45, 405.76, 406.69, 406.69, 406.69, 407.68])
profile_s = np.r_[0., .20, stations[1:]]
profile_z = np.r_[low, low, floor_z[1:]]


@lru_cache(maxsize=60000)
def floor(x, y):
    return float(np.interp(route.project(Point(x, y)), profile_s, profile_z))


# The southern KUBA approach is not replaced by a rectangular shortcut. The
# AV record wins in the central tunnel; tiny source-layer discrepancies remain
# explicitly quantified. Existing022 north paving is preserved.
south = whole.intersection(box(2683400, 1246700, 2683600, 1246817.4)).difference(under)
corridor = unary_union([under, south]).difference(north).buffer(0)
assert corridor.geom_type == 'Polygon', corridor.geom_type
assert 230 < corridor.area < 370


def path_between(ring, start, end, step):
    coords = np.array(ring.coords)[:-1]
    i = int(np.argmin(np.linalg.norm(coords-np.array(start), axis=1)))
    j = int(np.argmin(np.linalg.norm(coords-np.array(end), axis=1)))
    out = [coords[i]]
    while i != j:
        i = (i+step) % len(coords)
        out.append(coords[i])
        assert len(out) <= len(coords)
    return LineString(out)


ring = corridor.exterior
outer = path_between(ring, [2683488.212, 1246848.608], [2683520.256, 1246778.682], 1)
if outer.distance(Point(2683478.797, 1246840.083)) > .01:
    outer = path_between(ring, [2683488.212, 1246848.608], [2683520.256, 1246778.682], -1)
inner = path_between(ring, [2683490.079, 1246847.164], [2683523.234, 1246779.777], 1)
if inner.distance(Point(2683482.636, 1246839.0)) > .01:
    inner = path_between(ring, [2683490.079, 1246847.164], [2683523.234, 1246779.777], -1)
assert outer.distance(Point(2683478.797, 1246840.083)) < .01
assert inner.distance(Point(2683482.636, 1246839.0)) < .01
outer_band = outer.buffer(.26, cap_style='flat').intersection(corridor)
inner_band = inner.buffer(.24, cap_style='flat').intersection(corridor)
# The source steel stair is a side access through the landward retaining wall.
inner_band = inner_band.intersection(under.buffer(.05)).difference(south_stair.buffer(.08))
walk = corridor.difference(outer_band.union(inner_band)).difference(lake_wall).difference(south_stair)


def polys(g):
    return [p for p in ([g] if g.geom_type == 'Polygon' else getattr(g, 'geoms', []))
            if p.geom_type == 'Polygon' and p.area > 1e-8]


parts = []


def slab(name, geom, top, bottom, role, source):
    for k, p in enumerate(polys(geom)):
        p = orient(p, 1)
        vertices, faces, surfaces = [], [], []
        for tr in constrained_delaunay_triangles(p).geoms:
            xy = list(orient(tr, 1).exterior.coords)[:3]
            for fn, rev, label in [(top, False, 'top'), (bottom, True, 'bottom')]:
                pts = xy[::-1] if rev else xy
                off = len(vertices)
                vertices.extend([[x-O[0], y-O[1], fn(round(x, 6), round(y, 6))-400] for x, y in pts])
                faces.append([off, off+1, off+2]); surfaces.append(label)
        for edge in [p.exterior, *p.interiors]:
            for a, b in zip(list(edge.coords), list(edge.coords)[1:]):
                off = len(vertices)
                vertices.extend([[a[0]-O[0], a[1]-O[1], bottom(*a)-400],
                                 [b[0]-O[0], b[1]-O[1], bottom(*b)-400],
                                 [b[0]-O[0], b[1]-O[1], top(*b)-400],
                                 [a[0]-O[0], a[1]-O[1], top(*a)-400]])
                faces.append([off, off+1, off+2, off+3]); surfaces.append('side')
        parts.append(dict(name=name+(f'_{k}' if k else ''), vertices=vertices,
                          faces=faces, surfaces=surfaces, role=role, source=source,
                          plan=mapping(p), area_m2=p.area))


def split_slab(name, geom, top, bottom, role, source, interval=1.):
    for k, y in enumerate(np.arange(math.floor(geom.bounds[1]), math.ceil(geom.bounds[3]), interval)):
        slab(f'{name}_{k:03}', geom.intersection(box(2683400, y, 2683600, y+interval)),
             top, bottom, role, source)


split_slab('FLOOR', corridor.difference(lake_wall).difference(south_stair), floor,
           lambda x, y: floor(x, y)-.26, 'paving', 'AV39461 + KUBA477')


def parapet_top(x, y):
    # A940mm blue-lined trough parapet is inferred from the actual underpass
    # photograph. Outside the bridge, use the existing bank treatment family.
    return floor(x, y)+1.0


for name, region in [('WATER_WALL', outer_band.intersection(under)), ('LAND_WALL', inner_band)]:
    split_slab(name, region, parapet_top, lambda x, y: floor(x, y)-.26,
               'blue_lining', 'AV39461 + KUBA477', 1.5)
    split_slab(name+'_COPING', region.buffer(.025).intersection(corridor.buffer(.025)),
               lambda x, y: parapet_top(x, y)+.035, lambda x, y: parapet_top(x, y)-.035,
               'coping', 'reference_guided_trough_edge', 1.5)
split_slab('LAKE_EDGE_FASCIA', outer_band.difference(under),
           lambda x,y: floor(x,y)-.015, lambda x,y:floor(x,y)-.6,
           'concrete','KUBA477 lake edge',1.5)

# The real curved retaining wall remains separate from the low trough parapet.
retaining = lake_wall.intersection(box(2683400, 1246778.5, 2683600, 1246817)).difference(south_stair.buffer(.03))
split_slab('LAKE_RETAINING', retaining, lambda x, y: ground(round(x, 5), round(y, 5)),
           lambda x, y: floor(x, y)-.30, 'concrete', 'av_ei_flaechenelement_a.15891', 1.5)

#13 real riser lines, sorted in the true up-stair direction. Heights and steel
#sections are inference, while every riser XY and source identity are retained.
line_path = R/'sources/features/av_ei_linienelement.geojson'
lines = [f for f in json.loads(line_path.read_text(encoding='utf-8'))['features']
         if f['properties'].get('art_txt') == 'wichtige_Treppe'
         and shape(f['geometry']).distance(south_stair) < .05]
assert len(lines) == 13
lines.sort(key=lambda f: -np.mean(np.array(f['geometry']['coordinates'])[:, 1]))
start = np.array([[2683509.111, 1246806.166], [2683510.254, 1246807.136]])
boundaries = [start]
for f in lines:
    points = np.array(f['geometry']['coordinates'])
    if points[0, 0] > points[1, 0]: points = points[::-1]
    boundaries.append(points)
bottom_z = floor(*start.mean(0))
top_z = ground(2683513.55, 1246802.4)
rise = (top_z-bottom_z)/13
assert .14 < rise < .20, rise
treads = []
for i, (a, b) in enumerate(zip(boundaries, boundaries[1:])):
    p = Polygon([a[0], b[0], b[1], a[1]]).intersection(south_stair)
    treads.append(dict(index=i, lower_edge=a.tolist(), upper_edge=b.tolist(),
                       z=bottom_z+i*rise, source=lines[i]['id'], plan=mapping(p)))
covered = unary_union([shape(t['plan']) for t in treads])
landing = south_stair.difference(covered)
slab('SOUTH_STAIR_LANDING', landing, lambda x, y: top_z, lambda x, y: top_z-.08,
     'steel', 'av_ei_flaechenelement_a.6191')

# A robust deck curve is fitted to388-ish original photograph support faces.
# Independent cells prevent dense patches from dominating. No water-floor
# candidate is used here. Residuals remain recorded, rather than hidden.
deck_rows = np.load(D/'deck_photo_support.npz')['rows']
cells = {}
for q in deck_rows:
    cells.setdefault((int(q[0]//2), int(q[1]//2)), []).append(q[:3])
support = np.array([np.median(q, axis=0) for q in cells.values()])
X = np.c_[np.ones(len(support)), support[:, 0], support[:, 0]**2, support[:, 1]]
weights = np.ones(len(support))
for _ in range(15):
    coef = np.linalg.lstsq(X*weights[:, None], support[:, 2]*weights, rcond=None)[0]
    residual = support[:, 2]-X@coef
    weights = np.minimum(1., .07/np.maximum(abs(residual), 1e-9))
A = np.array([2683492.23, 1246814.496])
T = np.array([-117.419, -31.436]); T /= np.linalg.norm(T)
N = np.array([T[1], -T[0]])


def deck(x, y):
    st, d = (np.array([x, y])-A)@np.array([T, N]).T
    return float(coef@[1, st, st*st, d])


def xy(st, d): return A+st*T+d*N


bridge = shape(F['view_kuba_flaechen.502']['geometry'])
bay = bridge.intersection(Polygon([xy(-.03, -1), xy(22.625, -1), xy(22.625, 32), xy(-.03, 32)]))
for k, st in enumerate(np.arange(0, 22.625, 1.)):
    cell = Polygon([xy(st, -1), xy(min(st+1, 22.625), -1), xy(min(st+1, 22.625), 32), xy(st, 32)])
    slab(f'BRIDGE_SLAB_{k:02}', bay.intersection(cell), lambda x, y: deck(x, y)-.11,
         lambda x, y: deck(x, y)-.40, 'concrete', 'KUBA502 +1985 section +photo deck fit')

# Only the first/eastern bay is reconstructed; the remainder is existing
# photographic context. Its small boundary-crossing structural continuation is
# not an expansion of the G1 walking/acceptance area.
girder_stations = np.linspace(.0, 22.625, 93)
girders = []
for di, across in enumerate([4.69, 11.79, 18.89, 25.99]):
    arr = []
    for st in girder_stations:
        p = xy(st, across)
        u = (st-22.625/2)/(22.625/2)
        depth = 1.1+u*u*(.85 if u < 0 else 1.90)
        upper = deck(*p)-.42
        arr.append([float(st), *p, upper, upper-depth])
    girders.append(dict(index=di, across=across, stations=arr))

# Landward abutment is behind the path, not an invented public void. Its exact
#stone courses and the hidden mass are a reference-guided construction model.
abut = Polygon([xy(-1.5, 3.0), xy(1.8, 3.0), xy(1.8, 27.4), xy(-1.5, 27.4)])
abut = abut.difference(corridor.buffer(.04))
split_slab('ABUTMENT', abut, lambda x, y: deck(x, y)-.40,
           lambda x, y:404.75, 'abutment', 'KUBA502 eastern abutment', 1.5)

# Both source-shaped outside edges get continuous rail support records; they
#also define UV stationing and photo replacement, not gameplay/path targets.
edge_records = {}
for key, line in [('outer', outer), ('inner', inner)]:
    row = []
    for sta in np.linspace(0, line.length, max(2, int(line.length/.45)+1)):
        p = np.array(line.interpolate(sta).coords[0])
        a = np.array(line.interpolate(max(0, sta-.04)).coords[0])
        b = np.array(line.interpolate(min(line.length, sta+.04)).coords[0])
        t = (b-a)/np.linalg.norm(b-a)
        n = np.array([t[1], -t[0]])
        if not corridor.buffer(.002).covers(Point(p+n*.12)): n = -n
        row.append(dict(xy=p.tolist(), along=t.tolist(), inward=n.tolist(),
                        floor=floor(*p), station=float(sta)))
    edge_records[key] = row

hangers=[]
for girder in girders:
    across=girder['across']
    for side,line in [('outer',outer),('inner',inner)]:
        cross=line.intersection(LineString([xy(-2,across),xy(12,across)]))
        points=[cross] if cross.geom_type=='Point' else [q for q in getattr(cross,'geoms',[]) if q.geom_type=='Point']
        assert len(points)==1,(side,across,cross.geom_type)
        p=np.array(points[0].coords[0]);st=float((p-A)@T)
        samples=np.array(girder['stations'])
        end=float(np.interp(st,samples[:,0],samples[:,4]))
        hangers.append(dict(girder=girder['index'],side=side,xy=p.tolist(),bottom=floor(*p)+.96,top=end+.018))
bank_seats=[]
lake_line=outer.difference(under.buffer(.35))
segments=[lake_line] if lake_line.geom_type=='LineString' else list(lake_line.geoms)
lake_line=max(segments,key=lambda q:q.length)
for sta in np.linspace(.5,lake_line.length-.5,max(2,int(lake_line.length/2.35)+1)):
    p=np.array(lake_line.interpolate(sta).coords[0])
    a=np.array(lake_line.interpolate(max(0,sta-.04)).coords[0]);b=np.array(lake_line.interpolate(min(lake_line.length,sta+.04)).coords[0])
    t=(b-a)/np.linalg.norm(b-a);n=np.array([t[1],-t[0]])
    if not corridor.covers(Point(p+n*.3)):n=-n
    bank_seats.append(dict(xy=p.tolist(),along=t.tolist(),inward=n.tolist(),floor=floor(*p)))

report = dict(corridor_m2=corridor.area, unobstructed_plan_candidate_m2=walk.area,
              floor_profile_stations_m=profile_s.tolist(), floor_profile_ln02_m=profile_z.tolist(),
              maximum_centreline_grade=float(np.max(abs(np.diff(profile_z)/np.diff(profile_s)))),
              underpass_floor_inferred_ln02_m=405.45, source_riser_count=13,
              south_stair_low_ln02_m=bottom_z, south_stair_top_terrain_interpreted_ln02_m=top_z,
              south_stair_rise_m=rise, bridge_deck_fit_cells=len(support),
              bridge_deck_fit_median_abs_residual_m=float(np.median(abs(residual))),
              bridge_deck_fit_95pct_abs_residual_m=float(np.quantile(abs(residual), .95)),
              three_unclassified_low_photo_faces_excluded_from_floor=True,
              hidden_floor_profile_surveyed=False, geometry_authored=False, natural_use_verified=False)
out = dict(version='G1_023', origin=O.tolist(), corridor=mapping(corridor), walk=mapping(walk),
           underpass=mapping(under), outer=mapping(outer), inner=mapping(inner),
           retaining=mapping(retaining), south_stair=mapping(south_stair), bridge_bay=mapping(bay),
           parts=parts, treads=treads, stair_boundaries=[b.tolist() for b in boundaries],
           edges=edge_records, girders=girders, bridge_anchor=A.tolist(), bridge_along=T.tolist(),
           bridge_across=N.tolist(), bridge_deck_coefficients=coef.tolist(),
           route=route_xy.tolist(), route_floor=floor_z.tolist(), hangers=hangers,bank_seats=bank_seats,report=report,
           source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [D/'context.json', D/'survey_terrain_context.npz', D/'deck_photo_support.npz', line_path]})
(D/'build_input.json').write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'parts':len(parts), 'report':report}, indent=2))
