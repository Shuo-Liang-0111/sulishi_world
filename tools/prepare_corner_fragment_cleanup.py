"""Remove observed remnants only where source ground has already been rebuilt."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import Point,MultiPoint,shape,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/west_context';O=np.array([2683775,1246700])
platform=shape(json.loads((D/'platform_input.json').read_text())['geometry_lv95'])
hits=np.array([[-241.60360718,150.71815491],[-242.99891663,150.16545105],[-241.03945923,151.15376282]])+O
# The first two hits are below the earlier tree replacement's fixed lower Z.
# Bound the correction to this actually modeled platform, near the observed hits.
mask=MultiPoint(hits).convex_hull.buffer(.45).intersection(platform)
protected=[]
for layer,ids,radius in [('haltestellen_sipf',[25],.60),('haltestellen_infosystem',[417],.65)]:
 fs=json.loads((R/'sources/features/vbz'/f'{layer}.geojson').read_text())['features']
 for f in fs:
  if int(f['id'].split('.')[-1]) in ids:
   guard=shape(f['geometry']).buffer(radius);mask=mask.difference(guard);protected.append(f['id'])
assert mask.area>1 and mask.area<12
rec={'observed_context':'CTX_I3S_34280','observed_camera':'BE_QA_CORNER_FIXTURES','hit_xy_lv95':hits.tolist(),'mask_lv95':mapping(mask),'area_m2':mask.area,'protected_unbuilt_devices':protected,'basis':'Actual same-camera rays intersect low green fragments and vertical photographic smear at previously rebuilt AV459; source originals retained. Detailed identity of smear is uncertain.','lower_ln02':408.25,'upper_ln02':412.20}
(D/'corner_fragment_cleanup_basis.json').write_text(json.dumps(rec,indent=2))
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':rec['lower_ln02'],'CUT_UPPER':rec['upper_ln02'],'CUT_BASE':'west_end_fixture_photo_cut.json','CUT_OUTPUT':'corner_fragment_cleanup.json','CUT_STATS_KEY':'corner_fragment_cleanup','CUT_DESCRIPTION':f'Observed CTX_I3S34280 fragments within {mask.area:.3f}m2 already rebuilt AV459, LN02408.25..412.20. Preserve SIPF25 and info417 guards; see corner_fragment_cleanup_basis.json. No source deletion.'})
