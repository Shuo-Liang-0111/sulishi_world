"""Bounded repairs grounded in the actually inspected G1_015 east image."""
from pathlib import Path
import json,runpy
from collections import Counter
import numpy as np
from shapely.geometry import Point,Polygon,shape
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_remaining'
p=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text(encoding='utf-8'))
ctx=json.loads((R/'derived/bellevue/south_context/ground_support.json').read_text(encoding='utf-8'))
basis=json.loads((R/'derived/bellevue/south_context/photo_cut_basis.json').read_text())
data=json.loads((D/'trees_input.json').read_text(encoding='utf-8'))
guards=unary_union([shape(x['geometry']) for x in basis['protected_records'] if x['id'] in data['remaining_facility_guards']])
w=json.loads((R/'runtime/station_road_working.json').read_text());assert w['version']=='G1_015'
base=Path(w['source_cut_file']).name
for ident in [139162,65530]:
    t=next(x for x in ctx['trees'] if x['properties']['objectid']==ident)
    c=np.array(t['geometry']['coordinates']);area=Point(c).buffer(12.25,quad_segs=80)
    for other in ctx['trees']:
        if other['properties']['objectid']==ident:continue
        q=np.array(other['geometry']['coordinates']);n=(q-c)/np.linalg.norm(q-c);mid=(q+c)/2;v=np.array([-n[1],n[0]])
        area=area.intersection(Polygon([mid+v*500,mid-v*500,mid-v*500-n*500,mid+v*500-n*500]))
    area=area.difference(guards)
    pit=next(x for x in p['pits'] if x['source']['properties']['objectid']==ident)
    out=f'grove_canopy_{ident}_photo_cut.json'
    runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
        'CUT_MASK':area,'CUT_LOWER':413.10,'CUT_UPPER':400+pit['soil_z_local']+t['properties']['hoehe']+1,
        'CUT_BASE':base,'CUT_OUTPUT':out,'CUT_STATS_KEY':'grove_upper_residual',
        'CUT_DESCRIPTION':f'Actual east-view rays hit CTX33492 residual crown associated with already rebuilt tree{ident}. '
            'Upper-only replacement above roofmax+0.32m, radius12.25m, nearest-tree partition and unbuilt facility guards retained. No change to source originals.'})
    base=out

# The previous 32mm-deep pit surface had no exposed vertical asphalt edge. Close
# only this genuine gap using the exact float32 soil mesh boundary, keeping its
# opening, floor, roots and the official island boundary untouched.
soil=np.asarray(p['parts']['soil'],dtype=np.float32)
counts=Counter();directions={}
for tri in soil:
    for a,b in zip(tri,np.roll(tri,-1,axis=0)):
        aa,bb=tuple(float(x) for x in a),tuple(float(x) for x in b)
        key=tuple(sorted([aa,bb]));counts[key]+=1;directions[key]=(aa,bb)
rings=unary_union([shape(x['geometry_local']).boundary for x in p['pits']])
triangles=[];uv=[];length=0.;top_errors=[]
for key,count in counts.items():
    if count!=1:continue
    a,b=[np.array(x) for x in directions[key]]
    distance=np.linalg.norm(b[:2]-a[:2])
    if distance<1e-7 or rings.distance(Point((a[:2]+b[:2])/2))>3e-5:continue
    at=a+[0,0,.032];bt=b+[0,0,.032]
    triangles.extend([[b,a,at],[b,at,bt]])
    uv.extend([[[distance/2.05,0],[0,0],[0,.032/2.05]],[[distance/2.05,0],[0,.032/2.05],[distance/2.05,.032/2.05]]])
    length+=distance
assert abs(length-rings.length)<.002,(length,rings.length)
record={'source_cut_file':'derived/bellevue/west_context/'+base,
        'pit_edge_triangles':np.asarray(triangles).tolist(),'pit_edge_uv':uv,
        'pit_edge_length_m':length,'source_pit_perimeter_m':rings.length,'exposed_edge_height_m':.032,
        'basis':'Close missing vertical cut asphalt faces around existing inferred pits; all existing topography and pit openings unchanged. Upper photography repair is tied to recorded actual-image rays.'}
(D/'repairs_input.json').write_text(json.dumps(record,separators=(',',':')))
print(json.dumps({k:v for k,v in record.items() if k not in ['pit_edge_triangles','pit_edge_uv']}))
