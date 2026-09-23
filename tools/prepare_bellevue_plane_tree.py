"""One measured tree identity; preserve source facts separately from inferred morphology."""
import json,hashlib,runpy
from pathlib import Path
import numpy as np
from shapely.geometry import Point,mapping

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context'
source=ROOT/'sources/features/bauminventar.geojson'
tree=next(f for f in json.loads(source.read_text())['features'] if f['properties']['objectid']==69773)
xy=np.array(tree['geometry']['coordinates']);origin=np.array([2683775,1246700,400])
platform=json.loads((OUT/'platform_input.json').read_text());tt=np.array(platform['parts']['platform']);local=xy-origin[:2]
# Sample adjacent actual platform around the tree pit, then the existing soil surface.
soil=np.array(platform['parts'].get('tree_soil',[]))
parts=list(platform['parts']);ground=None
for key in parts:
 if 'soil' not in key.lower():continue
 for t in np.array(platform['parts'][key]):
  A=(t[1:,:2]-t[0,:2]).T
  if abs(np.linalg.det(A))<1e-10:continue
  w=np.linalg.solve(A,local-t[0,:2])
  if min(w)>-1e-6 and sum(w)<1.000001:ground=float(t[0,2]+w@(t[1:,2]-t[0,2])+400)
assert ground is not None,'A tree must have an existing support surface, not a guessed constant Z.'
rec={'id':tree['id'],'source':tree,'source_file':str(source.relative_to(ROOT)),
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'origin':origin.tolist(),
 'ground_ln02_m':ground,'ground_basis':'Existing AV459 reconstructed soil surface, itself photography-supported inference',
 'height_m':tree['properties']['hoehe'],'height_epoch':tree['properties']['datenstand'],
 'inferred':{'trunk_diameter_m':.58,'crown_radius_m':[4.8,4.15],'branch_clearance_m':4.3,'seed':69773,
 'note':'Editable inferred branch architecture and summer foliage. Height/species/XY are source records; diameter, crown and every branch are not individual measurements.'},
 'references':['https://data.stadt-zuerich.ch/dataset/geo_bauminventar',
 'https://www.stadt-zuerich.ch/misc/de/mitteilungsarchiv/medienmitteilungen/2014/02/140207b.html',
 'https://selectree.calpoly.edu/tree-detail/1099','sources/references/swissimage-bellevue-west.jpg'],
 'accepted':False}
(OUT/'tree_69773_input.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False))
# Volume is limited below and above. Existing canopy source is only a poor photo
# envelope; the real shelter roof and other original-source objects stay intact.
volumes=[('tree_69773_trunk_cut.json','platform_tip_photo_cut.json',Point(xy).buffer(1.45),ground+.08,ground+4.35),
         ('tree_69773_photo_cut.json','tree_69773_trunk_cut.json',Point(xy).buffer(5.5),max(412.50,ground+4.35),ground+14.0)]
receipts=[]
for dest,base,mask,lo,hi in volumes:
 runpy.run_path(str(ROOT/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
  'CUT_MASK':mask,'CUT_LOWER':lo,'CUT_UPPER':hi,'CUT_BASE':base,'CUT_OUTPUT':dest,'CUT_STATS_KEY':'tree_stats',
  'CUT_DESCRIPTION':f'Bounded replacement for surveyed Platanus 69773: {lo:.4f}<LN02<{hi:.4f}; radius {1.45 if "trunk" in dest else 5.5}m. Detailed morphology is inferred. Original source retained.'})
 receipts.append({'file':dest,'mask':mapping(mask),'lower_ln02':lo,'upper_ln02':hi})
(OUT/'tree_69773_cut_volumes.json').write_text(json.dumps(receipts,indent=2))
print(json.dumps({'id':rec['id'],'ground_ln02':ground,'height_m':rec['height_m'],'accepted':False}))
