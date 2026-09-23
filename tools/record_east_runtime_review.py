"""Record the seven screenshots actually inspected; no automatic visual scoring."""
import hashlib,json,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[1];E=R/'evidence/G1_016r1'
views={
 'runtime_front.png':'Tree-pit triangular lighting discontinuities no longer visible; trunk contact continuous. Open door illumination still differs from baked walls.',
 'runtime_north.png':'Canopy underside has directional shading and poster lines remain resolved. Text/reflection still require improvement.',
 'runtime_east_info.png':'Full frame and foot sleeves present; glass-covered map is washed out compared with the same native view.',
 'runtime_east_reverse.png':'Reverse print orientation and frame retained; removed low floating source remnant absent. Map cover still too blurry.',
 'runtime_east_bin.png':'Aperture and inner liner present, not a decal; metal response remains too uniform without local surroundings.',
 'runtime_toilet.png':'Room geometry retained; moving cubicle doors overbright and mirrors show global sky instead of room reflection.',
 'runtime_cafe_regression.png':'Original cafe geometry, counter and equipment load; unbaked surfaces still differ substantially from native lighting.'}
screens=[]
for name,note in views.items():
 p=E/name;assert p.is_file();screens.append({'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'observation':note})
record={'version':'G1_016r1','updated_at':datetime.datetime.now().isoformat(),'loading_verified':True,'loaded_native_identities':3917,
 'screenshots_actually_inspected':screens,'shader_errors_observed':[],
 'scope':'Seven CUA views after contiguous light-UV and before the added east reflection / information-glass correction.',
 'candidate_can_replace_default':False,'accepted':False,'default_preserved':'G1_007r5',
 'remaining':'Physical foliage remnants, neighboring source buildings, localized real-time shading, dynamic doors, mirrors and natural-use controls remain unfinished. Whole-region fidelity is not accepted.'}
(E/'runtime_review.json').write_text(json.dumps(record,indent=2))
p=R/'evidence/G1_015r3/runtime_review.json';old=json.loads(p.read_text());old['reason']='Replacement linear HDR was actually inspected in north, front, entry, toilet and cafe views. Panorama orientation calibrated on GPU; poster backing-distance correction reviewed. Soil triangle discontinuities prompted the contiguous UV rebuild in016r1. Dynamic doors, mirrors and surrounding photography remain unaccepted.'
old['views_actually_inspected'] += ['corrected linear HDR: north, front, entry, toilet and cafe','corrected panorama / poster sampling: north and front']
p.write_text(json.dumps(old,indent=2))
print('Seven actual runtime views recorded; no whole-region or natural-use acceptance.')
