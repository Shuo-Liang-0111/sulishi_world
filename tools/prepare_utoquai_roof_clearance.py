"""Replace old photographic fragments over the reconstructed kiosk roof."""
from pathlib import Path
import json
import runpy
import numpy as np
from shapely.geometry import Point, shape, mapping
from shapely.ops import unary_union

root=Path(__file__).resolve().parents[1];data=root/'derived/bellevue/utoquai_kiosk'
plan=json.loads((data/'build_input.json').read_text())
foot=shape(plan['source']['footprint']['geometry'])
mask=foot.buffer(1.05)
guards=[]
for f in json.loads((root/'sources/features/av_ei_flaechenelement_a.geojson').read_text())['features']:
    if f['properties']['art_txt'] in ['Mauer.Mauer','wichtige_Treppe'] and shape(f['geometry']).distance(foot)<2:
        guards.append(shape(f['geometry']).buffer(.18))
mask=mask.difference(unary_union(guards))
pits=json.loads((root/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text())['pits']
rebuilt={t['source']['id']:t for t in pits}
inventory=json.loads((root/'sources/features/bauminventar.geojson').read_text())['features']
points=np.array([f['geometry']['coordinates'] for f in inventory]);owners=set()
minx,miny,maxx,maxy=mask.bounds
for x in np.arange(minx,maxx+.1,.20):
    for y in np.arange(miny,maxy+.1,.20):
        if not mask.covers(Point(x,y)):continue
        index=np.argmin(np.linalg.norm(points-[x,y],axis=1));ident=inventory[index]['id']
        assert ident in rebuilt,('Do not remove unbuilt neighboring tree',ident)
        owners.add(ident)
low=plan['source']['roof_ln02_m']+.002
high=max(rebuilt[ident]['ground_ln02_m']+rebuilt[ident]['height_m']+1.25 for ident in owners)
record={'mask_lv95':mapping(mask),'mask_m2':mask.area,'lower_ln02':low,'upper_ln02':high,'nearby_rebuilt_tree_owners':sorted(owners),'tree_ownership_sample_spacing_m':.20,'basis':'The current solid viewport exposes old photographic tree remnants directly above the authored kiosk. Rebuilt roof and inferred exhaust cowl replace the roof fixtures; already authored inventory trees replace the vegetation. Limit to kiosk+1.05m and protect cadastral walls/stairs. Keep all source blocks and distant context.'}
(data/'roof_clearance_input.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
runpy.run_path(str(root/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':low,'CUT_UPPER':high,'CUT_BASE':'utoquai_kiosk_clearance_cut.json','CUT_OUTPUT':'utoquai_kiosk_roof_cut.json','CUT_STATS_KEY':'utoquai_roof_clearance_stats','CUT_DESCRIPTION':record['basis']})
print(json.dumps({k:v for k,v in record.items() if k!='mask_lv95'}))
