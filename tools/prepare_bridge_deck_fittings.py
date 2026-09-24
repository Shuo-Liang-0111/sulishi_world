"""Explicit inferred attachment geometry for the source-positioned contact net."""
from pathlib import Path
import hashlib,json
import numpy as np
from shapely.geometry import LineString,Point

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_deck'
P=json.loads((D/'build_input.json').read_text())
spans=[p for p in P['pipes'] if p['name'].startswith('SPAN_')]
contacts=[p for p in P['pipes'] if p['name'].startswith('CONTACT_')]

def point_at(pipe,position):
    p=np.array(pipe['points']);length=np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1);s=np.r_[0,np.cumsum(length)]
    return np.array([np.interp(position,s,p[:,i]) for i in range(3)])

attachments=[];exits=[];seen=set()
for contact in contacts:
    for endpoint in [contact['points'][0],contact['points'][-1]]:
        key=tuple(round(q,4) for q in endpoint)
        if key in seen:continue
        seen.add(key)
        candidate=[]
        for span in spans:
            line=LineString(np.array(span['points'])[:,:2]);pt=Point(endpoint[:2])
            candidate.append((line.distance(pt),span,line.project(pt)))
        distance,span,position=min(candidate,key=lambda q:q[0])
        if distance>.25:
            exits.append(dict(contact=contact['name'],point=endpoint,nearest_span_distance_m=distance))
            continue
        high=point_at(span,position)
        assert .07<high[2]-endpoint[2]<.15
        attachments.append(dict(name='HANGER_'+str(len(attachments)),low=endpoint,high=high.tolist(),
                                 source=contact['source']+' / '+span['source'],lateral_correction_m=distance))
clamps=[];insulators=[]
for span in spans:
    pts=np.array(span['points']);length=LineString(pts[:,:2]).length
    for j,(position,along) in enumerate([(0,1),(length,-1)]):
        point=point_at(span,position);mast=min(P['masts'],key=lambda m:np.linalg.norm(np.array(m['xy'])-point[:2]))
        assert np.linalg.norm(np.array(mast['xy'])-point[:2])<.05
        assert mast['base_ln02_m']<point[2]<mast['top_ln02_m']
        clamps.append(dict(name=f"CLAMP_{span['name']}_{j}",point=point.tolist(),mast=mast['id']))
        insulators.append(dict(name=f"INSULATOR_{span['name']}_{j}",a=point_at(span,position+along*.45).tolist(),
                                b=point_at(span,position+along*.68).tolist(),source=span['source']))
result=dict(input_sha256=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest(),attachments=attachments,
            clamps=clamps,insulators=insulators,network_boundary_exits=exits,
            fabrication_inferred=True,complete_transport_network=False)
(D/'fittings.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(attachments=len(attachments),clamps=len(clamps),insulators=len(insulators),boundary_exits=len(exits))))
