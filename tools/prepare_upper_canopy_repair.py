"""Release erroneous vertical ground-feature guards and remove identified crown scraps.

The ray evidence names existing replacement trees; no trees or street data are
moved. Original photography and all geometry below LN02 413.10 remain intact.
"""
from pathlib import Path
import json,runpy,hashlib
import numpy as np
from shapely.geometry import Point,Polygon,shape,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/canopy_continuity';D.mkdir(exist_ok=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());assert w['version']=='G1_016r1'
ctx=json.loads((R/'derived/bellevue/south_context/ground_support.json').read_text())
platform=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text())
inventory=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
roof_data=json.loads((R/'sources/features/bauten_dachmodell_3d.geojson').read_text())['features']
LOWER=413.10
def coordinates(value):
    if isinstance(value,list) and value and isinstance(value[0],(float,int)):yield value
    elif isinstance(value,list):
        for item in value:yield from coordinates(item)
roofs=[]
for f in roof_data:
    points=np.array(list(coordinates(f['geometry']['coordinates'])))
    if len(points) and points.shape[1]>=3 and points[:,2].max()>=LOWER-.2:
        polygon=shape(f['geometry'])
        if not polygon.is_valid:polygon=polygon.buffer(0)
        if not polygon.is_empty:roofs.append(polygon.buffer(.35))
roof_guard=unary_union(roofs)
base=Path(w['source_cut_file']).name;records=[]
for ident,radius in [(65530,13.0),(60694,12.25),(121245,11.5)]:
    tree=next(f for f in ctx['trees'] if f['properties']['objectid']==ident)
    c=np.asarray(tree['geometry']['coordinates']);area=Point(c).buffer(radius,quad_segs=80)
    for other in inventory:
        if other['properties']['objectid']==ident:continue
        q=np.asarray(other['geometry']['coordinates'])[:2]
        if np.linalg.norm(q-c)>2*radius:continue
        n=(q-c)/np.linalg.norm(q-c);mid=(q+c)/2;v=np.array([-n[1],n[0]])
        area=area.intersection(Polygon([mid+v*500,mid-v*500,mid-v*500-n*500,mid+v*500-n*500]))
    before=area.area;area=area.difference(roof_guard)
    pit=next(p for p in platform['pits'] if p['source']['properties']['objectid']==ident)
    upper=400+pit['soil_z_local']+tree['properties']['hoehe']+1
    out=f'continuous_upper_tree_{ident}_photo_cut.json'
    runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
        'CUT_MASK':area,'CUT_LOWER':LOWER,'CUT_UPPER':upper,'CUT_BASE':base,'CUT_OUTPUT':out,'CUT_STATS_KEY':'upper_canopy_continuity',
        'CUT_DESCRIPTION':f'G1_017: ray-identified scraps near already rebuilt tree{ident}; upper-only LN02 {LOWER}..{upper:.3f}, radius{radius}m partitioned by full nearby inventory, high surveyed roofs protected. Ground-feature guards do not extend into the air. Geometry below413.10m and original source files retained.'})
    records.append({'tree':ident,'radius_m':radius,'lower_ln02_m':LOWER,'upper_ln02_m':upper,'mask_lv95':mapping(area),'area_m2':area.area,'roof_guard_removed_m2':before-area.area})
    base=out
output={'base_version':w['version'],'base_cut':w['source_cut_file'],'source_cut_file':'derived/bellevue/west_context/'+base,
 'records':records,'ray_evidence':'evidence/G1_016r1/upper_photo_residual_rays.json',
 'kept_below_ln02_m':LOWER,'new_external_data':False,'authoring_geometry_changed':False,'accepted':False}
(D/'input.json').write_text(json.dumps(output,indent=2))
print(json.dumps({k:v for k,v in output.items() if k!='records'}))
