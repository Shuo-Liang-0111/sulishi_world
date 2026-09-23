"""Use the existing tree inventory and authored soil; no new place survey."""
from pathlib import Path
import json,hashlib,runpy,numpy as np
from shapely.geometry import Point,shape,mapping
R=Path(__file__).resolve().parents[1];D=R/'derived/haus_bellevue';O=np.array([2683775,1246700,400])
source=R/'sources/features/bauminventar.geojson';tree=next(f for f in json.loads(source.read_text(encoding='utf-8'))['features'] if f['properties']['objectid']==119962)
b=json.loads((D/'build_input.json').read_text(encoding='utf-8'));xy=np.array(tree['geometry']['coordinates']);ground=b['tree_pit']['ground_z_local']+400
assert np.linalg.norm(xy-O[:2]-b['tree_pit']['center_local'])<1e-6
mask=Point(xy).buffer(6.1,quad_segs=64)
context=json.loads((D/'context.json').read_text(encoding='utf-8'));assert shape(context['building_footprint']['geometry']).distance(mask)>3.0
near=[]
for p in (R/'sources/features/vbz').glob('*.geojson'):
 for f in json.loads(p.read_text(encoding='utf-8'))['features']:
  g=shape(f['geometry'])
  if g.geom_type in ['Point','MultiPoint'] and g.distance(Point(xy))<6.1:near.append(f['id'])
assert not near,near
record={'source':tree,'source_file':str(source.relative_to(R)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'origin':O.tolist(),'ground_ln02_m':ground,'ground_basis':'Previously built AV35946 soil patch, reconstructed from the shared frontage/road grade; not a separate height survey.','height_m':17.0,'inferred':{'seed':119962,'trunk_diameter_m':.72,'crown_radius_m':[5.7,5.0],'branch_clearance_m':4.0},'mask_lv95':mapping(mask),'basis':'XY/species/17m height from the existing 2022 inventory; individual trunk/crown/branches/leaves and tree-pit detail inferred.','accepted':False}
(D/'tree_119962_input.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
# Preserve unbuilt adjacent ground; the source tree is replaced above ankle height.
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_MASK':mask,'CUT_LOWER':ground+.12,'CUT_UPPER':ground+18.4,
 'CUT_BASE':'haus_upper_balcony_refined_cut.json','CUT_OUTPUT':'haus_tree_119962_photo_cut.json','CUT_STATS_KEY':'haus_tree_replacement',
 'CUT_DESCRIPTION':'Replace distorted source tree119962 within radius6.1m from inventory XY, above existing soil+0.12m to soil+18.4m; no mapped VBZ upright facility or building falls in this volume. Ground below the cut and all original source geometry retained. Branch and crown form inferred.'})
print(json.dumps({'source_id':tree['id'],'ground_ln02_m':ground,'mask_area_m2':mask.area,'height_m':17.0}))
