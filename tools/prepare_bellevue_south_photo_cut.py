"""Ground and two tree volumes; protect unbuilt infrastructure and building."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import shape,Point,Polygon,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_context';ctx=R/'derived/bellevue/west_context';d=json.loads((D/'ground_support.json').read_text(encoding='utf-8'));p=json.loads((D/'platform_input.json').read_text(encoding='utf-8'));g=shape(d['av']['geometry']);O=np.array(d['origin']);newids={68441,17167}
guards=[]
for f in d['facilities']:
 radius=.75 if 'infosystem' in f['id'] else .55
 guards.append({'id':f['id'],'geometry':mapping(shape(f['geometry']).buffer(radius))})
for f in json.loads((R/'sources/features/wvz_brunnen.geojson').read_text(encoding='utf-8'))['features']:
 if shape(f['geometry']).distance(g)<1:guards.append({'id':f['id'],'geometry':mapping(shape(f['geometry']).buffer(2.0))})
protect=unary_union([shape(x['geometry']) for x in guards]);treeguards=unary_union([Point(t['geometry']['coordinates']).buffer(1.0) for t in d['trees'] if t['properties']['objectid'] not in newids]);mask=g.difference(protect).difference(treeguards)
roof_features=[f for f in json.loads((R/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features'] if f['properties'].get('egid')==302040350 and f['properties'].get('type')=='RoofSurface'];assert roof_features
roof=unary_union([shape(f['geometry']) for f in roof_features]).buffer(.35)
heights=[]
def visit(a):
 if len(a)>=3 and isinstance(a[0],(float,int)):heights.append(a[2])
 else:
  for x in a:visit(x)
for f in roof_features:visit(f['geometry']['coordinates'])
split=max(heights)+.35
cuttool=R/'tools/prepare_bellevue_west_shelter_cut.py';runs=[]
def cut(mask,lo,hi,base,output,note):
 runpy.run_path(str(cuttool),init_globals={'CUT_MASK':mask,'CUT_LOWER':lo,'CUT_UPPER':hi,'CUT_BASE':base,'CUT_OUTPUT':output,'CUT_STATS_KEY':'south_replacement','CUT_DESCRIPTION':note})
 runs.append({'file':output,'lower':lo,'upper':hi,'geometry_lv95':mapping(mask),'basis':note})
cut(mask,407.55,408.95,'corner_fragment_cleanup.json','south_ground_photo_cut.json','Replace only rebuilt AV3573 ground slab LN02407.55..408.95, excluding all21 VBZ/fountain guard records and ten unrebuilt tree bases. Original source unchanged; building hole preserved. Actual footway grade separately inferred and checked.')
base='south_ground_photo_cut.json';trees=[]
for pit in p['pits']:
 ident=pit['source']['properties']['objectid']
 if ident not in newids:continue
 t=pit['source'];xy=np.array(t['geometry']['coordinates']);h=t['properties']['hoehe'];z=pit['soil_z_local']+400;radius=5.4 if ident==68441 else 6.5
 # Keep the real canopy/building even where source tree foliage overlaps it.
 low=Point(xy).buffer(radius,quad_segs=64).difference(protect).difference(roof)
 high=Point(xy).buffer(radius,quad_segs=64).difference(protect)
 n=f'south_tree_{ident}_low_cut.json';cut(low,z+.04,split,base,n,f'Tree{ident} lower replacement at actual inventory XY radius{radius}m; exclude unbuilt devices/fountain and entire official EGID302040350 roof plan+0.35m including overhangs, ground+0.04 toLN02{split:.3f}. Shape inferred; source intact.');base=n
 n=f'south_tree_{ident}_photo_cut.json';cut(high,split,z+h+1,base,n,f'Tree{ident} upper canopy replacement radius{radius}m above source roofmax+0.35=LN02{split:.3f} tosoil+height+1; source infrastructure guards retained.');base=n
 trees.append({'source':t,'ground_ln02_m':z,'height_m':h,'origin':d['origin'],'inferred':{'seed':ident,'trunk_diameter_m':.58 if ident==68441 else .86,'crown_radius_m':[radius-.35,radius-.65],'branch_clearance_m':3.7 if ident==68441 else 4.0},'basis':'Source tree XY/species and inventory height; supported by new AV3573 soil. Crown architecture, girth and surface detail inferred; not tree-specific scan.'})
(D/'tree_inputs.json').write_text(json.dumps({'trees':trees,'source_cut_file':str((ctx/base).relative_to(R))},indent=2,ensure_ascii=False),encoding='utf-8')
(D/'photo_cut_basis.json').write_text(json.dumps({'protected_records':guards,'cuts':runs,'accepted':False},indent=2))
print(json.dumps({'trees':[t['source']['id'] for t in trees],'protected_records':len(guards),'source_cut':base,'ground_cut_area_m2':mask.area}))
