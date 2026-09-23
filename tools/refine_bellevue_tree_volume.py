"""Use observed source rays, not an assumed natural trunk cylinder, for malformed photo replacement."""
import json,runpy
from pathlib import Path
import numpy as np
from shapely.geometry import Point,shape,mapping
from inspect_platform_road_join import Surface,road

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context'
data=json.loads((OUT/'tree_69773_input.json').read_text(encoding='utf-8'));xy=np.array(data['source']['geometry']['coordinates']);mask=Point(xy).buffer(5.5)
near=[]
for f in (ROOT/'sources/features/vbz').glob('*.geojson'):
 if f.stem in ['haltestellen_blindenrillenplat','haltestellen_haltebalken']:continue
 for r in json.loads(f.read_text())['features']:
  g=shape(r['geometry'])
  if g.geom_type not in ['Point','MultiPoint']:continue
  if g.distance(Point(xy))<8:near.append({'id':r['id'],'distance_m':g.distance(Point(xy))})
assert all(r['distance_m']>5.7 for r in near),'Do not remove an unmodeled upright facility.'
rays=[[2683533.81761,1246841.56366,410.89445],[2683532.79221,1246840.92941,409.94890],[2683534.71597,1246842.79741,409.85157],[2683530.85814,1246840.39679,411.70241],[2683535.77344,1246842.17635,412.69876]]
assert all(mask.contains(Point(p[:2])) for p in rays)
lower=data['ground_ln02_m']-.4;upper=data['ground_ln02_m']+14
runpy.run_path(str(ROOT/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_MASK':mask,'CUT_LOWER':lower,'CUT_UPPER':upper,'CUT_BASE':'platform_tip_photo_cut.json',
 'CUT_OUTPUT':'tree_69773_refined_photo_cut.json','CUT_STATS_KEY':'tree_stats',
 'CUT_DESCRIPTION':'Photo tree69773 sagged into a low green wall, confirmed by same-camera rays. Replace only 5.5m radius around source XY, LN02 ground-0.4 to ground+14. Nearest unmodeled VBZ upright mast is 6m away, excluded; ground tactile and halt marks are retained as source requirements, not claimed constructed. All authored roofs/surfaces and original photo reference remain.'})
camera_xy=xy+np.array([6,-14]);z,d=Surface(road).sample(camera_xy-np.array(data['origin'][:2]));assert d<1e-6
record={'rays_from_G1_008r6':rays,'source_node':'34280','mask':mapping(mask),'lower_ln02_m':lower,'upper_ln02_m':upper,'nearby_upright_facilities':near,
 'camera_position_local':[*(camera_xy-np.array(data['origin'][:2])),z+1.65],'eye_height_m':1.65,'camera_support_distance_m':d,
 'caution':'Crown envelope and replacement volume inferred; observed photo artifact extent is not actual botanical geometry.'}
(OUT/'tree_69773_volume_review.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,default=float))
