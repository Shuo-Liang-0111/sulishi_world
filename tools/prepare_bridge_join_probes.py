"""Sample the actual prepared old/new seam, independent of its height blend."""
from pathlib import Path
import json
import numpy as np
from shapely.geometry import Polygon,shape,Point
from shapely.ops import unary_union,nearest_points
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_deck'
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
old=json.loads((D/'existing_approaches.json').read_text())
plan=unary_union([Polygon(np.array(t)[:,:2]+O[:2]) for row in old['surfaces'] for t in row['triangles']])
new=shape(P['surface']);border=new.boundary.intersection(plan.buffer(.0005))
def lines(g):
    if g.geom_type=='LineString':return [g]
    return [p for q in getattr(g,'geoms',[]) for p in lines(q)]
samples=[]
for line in lines(border):
    if line.length<.04:continue
    for pos in np.linspace(.015,line.length-.015,max(2,int(line.length/.7))):
        p=np.array(line.interpolate(pos).coords[0]);q=np.array(nearest_points(plan,Point(p))[0].coords[0]);v=p-q
        if np.linalg.norm(v)<1e-8:continue
        v/=np.linalg.norm(v);a=p+.03*v;b=p-.03*v
        if new.covers(Point(a)) and plan.covers(Point(b)):
            zone=next(z for z in P['zones'] if shape(z['geometry']).covers(Point(a)))
            matches=[r['object'] for r in old['surfaces'] if any(Polygon(np.array(t)[:,:2]+O[:2]).covers(Point(b)) for t in r['triangles'])]
            assert matches
            old_raised=not matches[0].startswith('BE_PAVING_')
            samples.append(dict(new_xy=(a-O[:2]).tolist(),old_xy=(b-O[:2]).tolist(),new_source=zone['id'],
                                new_raised=zone['raised'],old_raised=old_raised,old_object=matches[0]))
assert len(samples)>20,len(samples)
(D/'join_probes.json').write_text(json.dumps(dict(samples=samples,old_objects=[r['object'] for r in old['surfaces']]),indent=2),encoding='utf-8')
print('BRIDGE_JOIN_PROBES',len(samples))
