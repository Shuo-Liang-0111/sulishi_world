"""v07 joins the new wall foot underneath the existing author return wall."""
from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parent;path=P/'derived/build_input.json'
d=json.loads(path.read_text());assert d['version']=='SF1_v06'
rows=d['left_wall_foot']['samples'];u0=rows[-1]['u'];v0=rows[-1]['top_front_v']
for u in np.linspace(u0,-.45,19)[1:]:
    t=float(np.clip((u-u0)/(-1.20-u0),0,1))
    rows.append(dict(u=float(u),top_front_v=v0+(-.668-v0)*t))
d['version']='SF1_v07'
d['v07_revision_basis']='Original approach view of v06 exposed the 77mm along-facade gap between the new wall foot ending at u=-1.29 and the measured plinth side at about -1.213. Extend the foot beneath the existing author return wall to u=-0.45. The top is recessed 8mm behind the existing stone face to avoid coincident surfaces. No crop, camera, ground, measured footprint or upper facade changes.'
path.write_text(json.dumps(d,indent=2),encoding='utf-8')
print(d['version'],'wall foot range',rows[0]['u'],rows[-1]['u'])
