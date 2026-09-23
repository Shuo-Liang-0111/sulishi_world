"""Prepare the remaining east-side pole, information frame and bin from existing data."""
from pathlib import Path
import json
import runpy
import hashlib
import numpy as np
from shapely.geometry import shape, Point, LineString
from shapely.ops import unary_union

R=Path(__file__).resolve().parents[1]
D=R/'derived/bellevue/south_context/east_facilities';D.mkdir(parents=True,exist_ok=True)
source=R/'derived/bellevue/south_context/ground_support.json'
data=json.loads(source.read_text())
platform=R/'derived/bellevue/south_context/platform_input.json'
p=json.loads(platform.read_text());origin=np.asarray(data['origin'])
triangles=np.asarray(p['parts']['asphalt']+p['parts']['curb_top'])
centres=triangles[:,:,:2].mean(axis=1)

def feature(ident):return next(f for f in data['facilities'] if f['id']==ident)
def ground(f):
    xy=np.asarray(shape(f['geometry']).centroid.coords[0])-origin[:2]
    for idx in np.argsort(np.linalg.norm(centres-xy,axis=1))[:100]:
        t=triangles[idx];matrix=(t[1:,:2]-t[0,:2]).T
        if abs(np.linalg.det(matrix))<1e-11:continue
        w=np.linalg.solve(matrix,xy-t[0,:2])
        if min(w)>-1e-6 and sum(w)<1.000001:
            return float(t[0,2]+w@(t[1:,2]-t[0,2]))
    raise ValueError('No real ground support: '+f['id'])

mast=feature('fahrleitungen_mast.4211')
info=feature('haltestellen_infosystem.2717')
bin_record=feature('haltestellen_papierkorb.1173')
runpy.run_path(str(R/'tools/prepare_bellevue_corner_fixtures.py'),init_globals={
    'FIXTURE_CONFIG':{
        'out_dir':'derived/bellevue/south_context/east_facilities/info',
        'platform_id':3573,'mast_id':4211,'info_ids':[2717,2580],
        'mast_ground_local':ground(mast),'info_ground_local':ground(info),
        'ground_basis':'Barycentric interpolation on existing source-supported AV3573 asphalt/curb. Confirm actual mesh contact in Blender.',
        'orientation_signs':[1,-1], 'cut_lower':408.15,
        'cut_base':'grove_canopy_65530_photo_cut.json',
        'cut_output':'south_east_info_photo_cut.json'}})
cfg=json.loads((D/'info/input.json').read_text())
c=np.asarray(shape(info['geometry']).centroid.coords[0])
frame=unary_union([LineString([c,c+np.asarray(cfg[a])*.7]).buffer(.035) for a in ['u','v']])
bin_clearance=frame.distance(shape(bin_record['geometry']))-.225
assert bin_clearance>.40
cut=R/'derived/bellevue/west_context/south_east_facilities_photo_cut.json'
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
    'CUT_MASK':shape(bin_record['geometry']).buffer(.58),'CUT_LOWER':408.15,'CUT_UPPER':410.05,
    'CUT_BASE':'south_east_info_photo_cut.json','CUT_OUTPUT':cut.name,
    'CUT_STATS_KEY':'south_east_bin_replacement',
    'CUT_DESCRIPTION':'Replace remaining source bin1173 guarded volume only, below LN02410.05m. Native3mm sheet shell follows reviewed Haifisch110L family, installed variant inferred. Fountain and unbuilt tactile feature protected.'})
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'platform_sha256':hashlib.sha256(platform.read_bytes()).hexdigest(),
    'origin':origin.tolist(),'mast':{'source':mast,'ground_local':ground(mast)},
    'information':cfg,'bin':{'source':bin_record,'ground_local':ground(bin_record)},
    'info_bin_clearance_m':bin_clearance,'cut_file':str(cut.relative_to(R)),
    'cut_sha256':hashlib.sha256(cut.read_bytes()).hexdigest(),
    'status':'prepared_only_not_built',
    'inferred':'Pole fabrication, shared tubular information family and110L bin variant; location and source bearing retained. New AV neighborhood map, not a replica of actual posted notices.'}
(D/'input.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'prepared':str(D),'ground':{key:report[key]['ground_local'] for key in ['mast','bin']},
                  'info_bin_clearance_m':bin_clearance,'built':False}))
