"""Dimension the inferred kiosk fabrication while preserving cached survey data."""
from pathlib import Path
import json
import runpy
import numpy as np
from shapely.geometry import shape, Polygon, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'derived/bellevue/utoquai_kiosk'
source = json.loads((DATA / 'source_input.json').read_text(encoding='utf-8'))
foot = shape(source['footprint']['geometry'])
floor = max(source['perimeter_grade_ln02_m']) + .008 - 400
roof = source['roof_ln02_m'] - 400
service_edges = [2, 3, 4]
door_edge = 1
windows = [5]
mask_parts = [foot.buffer(.40, join_style=2)]
for edge in source['edges']:
    if edge['index'] not in service_edges:
        continue
    a, b = np.array(edge['a_lv95']), np.array(edge['b_lv95'])
    n = np.array(edge['outward_xy'])
    t = (b - a) / edge['length_m']
    mask_parts.append(Polygon([a+t*.08-n*.08, b-t*.08-n*.08, b-t*.08+n*1.23, a+t*.08+n*1.23]))
mask = unary_union(mask_parts)
elements = json.loads((ROOT / 'sources/features/av_ei_flaechenelement_a.geojson').read_text())['features']
guards = [shape(f['geometry']).buffer(.12) for f in elements if f['properties']['art_txt'] in ['Mauer.Mauer','wichtige_Treppe'] and shape(f['geometry']).distance(foot)<2]
if guards:
    mask = mask.difference(unary_union(guards))
assert mask.covers(foot), 'Do not erase part of the real body through a guard'
record = {'base_version':'G1_019r3','version':'G1_020','source':source,'floor_local_inferred':floor,'roof_local':roof,'wall_height_m':roof-floor,'service_edges_inferred':service_edges,'staff_door_edge_inferred':door_edge,'closed_window_edges_inferred':windows,'counter_z_relative':.94,'serving_sill_z_relative':.965,'hatch_top_z_relative':2.16,'hatch_height_m':1.18,'hatch_open_degrees':-84,'wall_thickness_m':.085,'roof_membrane_thickness_m':.04,'photo_cut_mask_lv95':mapping(mask),'photo_cut_lower_ln02':405.28,'photo_cut_upper_ln02':411.32,'basis':'Official eight-sided AV footprint and roof height retained. Source extrusion bottom is not floor. Level floor8mm above highest existing perimeter grade; south staff threshold about2-4cm. Opening assignment, fabrication, counters, hidden sides and kitchen are explicit inference from limited exterior photograph, not a surveyed as-built interior. Public approach stays outside the staff kitchen; no research-task staging. Existing source wall/stair geometry protected.','accepted':False}
(DATA / 'build_input.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
runpy.run_path(str(ROOT/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':record['photo_cut_lower_ln02'],'CUT_UPPER':record['photo_cut_upper_ln02'],'CUT_BASE':'limmat_sidewalk_low_canopy_cut.json','CUT_OUTPUT':'utoquai_kiosk_photo_cut.json','CUT_STATS_KEY':'utoquai_kiosk_stats','CUT_DESCRIPTION':'G1_020 replacement of source EGID302020548 body and inferred service-hatch envelope only, LN02405.28..411.32. Nearby cadastral wall/stair guards retained; original2039 photo nodes untouched.'})
print(json.dumps({'floor_local':floor,'roof_local':roof,'height':roof-floor,'cut_area_m2':mask.area,'source_area_m2':foot.area}))
