"""Three source-located trees adjoining the service building; bounded photo repair."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import Point,Polygon,shape,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_service';ctx=json.loads((R/'derived/bellevue/south_context/ground_support.json').read_text(encoding='utf-8'));p=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text(encoding='utf-8'));basis=json.loads((R/'derived/bellevue/south_context/photo_cut_basis.json').read_text());g=json.loads((D/'build_input.json').read_text())
built={'fahrleitungen_mast.1799','fahrleitungen_mast.4217','haltestellen_dfi_anzeiger.67','haltestellen_papierkorb.631','haltestellen_infosystem.2864','haltestellen_infosystem.2581'}|{f['id'] for f in g['facilities']}
guards=unary_union([shape(x['geometry']) for x in basis['protected_records'] if x['id'] not in built]);base='south_service_photo_cut.json';records=[];trees=[]
for ident,girth,radii,radius in [(138633,.80,[6.8,6.3],9.0),(64381,.78,[7.1,6.4],9.5),(139162,.74,[6.7,6.2],9.0)]:
 pit=next(x for x in p['pits'] if x['source']['properties']['objectid']==ident);t=pit['source'];c=np.array(t['geometry']['coordinates']);z=pit['soil_z_local']+400;h=t['properties']['hoehe'];area=Point(c).buffer(radius,quad_segs=80)
 for other in ctx['trees']:
  if other['properties']['objectid']==ident:continue
  q=np.array(other['geometry']['coordinates']);n=q-c;n/=np.linalg.norm(n);mid=(q+c)/2;v=np.array([-n[1],n[0]]);area=area.intersection(Polygon([mid+v*500,mid-v*500,mid-v*500-n*500,mid+v*500-n*500]))
 area=area.difference(guards);out=f'service_tree_{ident}_photo_cut.json'
 runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':area,'CUT_LOWER':z+.01,'CUT_UPPER':z+h+1,'CUT_BASE':base,'CUT_OUTPUT':out,'CUT_STATS_KEY':'service_trees','CUT_DESCRIPTION':f'Replace source tree{ident} photo volume radius{radius}m, clipped at neighboring-tree bisectors, soil+0.01 toinventoryheight+1; protect unbuilt facilities. Building and nine integral fixtures are already physically rebuilt, source originals retained. Root/crown form inferred.'});base=out
 trees.append({'source':t,'ground_ln02_m':z,'height_m':h,'origin':ctx['origin'],'inferred':{'seed':ident,'trunk_diameter_m':girth,'crown_radius_m':radii,'branch_clearance_m':4.2},'basis':'Official inventory XY, species and height; roots enter reconstructed AV soil. Crown, branching, girth and bark are individually seeded inferences, not tree-specific scan.'});records.append({'source_id':t['id'],'geometry_lv95':mapping(area),'lower_ln02':z+.01,'upper_ln02':z+h+1})
(D/'trees_input.json').write_text(json.dumps({'trees':trees,'cut_records':records,'source_cut_file':'derived/bellevue/west_context/'+base},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'trees':[t['source']['id'] for t in trees],'final_cut':base}))
