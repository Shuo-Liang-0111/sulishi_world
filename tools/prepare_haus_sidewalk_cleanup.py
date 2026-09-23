"""Remove near-sidewalk photo folds where the ground/facade will now be solid."""
from pathlib import Path
import json,runpy
from shapely.geometry import shape,Point
R=Path(__file__).resolve().parents[1];d=json.loads((R/'derived/haus_bellevue/context.json').read_text());g=shape(d['sidewalk']['geometry']);tree=shape(d['trees'][0]['geometry'])
mask=g.difference(tree.buffer(4.8))
base='haus_frontage_r1_photo_cut.json';dest='haus_walk_clear_photo_cut.json'
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_UPPER':413.34,'CUT_LOWER':408.0,'CUT_BASE':base,'CUT_OUTPUT':dest,'CUT_STATS_KEY':'haus_walk_clear','CUT_DESCRIPTION':'Authored AV35946 sidewalk and reconstructed frontage replace sagging awning/photo vertical remnants below413.34m; a4.8m radius around unrebuilt tree119962 remains untouched. VBZ mast1794 is replaced separately at its measured point and top.'})
src=R/'sources/features/vbz/fahrleitungen_mast.geojson';mast=next(f for f in json.loads(src.read_text())['features'] if f['properties']['objectid']==1794);p=shape(mast['geometry']).geoms[0]
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':p.buffer(.8),'CUT_UPPER':421.,'CUT_LOWER':408.,'CUT_BASE':dest,'CUT_OUTPUT':'haus_walk_mast_photo_cut.json','CUT_STATS_KEY':'haus_mast','CUT_DESCRIPTION':'Replace distorted mast1794 photo volume radius0.8m at official VBZ XY; measured top420.2m, base408.22m are recorded; taper and metal finish inferred.'})
(R/'derived/haus_bellevue/mast1794.json').write_text(json.dumps(mast,indent=2))
