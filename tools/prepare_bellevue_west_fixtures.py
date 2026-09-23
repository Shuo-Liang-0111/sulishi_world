"""Preserve facility identities and distinguish measured locations from inferred fabrication."""
import json, hashlib, math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'derived/bellevue/west_context'
ORIGIN=np.array([2683775,1246700])
selected={
    'haltestellen_plakatstelle':[283,586,587],
    'haltestellen_sitzgelegenheit':[544],
    'haltestellen_dfi_anzeiger':[64],
    'haltestellen_ticketautomat':[574],
}
features={};sources=[]
for layer,ids in selected.items():
    p=ROOT/'sources/features/vbz'/f'{layer}.geojson'
    j=json.loads(p.read_text(encoding='utf-8'))
    features[layer]=[f for f in j['features'] if f['properties']['objectid'] in ids]
    assert len(features[layer])==len(ids)
    sources.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
ads=sorted(features['haltestellen_plakatstelle'],key=lambda f:f['geometry']['coordinates'][0][0])
xy=np.array([f['geometry']['coordinates'][0] for f in ads]);delta=xy[-1]-xy[0]
axis=delta/np.linalg.norm(delta);normal=np.array([-axis[1],axis[0]])
bear=math.degrees(math.atan2(axis[0],axis[1]))%180
orient=float(ads[0]['properties']['orientierung'])%180
bench=features['haltestellen_sitzgelegenheit'][0]
assert np.linalg.norm(np.array(bench['geometry']['coordinates'][0])-xy[1])<1e-5
ticket=features['haltestellen_ticketautomat'][0]
txy=np.array(ticket['geometry']['coordinates'][0][0])[:4,:2]
edges=np.roll(txy,-1,axis=0)-txy;lengths=np.linalg.norm(edges,axis=1);long=edges[np.argmax(lengths)]/max(lengths)
# The operating face is the SE-facing side, toward the shelter's clear waiting area.
if long[1]<0:long=-long
tnormal=np.array([-long[1],long[0]])
dfi=features['haltestellen_dfi_anzeiger'][0];dxy=np.array(dfi['geometry']['coordinates'][0]);theta=math.radians(float(dfi['properties']['orientierung']))
result={
    'source_files':sources,'features':features,
    'ad_row':{'centres_lv95':xy.tolist(),'ids':[f['id'] for f in ads],'axis':axis.tolist(),'rear_normal':normal.tolist(),
              'centre_spacing_m':np.linalg.norm(np.diff(xy,axis=0),axis=1).tolist(),
              'bearing_deg_from_north_mod180':bear,'orientation_field_mod180':orient,'bearing_difference_deg':abs(bear-orient),
              'orientation_basis':'Inferred clockwise degrees from north, checked against three collinear ad points; geocat attribute definition is empty. Do not treat convention as officially documented.',
              'panel_outer_width_m_inferred':1.195,'panel_outer_height_m_inferred':1.78,'panel_bottom_above_platform_m_inferred':.40,
              'poster_format_basis':'APG F200 paper 116.5 x 170 cm; inferred installed format, not a verified subtype. Case and glass dimensions are inferred.',
              'artwork_basis':'New neutral typographic urban-life poster designs, not observed advertisements and not a dated historical reproduction.'},
    'bench':{'source_id':bench['id'],'source_point_lv95':xy[1].tolist(),'axis':axis.tolist(),
             'seat_length_m_inferred':3.46,'seat_center_offset_toward_track_m_inferred':.40,
             'basis':'Recorded Bank in WH lang point coincides exactly with central ad point. Treat it as assembly anchor; seat offset/fabrication remain inference, not independent surveyed position. Standard 2m standalone VBZ bench drawing is not silently substituted.'},
    'ticket':{'source_id':ticket['id'],'center_lv95':txy.mean(axis=0).tolist(),'axis':long.tolist(),'rear_normal':tnormal.tolist(),
              'source_width_m':float(max(lengths)),'source_depth_m':float(min(lengths)),
              'basis':'Exact source polygon preserved, but source location quality unknown and epoch unspecified. ZVV 2023 photo constrains blue control face and gray casing. Height, supports, details and face direction inferred. Installation drawing is a generic foundation reference, not proof of Typ20 body dimensions.'},
    'dfi':{'source_id':dfi['id'],'source_point_lv95':dxy.tolist(),'axis_toward_track':[math.sin(theta),math.cos(theta)],
           'mast_width_m':.13,'case_width_m_inferred':1.25,'case_height_m_inferred':.57,'case_bottom_m_inferred':2.48,
           'basis':'Official Info Smart point and orientation; mast 0.13m from VBZ drawing 4540-980-460. Case, bracket, top height inferred. No current departures or operational service claimed.'},
    'references':['sources/references/bellevue_shelters/VBZ_Montagekatalog_2016.pdf',
                  'sources/references/bellevue_shelters/Immobilia_2016_05.pdf',
                  'sources/references/bellevue_shelters/APG_Poster_production_2021.pdf',
                  'sources/references/bellevue_shelters/ZVV_ticket_2023.jpg'],
    'accepted':False,
}
(OUT/'fixtures_input.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ad_spacing':result['ad_row']['centre_spacing_m'],'bearing_difference_deg':abs(bear-orient),'ticket_dims_m':[max(lengths),min(lengths)],'accepted':False}))
