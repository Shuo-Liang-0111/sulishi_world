"""Own equipment positions, grounded in AV3573; reuse reviewed fabrication only."""
from pathlib import Path
import json,runpy,numpy as np,hashlib
from shapely.geometry import shape,Point,LineString
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_context';data=json.loads((D/'ground_support.json').read_text(encoding='utf-8'));p=json.loads((D/'platform_input.json').read_text(encoding='utf-8'));O=np.array(data['origin']);tt=np.array(p['parts']['asphalt']+p['parts']['curb_top']);centres=tt[:,:,:2].mean(1)
def feature(ident):return next(f for f in data['facilities'] if f['id']==ident)
def ground(f):
 xy=np.array(shape(f['geometry']).centroid.coords[0])-O[:2]
 for idx in np.argsort(np.linalg.norm(centres-xy,axis=1))[:80]:
  t=tt[idx];A=(t[1:,:2]-t[0,:2]).T
  if abs(np.linalg.det(A))<1e-11:continue
  w=np.linalg.solve(A,xy-t[0,:2])
  if min(w)>-1e-6 and sum(w)<1.000001:return float(t[0,2]+w@(t[1:,2]-t[0,2]))
 raise ValueError(f['id'])
mast=feature('fahrleitungen_mast.1799');info=feature('haltestellen_infosystem.2864');bin=feature('haltestellen_papierkorb.631')
runpy.run_path(str(R/'tools/prepare_bellevue_corner_fixtures.py'),init_globals={'FIXTURE_CONFIG':{'out_dir':'derived/bellevue/south_context/info','platform_id':3573,'mast_id':1799,'info_ids':[2864,2581],'mast_ground_local':ground(mast),'info_ground_local':ground(info),'orientation_signs':[1,-1],'cut_lower':408.15,'cut_base':'south_tree_68441_photo_cut.json','cut_output':'south_corner_fixture_photo_cut.json'}})
dfi=feature('haltestellen_dfi_anzeiger.67');mast2=feature('fahrleitungen_mast.4217');i=json.loads((D/'info/input.json').read_text());i['ground_basis']='Triangle interpolation of reconstructed AV3573 asphalt/curb, source-supported grade with road-edge joins';(D/'info/input.json').write_text(json.dumps(i,indent=2));c=np.array(shape(info['geometry']).centroid.coords[0]);frame=unary_union([LineString([c,c+np.array(i['u'])*.70]).buffer(.035),LineString([c,c+np.array(i['v'])*.70]).buffer(.035)]);assert frame.distance(shape(bin['geometry']))>.35
new={'mast2':{'source':mast2,'ground_local':ground(mast2)},'dfi':{'source':dfi,'ground_local':ground(dfi)},'bin':{'source':bin,'ground_local':ground(bin),'basis':'Source type Papierkorb Haifisch. Inferred110L variant using ANTA110L drawing1.089m high/0.450m diameter/0.261x0.110m aperture; local installed size and ashtray option not established.'},'info_bin_min_distance_m':frame.distance(shape(bin['geometry']))}
(D/'fixtures_input.json').write_text(json.dumps(new,indent=2))
mask=unary_union([shape(f['geometry']).buffer(r) for f,r in [(mast2,.80),(dfi,.90),(bin,.58)]])
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':408.15,'CUT_UPPER':422.7,'CUT_BASE':'south_corner_fixture_photo_cut.json','CUT_OUTPUT':'south_fixtures_photo_cut.json','CUT_STATS_KEY':'south_fixtures','CUT_DESCRIPTION':'Replace guarded source mast4217/DFI67/bin631 volumes with own grounded physical entities; radii0.80/0.90/0.58m. Original source retained, device fine geometry inferred. Main mast1799 and info2864+2581 replaced by preceding cut.'})
ref=R/'sources/references/street_furniture/Abfallhai_110l_manufacturer.pdf';(ref.parent/'Abfallhai_receipt.json').write_text(json.dumps({'drawing_url':'https://onlineshop.antaswiss.ch/daten/bilder/Technische_zeichnungen/Abfallhai%20110%20liter/AH-C110-00001%20Abfallhai%20110l.pdf','product_page':'https://onlineshop.antaswiss.ch/de/artikel/AH-C110-00001','sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'use':'Technical dimensions and visible construction reference only, not redistributed material texture; actual110L installed variant not confirmed.','page_actually_inspected':1},indent=2))
print(json.dumps({'ground':{k:new[k]['ground_local'] for k in ['mast2','dfi','bin']},'info_bin_clearance_m':new['info_bin_min_distance_m']}))
