"""Replace residual canopy as one continuous volume around the twelve rebuilt trees."""
import json,runpy
from pathlib import Path
import numpy as np
from shapely.geometry import Point,Polygon,shape,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/canopy_continuity/G1_017r1';D.mkdir(parents=True,exist_ok=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());assert w['version']=='G1_017'
ctx=json.loads((R/'derived/bellevue/south_context/ground_support.json').read_text())
p=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text())
inventory=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
roof_data=json.loads((R/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features']
LOWER=413.10;radius=16.;pieces=[]
for tree in ctx['trees']:
    c=np.array(tree['geometry']['coordinates']);area=Point(c).buffer(radius,quad_segs=96)
    for other in inventory:
        if tree['id']==other['id']:continue
        q=np.asarray(other['geometry']['coordinates'])[:2]
        if np.linalg.norm(q-c)>2*radius:continue
        n=q-c;n/=np.linalg.norm(n);mid=(q+c)/2;v=np.array([-n[1],n[0]])
        area=area.intersection(Polygon([mid+v*500,mid-v*500,mid-v*500-n*500,mid+v*500-n*500]))
    pieces.append(area)
mask=unary_union(pieces)
def coordinates(value):
    if isinstance(value,list) and value and isinstance(value[0],(float,int)):yield value
    elif isinstance(value,list):
        for item in value:yield from coordinates(item)
guards=[]
for f in roof_data:
    points=np.array(list(coordinates(f['geometry']['coordinates'])))
    if len(points) and points.shape[1]>=3 and points[:,2].max()>=LOWER-.2:
        polygon=shape(f['geometry'])
        if not polygon.is_valid:polygon=polygon.buffer(0)
        if not polygon.is_empty and polygon.intersects(mask):guards.append(polygon.buffer(.35))
mask=mask.difference(unary_union(guards))
upper=max(400+pit['soil_z_local']+pit['source']['properties']['hoehe'] for pit in p['pits'])+3
out='grove_continuous_upper_photo_cut.json'
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
    'CUT_MASK':mask,'CUT_LOWER':LOWER,'CUT_UPPER':upper,'CUT_BASE':Path(w['source_cut_file']).name,'CUT_OUTPUT':out,'CUT_STATS_KEY':'grove_canopy_continuity',
    'CUT_DESCRIPTION':f'G1_017r1: replace remaining upper source crown around all12 already authored AV3573 trees as one continuous zone. Maximum16m radius, full inventory nearest-tree partition excludes unbuilt neighboring trees; tall surveyed roofs protected. Only LN02 {LOWER}..{upper:.3f}. Ground objects and original photo source retained. This is a context cleanup extent, not a measured crown size.'})
record={'base_version':'G1_017','target_version':'G1_017r1','source_cut_file':'derived/bellevue/west_context/'+out,
        'tree_ids':[f['properties']['objectid'] for f in ctx['trees']],'mask_lv95':mapping(mask),'area_m2':mask.area,'kept_below_ln02_m':LOWER,'upper_ln02_m':upper,'protected_roofs':len(guards),
        'basis':'017 actual east image retained fragments associated with tree114064 and bin1173 guard, plus60694 at12.385m. North image still shows merged upper canopy. Clean the continuous already-rebuilt grove, preserving all neighboring inventory regions and ground features.',
        'new_external_data':False,'inferred_extent':True,'accepted':False}
(D/'input.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='mask_lv95'}))
