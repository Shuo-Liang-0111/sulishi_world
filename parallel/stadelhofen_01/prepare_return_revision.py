"""v04 closes the visually observed side return and adds visible side ground edges."""
from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parent;path=P/'derived/build_input.json';d=json.loads(path.read_text())
assert d['version'] in ['SF1_v03','SF1_v04']
ns={'__file__':str(P/'prepare_seam_repair.py')}
exec((P/'prepare_seam_repair.py').read_text().split('polys=')[0],ns)
d['ground_edge_profiles']=[p for p in d['ground_edge_profiles'] if not str(p['edge']).startswith('plinth_side_')]
for label,a,b in [('plinth_side_left',[-1.3,.25],[-1.3,1.54]),('plinth_side_right',[13.25,1.54],[13.25,.25])]:
    a=np.array(a);b=np.array(b);rows=[]
    for t in np.linspace(0,1,25):
        uv=a+(b-a)*t;hs=ns['hits'](uv);assert hs,(label,uv)
        rows.append(dict(t=float(t),uv=uv.tolist(),z=hs[0]['z'],hits=hs))
    d['ground_edge_profiles'].append(dict(edge=label,a=a.tolist(),b=b.tolist(),samples=rows))
d['version']='SF1_v04';d['v04_return_revision_basis']='Actual v03 approach view exposed a depth gap between the recessed wing strips and the projecting pilasters. Add continuous masonry corner returns and wrapped cornices. Also match two 1.29m visible narrow paving edges alongside the plinths, using existing source-ground triangles. Same crop bounds, no scope extension.'
path.write_text(json.dumps(d,indent=2),encoding='utf-8')
print(d['version'],'profiles',len(d['ground_edge_profiles']),'samples',sum(len(e['samples']) for e in d['ground_edge_profiles']))
