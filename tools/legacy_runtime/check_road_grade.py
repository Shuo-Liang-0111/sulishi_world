import json
from pathlib import Path
p=Path('derived/bellevue/transport/road_input.json');j=json.loads(p.read_text());import numpy as np
for part in j['pieces']:
 if part['kind']!='road_asphalt':continue
 t=np.array(part['triangles']);cr=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);sl=np.linalg.norm(cr[:,:2],axis=1)/np.maximum(abs(cr[:,2]),1e-12)
 print(part['id'],len(t),'slope p95/max',np.quantile(sl,[.95,1]).tolist())
