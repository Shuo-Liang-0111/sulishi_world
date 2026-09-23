"""Finish the seven remaining inventory trees on the already authored AV3573 island.

No additional external survey. Individual forms are explicit inference; source
positions, species and inventory heights remain authoritative. Photography is
replaced only inside each tree's bounded region, with unbuilt facilities guarded.
"""
from pathlib import Path
import json
import runpy
import numpy as np
from shapely.geometry import Point, Polygon, shape, mapping
from shapely.ops import unary_union

R = Path(__file__).resolve().parents[1]
D = R / 'derived/bellevue/south_remaining'
D.mkdir(exist_ok=True)
ctx = json.loads((R/'derived/bellevue/south_context/ground_support.json').read_text(encoding='utf-8'))
platform = json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text(encoding='utf-8'))
basis = json.loads((R/'derived/bellevue/south_context/photo_cut_basis.json').read_text())
service = json.loads((R/'derived/bellevue/south_service/build_input.json').read_text())
working = json.loads((R/'runtime/station_road_working.json').read_text())
assert working['version'] == 'G1_014r3'
built = {'fahrleitungen_mast.1799', 'fahrleitungen_mast.4217',
         'haltestellen_dfi_anzeiger.67', 'haltestellen_papierkorb.631',
         'haltestellen_infosystem.2864', 'haltestellen_infosystem.2581'}
built |= {f['id'] for f in service['facilities']}
guards = unary_union([shape(x['geometry']) for x in basis['protected_records'] if x['id'] not in built])
base = Path(working['source_cut_file']).name
trees, cuts = [], []
# Diameter, crown radii, clearance and replacement radius are inferred, separately
# from the retained 2022 inventory record. Do not present these as measured girths.
forms = [
    (129634, .81, (6.5, 6.0), 4.10, 9.0),
    (36770,  .76, (6.7, 6.2), 4.30, 9.0),
    (53451,  .59, (5.1, 4.9), 3.80, 8.0),
    (121245, .73, (5.8, 5.3), 3.95, 8.5),
    (60694,  .83, (6.2, 5.7), 4.20, 9.0),
    (65530,  .90, (7.0, 6.5), 4.45, 9.5),
    (114064, .97, (7.7, 7.1), 4.60, 10.0),
]
for ident, diameter, radii, clearance, replacement_radius in forms:
    pit = next(p for p in platform['pits'] if p['source']['properties']['objectid'] == ident)
    source = pit['source']
    c = np.asarray(source['geometry']['coordinates'], dtype=float)
    ground = pit['soil_z_local'] + ctx['origin'][2]
    height = float(source['properties']['hoehe'])
    area = Point(c).buffer(replacement_radius, quad_segs=80)
    for other in ctx['trees']:
        if other['properties']['objectid'] == ident:
            continue
        q = np.asarray(other['geometry']['coordinates'], dtype=float)
        n = (q-c) / np.linalg.norm(q-c)
        mid = (q+c)/2
        v = np.array([-n[1], n[0]])
        area = area.intersection(Polygon([mid+v*500, mid-v*500,
                                         mid-v*500-n*500, mid+v*500-n*500]))
    area = area.difference(guards)
    output = f'remaining_tree_{ident}_photo_cut.json'
    runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'), init_globals={
        'CUT_MASK': area, 'CUT_LOWER': ground+.01, 'CUT_UPPER': ground+height+1,
        'CUT_BASE': base, 'CUT_OUTPUT': output, 'CUT_STATS_KEY': 'remaining_tree',
        'CUT_DESCRIPTION': f'Replace inventory tree {ident}, radius {replacement_radius}m, '
            'clipped by neighboring-tree bisectors; retain soil, unbuilt facilities and '
            'all original source meshes. Explicitly inferred crown and bark.'
    })
    base = output
    trees.append({'source': source, 'ground_ln02_m': ground, 'height_m': height,
                  'origin': ctx['origin'],
                  'inferred': {'seed': ident, 'trunk_diameter_m': diameter,
                               'crown_radius_m': radii, 'branch_clearance_m': clearance},
                  'basis': 'Inventory XY/species/height; existing AV3573 soil surface. '
                           'Individual crown, girth, branching and bark are inferred, not scans.'})
    cuts.append({'source_id': source['id'], 'geometry_lv95': mapping(area),
                 'lower_ln02': ground+.01, 'upper_ln02': ground+height+1})

report = {'base_version': working['version'], 'trees': trees, 'cut_records': cuts,
          'source_cut_file': 'derived/bellevue/west_context/'+base,
          'remaining_facility_guards': [x['id'] for x in basis['protected_records'] if x['id'] not in built],
          'new_external_data_requested': False}
(D/'trees_input.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'trees': [t['source']['id'] for t in trees], 'final_cut': base}))
