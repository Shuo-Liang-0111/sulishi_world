"""Release obsolete kiosk-eave protection only over already rebuilt sidewalk."""
from pathlib import Path
import json
import runpy
from shapely.geometry import shape, Point, mapping
from shapely.ops import unary_union

root=Path(__file__).resolve().parents[1]
data=root/'derived/bellevue/utoquai_kiosk'
plan=json.loads((data/'build_input.json').read_text())
foot=shape(plan['source']['footprint']['geometry'])
sidewalk=shape(json.loads((root/'derived/bellevue/limmat_sidewalk/context.json').read_text())['source']['geometry'])
old=json.loads((root/'derived/bellevue/limmat_sidewalk/low_canopy_basis.json').read_text())
trees=unary_union([shape(t['crown_mask_lv95']) for t in old['trees']])
guards=[]
for f in json.loads((root/'sources/features/av_ei_flaechenelement_a.geojson').read_text())['features']:
    if f['properties']['art_txt'] in ['Mauer.Mauer','wichtige_Treppe'] and shape(f['geometry']).distance(foot)<2:
        guards.append(shape(f['geometry']).buffer(.18))
mask=foot.buffer(1.05).intersection(sidewalk).intersection(trees).difference(unary_union(guards))
rays=json.loads((root/'evidence/G1_020/kiosk_photo_residual_rays.json').read_text())
target=[r['hits'][0] for r in rays if r['camera']=='UR_QA_NORTH' and r['pixel'] in [[680,375],[545,600]]]
assert len(target)==2
for hit in target:
    x,y,z=hit['point_local']
    assert hit['node']=='34344' and hit['nearby_trees'][0]['already_rebuilt']
    assert mask.covers(Point(x+2683775,y+1246700)), 'Evidence point is outside safe replacement mask'
low=min(plan['source']['perimeter_grade_ln02_m'])+.12
high=max(plan['source']['perimeter_grade_ln02_m'])+4.6
record={'base':'G1_020','mask_lv95':mapping(mask),'area_m2':mask.area,'lower_ln02':low,'upper_ln02':high,
        'evidence_pixels':[[680,375],[545,600]],'protected_wall_stair':mapping(unary_union(guards)),
        'basis':'Actual north-camera rays hit low photographic vegetation within the obsolete1m kiosk protection ring. Kiosk and adjacent AV24105 ground/trees now have authored replacements. Release only this bounded ring over rebuilt ground/tree territories. Neighbor walls, steps, ground below12cm and unbuilt river context remain protected.'}
(data/'refinement_input.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
runpy.run_path(str(root/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
    'CUT_MASK':mask,'CUT_LOWER':low,'CUT_UPPER':high,'CUT_BASE':'utoquai_kiosk_photo_cut.json',
    'CUT_OUTPUT':'utoquai_kiosk_clearance_cut.json','CUT_STATS_KEY':'utoquai_clearance_stats',
    'CUT_DESCRIPTION':'G1_020r1 '+record['basis']})
print(json.dumps({'mask_m2':mask.area,'range_ln02':[low,high],'source_photo_retained':True}))
