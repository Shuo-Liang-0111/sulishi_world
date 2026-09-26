"""Main-owned, whole-component repair at the accepted SF1 right wall foot.

The stopped SF2 diagnostic is an input, not an accepted construction package.
All outputs are independent main candidates. No Blender or frozen file edits.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from shapely.geometry import Polygon, LineString, box, mapping
from shapely.ops import unary_union, split
from shapely import constrained_delaunay_triangles
from workspace_paths import read_path, write_path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',default='derived/stadelhofen_joint/G1_027r16/construction.json')
parser.add_argument('--cheek-inset',type=float,default=0.)
parser.add_argument('--cutter-bottom-offset',type=float,default=-2.)
args=parser.parse_args()
assert 0<=args.cheek_inset<=.01
assert args.cutter_bottom_offset in [-2.,-.043]

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def cross2(a,b):
    return a[0]*b[1]-a[1]*b[0]


paths = {
    'accepted_spec': read_path('parallel/stadelhofen_01/derived/build_input.json'),
    'accepted_parts': read_path('parallel/stadelhofen_01/derived/part_outlines.json'),
    'reviewed_diagnostic_basis': read_path('config/stadelhofen_wallfoot_reference.json'),
    'current_audit': read_path('derived/stadelhofen_joint/G1_027r15/current_fabric_audit.json'),
}
d = json.loads(paths['accepted_spec'].read_text())
parts = json.loads(paths['accepted_parts'].read_text())
basis = json.loads(paths['reviewed_diagnostic_basis'].read_text())
g = basis['ground']
components = {'components': basis['components']}
audit = json.loads(paths['current_audit'].read_text())
assert audit['native_sha256'] == '496397518d867f64a0ea2f8052b0247881ef0bbd9c5aa570a9857e71e6cf2b9d'
W = d['width_m']
cheeks = unary_union([Polygon(p) for p in d['wall_outlines']])
patch = box(12.78, -.82, 13.25, .44).difference(cheeks)
# The actual old base ends at u=13.25. A coplanar Boolean cutter left vertical
# sheets on that exterior edge in r03. Overrun only that exterior termination
# by 0.1 mm; the construction footprint and all internal protected edges stay.
cutter_patch = box(12.78, -.82, 13.2501, .44).difference(cheeks.buffer(-args.cheek_inset,join_style=2) if args.cheek_inset else cheeks)
# Ground-level continuation of the existing wall, not an extra platform/ramp.
wall = unary_union([box(W+.47, -.99, 13.27, -.66),
                    box(W+.391, -.915, W+.551, -.285)])
wall_exposed = wall.difference(cheeks)
pa, pb = np.asarray(g['shared_edge_uvz'])[:, :2]
direction = pb-pa
line = LineString([pa-direction*20, pb+direction*20])
reference = np.asarray(g['side85_reference_uv'])-pa
sign = np.sign(cross2(direction, reference))
planes = {r['source_face']: np.asarray(r['plane_c_u_v']) for r in g['planes']}


def polygons(shape):
    if shape.is_empty:
        return []
    return [shape] if shape.geom_type == 'Polygon' else [p for p in shape.geoms if p.geom_type == 'Polygon' and p.area > 1e-12]


def surface(shape):
    rows = []
    for p in polygons(shape):
        for section in split(p, line).geoms:
            q = section.representative_point()
            which = 85 if cross2(direction, np.array([q.x, q.y])-pa)*sign >= 0 else 144
            for triangle in constrained_delaunay_triangles(section).geoms:
                uv = np.asarray(triangle.exterior.coords[:-1])
                assert uv.shape == (3, 2)
                if cross2(uv[1]-uv[0], uv[2]-uv[0]) < 0:
                    uv = uv[::-1]
                rows.append(np.c_[uv, np.c_[np.ones(3), uv] @ planes[which]].tolist())
    return rows


def solid(triangles, lower, upper):
    """Weld top surface and close its actual boundary; offsets are vertical."""
    verts, faces, lookup = [], [], {}
    for tri in triangles:
        ids = []
        for p in tri:
            key = tuple(round(c, 9) for c in p)
            if key not in lookup:
                lookup[key] = len(verts)
                verts.append(p)
            ids.append(lookup[key])
        faces.append(ids)
    edges = {}
    for f in faces:
        for a, b in zip(f, f[1:]+f[:1]):
            key = tuple(sorted([a, b]))
            edges.setdefault(key, []).append((a, b))
    assert all(len(e) <= 2 for e in edges.values())
    n = len(verts)
    bottom = [[*p[:2], p[2]+lower] for p in verts]
    top = [[*p[:2], p[2]+upper] for p in verts]
    ff = [f[::-1] for f in faces]+[[v+n for v in f] for f in faces]
    ff += [[a, b, b+n, a+n] for e in edges.values() if len(e) == 1 for a, b in e]
    return {'vertices_uvz': bottom+top, 'faces': ff}


stones = []
stone_polys = []
manifest=json.loads(read_path('web/assets/G1_027r15_current_r01/manifest.json').read_text())
chunk=next(c for c in manifest['chunks'] if c['collection']=='SF1_AUTHOR_ENTRANCE')
assert sha(chunk['expected_file'])==chunk['expected_sha256']
expected=np.load(chunk['expected_file'],allow_pickle=False)
A,U,N=[np.asarray(d[k]) for k in ['A','U','N']]
for index, name in [(123, 'SF1_APRON_GRANITE.004'), (132, 'SF1_APRON_GRANITE.010')]:
    part = next(p for p in parts['parts'] if p['role'] == 'forecourt_slab' and p['index'] == index)
    # A 4 mm joint terminates stone at the newly continuous wall toe.
    outline = Polygon(part['outline']).difference(wall.buffer(.004, join_style=2))
    assert outline.difference(patch.buffer(1e-8)).area < 1e-10
    component = next(r for r in components['components'] if r['object'] == name)
    row=next(r for r in chunk['geometry'] if r['name']==name)
    key=row['key'];matrix=expected[key+'_matrix']
    wp=expected[key+'_positions']@matrix[:3,:3].T+matrix[:3,3]
    local=np.c_[(wp[:,:2]-A)@U,(wp[:,:2]-A)@N,wp[:,2]]
    tris=local[expected[key+'_triangles']]
    from shapely.geometry import Point
    old_plan=Polygon(part['outline']).buffer(.00002)
    seeds=[i for i,t in enumerate(tris) if all(old_plan.covers(Point(*v[:2])) for v in t)]
    # The bevel can extend slightly beyond a concave nominal edge. Select the
    # entire connected stone, never just the faces fitting inside its plan.
    parent=list(range(len(local)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    ids=expected[key+'_triangles']
    for a,b,c in ids:
        ra,rb,rc=find(int(a)),find(int(b)),find(int(c))
        parent[rb]=ra;parent[rc]=ra
    roots={find(int(ids[i,0])) for i in seeds}
    assert len(roots)==1,(name,'Ambiguous whole-stone seed',roots)
    indices=[i for i,t in enumerate(ids) if find(int(t[0])) in roots]
    assert len(indices)>=len(seeds)>8
    selected=tris[indices]
    assert selected[:,:,0].max()-selected[:,:,0].min()<.5
    assert selected[:,:,1].max()-selected[:,:,1].min()<.65
    stones.append({'old_object': name, 'old_component': component,
                   'remove_evaluated_triangle_indices':indices,
                   'whole_component_triangle_count':len(indices),
                   'nominal_inside_triangle_count':len(seeds),
                   'expected_triangle_count':len(tris),
                   'part_index': index, 'material': 'SF1_MAT_grey_granite_%02d' % part['tone'],
                   'shape': mapping(outline), 'mesh': solid(surface(outline), -.043, 0),
                   'edge_radius_m': .0012})
    stone_polys.append(outline)
assert wall.covers(box(12.779, -.818, 12.783, -.750)), 'Former 9 cm interface must actually lie within solid wall'
# Separate stone, bedding and narrow recessed joints. The old 39 mm overlap
# between broad mortar top and stone is removed in this bounded patch.
bed_surface = surface(patch)
joint_shape = patch.difference(unary_union(stone_polys)).difference(wall)
result = {'version': 'G1_027r16', 'base_version': 'G1_027r15',
          'base_native_sha256': audit['native_sha256'],
          'source_files': [{'role': k, 'path': str(p), 'sha256': sha(p)} for k, p in paths.items()],
          'frame': {k:d[k] for k in ['A','U','N']},
          'patch': mapping(patch), 'patch_area_m2': patch.area,
          'cutter': solid(surface(cutter_patch), args.cutter_bottom_offset, 2),
          'cutter_vertical_offsets_m': [args.cutter_bottom_offset,2.],
          'base_cut_plan': mapping(cutter_patch),
          'base_cut_inside_cheek_m': args.cheek_inset,
          'cutter_exterior_overrun_m': .0001,
          'cutter_overrun_basis': 'Numerical clearance beyond the actual old base outer boundary; no construction extension.',
          'bed': solid(bed_surface, -.180, -.043),
          'joint': solid(surface(joint_shape), -.043, -.004),
          'stones': stones, 'wall_plan': mapping(wall),
          'wall_visible_plan': mapping(wall_exposed),
          'wall_bottom_z': 10.34, 'wall_top_z': 11.265,
          'wall_footprint_basis': 'Exact plan of the accepted upper return and corner return; lower masonry is inferred continuation.',
          'ground_basis': 'Continue observed adjacent source planes85/144 across their common breakline; no slope target fitting.',
          'old_west_stone_preserved': True,
          'old_west_step_inside_new_solid_wall': True,
          'inferred': ['Lower masonry courses and foundation depth', 'Unseen ground beneath wall', 'Bedding construction and mortar optical finish'],
          'native_built': False, 'sf2_accepted': False}
# Two simple courses with recessed mortar; tessellate the same continuous L.
flat = []
for p in polygons(wall):
    for t in constrained_delaunay_triangles(p).geoms:
        q = np.asarray(t.exterior.coords[:-1])
        if cross2(q[1]-q[0],q[2]-q[0]) < 0:
            q=q[::-1]
        flat.append(np.c_[q,np.zeros(3)].tolist())
core_flat=[]
for p in polygons(wall.buffer(-.004, join_style=2)):
    for t in constrained_delaunay_triangles(p).geoms:
        q=np.asarray(t.exterior.coords[:-1])
        if cross2(q[1]-q[0],q[2]-q[0]) < 0:q=q[::-1]
        core_flat.append(np.c_[q,np.zeros(3)].tolist())
result['wall_core'] = solid(core_flat, 10.34, 11.251)
courses=[]
for i,(low,high) in enumerate([(10.34, 11.047), (11.050, 11.265)]):
    # The narrow joint is occupied by the real continuous core, not an air slit.
    courses.append({'name':'SJ_RIGHT_PLINTH_COURSE_%d'%i,
                    'mesh':solid(flat,low,high),'material':'SF1_MAT_pale_limestone_%02d'%(3+i),
                    'edge_radius_m':.0012})
result['wall_courses']=courses
target = write_path(args.output)
assert not target.exists(), 'Construction specifications referenced by saved natives are immutable; use a new --output path.'
target.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'path':str(target),'patch_area_m2':patch.area,'wall_plan_area_m2':wall.area,
                  'stone_plan_area_m2':sum(x.area for x in stone_polys),'frozen_files_written':False}))
