"""Evidence-reviewed tree-remnant envelopes, bounded by neighboring identities."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import Point,Polygon,shape,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_context';d=json.loads((D/'ground_support.json').read_text(encoding='utf-8'));td=json.loads((D/'tree_inputs.json').read_text(encoding='utf-8'));basis=json.loads((D/'photo_cut_basis.json').read_text())
built={'fahrleitungen_mast.1799','fahrleitungen_mast.4217','haltestellen_dfi_anzeiger.67','haltestellen_papierkorb.631','haltestellen_infosystem.2864','haltestellen_infosystem.2581'}
guards=unary_union([shape(x['geometry']) for x in basis['protected_records'] if x['id'] not in built])
roof=unary_union([shape(f['geometry']) for f in json.loads((R/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features'] if f['properties'].get('egid')==302040350 and f['properties'].get('type')=='RoofSurface']).buffer(.35)
base='south_fixtures_photo_cut.json';records=[]
for t in td['trees']:
 ident=t['source']['properties']['objectid'];c=np.array(t['source']['geometry']['coordinates']);radius=9.2 if ident==17167 else 8.2;area=Point(c).buffer(radius,quad_segs=80)
 # Partition the existing tree field: never erase a neighboring trunk/crown core.
 for other in d['trees']:
  if other['properties']['objectid']==ident:continue
  q=np.array(other['geometry']['coordinates']);n=q-c;n=n/np.linalg.norm(n);mid=(q+c)/2;v=np.array([-n[1],n[0]])
  half=Polygon([mid+v*500,mid-v*500,mid-v*500-n*500,mid+v*500-n*500]);area=area.intersection(half)
 for part,lo,hi,mask in [('low',409.15,413.13,area.difference(guards).difference(roof)),('high',413.13,t['ground_ln02_m']+t['height_m']+1,area.difference(guards))]:
  output=f'south_tree_{ident}_{part}_refined_cut.json'
  runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':lo,'CUT_UPPER':hi,'CUT_BASE':base,'CUT_OUTPUT':output,'CUT_STATS_KEY':'canopy_refinement','CUT_DESCRIPTION':f'Observed tree{ident} residual-sheet cleanup: radius{radius}m envelope bounded by nearest inventory-tree bisectors; LN02{lo:.3f}..{hi:.3f}. Unbuilt devices protected; full roof+0.35m protected below413.13. Built equipment no longer requires photographic guard columns. Source untouched.'});base=output
  records.append({'tree_id':ident,'part':part,'lower':lo,'upper':hi,'geometry_lv95':mapping(mask),'area_m2':mask.area})
(D/'canopy_refinement.json').write_text(json.dumps({'records':records,'cut_file':'derived/bellevue/west_context/'+base,'crown_xy_scale':{'17167':[1.28,1.25],'68441':[1.34,1.30]},'basis':'Expanded individual crown envelope inferred from existing SWISSIMAGE and actual rendered remnants; positions/heights unchanged. Neighbor bisectors are construction masks, not surveyed crown outlines.','accepted':False},indent=2))
# Repair provenance text without rerunning unrelated geometry preparation.
p=D/'info/input.json';i=json.loads(p.read_text());i['ground_basis']='Triangle interpolation of reconstructed AV3573 asphalt/curb, source-supported grade with road-edge joins';p.write_text(json.dumps(i,indent=2))
print(json.dumps({'final_cut':base,'areas':[r['area_m2'] for r in records]}))
