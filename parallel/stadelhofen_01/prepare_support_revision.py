"""v03 responds to actual independently reopened v02 support failures."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;path=P/'derived/build_input.json';d=json.loads(path.read_text())
assert d['version'] in ['SF1_v02','SF1_v03']
d['version']='SF1_v03';d['handrail_post_v']=[.8,2.04,2.96,3.42]
d['camera_uv']={'SF1_QA_CONTEXT':[7.,20.9]}
d['camera_ground_z']['SF1_QA_CONTEXT']=9.9713134765625
d['v03_support_revision_basis']='Independent v02 evaluated checks: lower-tread post base at v=2.84 straddled next riser; shift to v=2.96. Add flush 12mm mineral bedding under baseplates to fill the 3mm slab joints, separately check bedding overlap with actual paving before checking plate contact. Geometry manufacture remains inferred.'
d['camera_correction_basis']='PID4416 on actual v02 native: original context UV[7,21] landed on a steep scan triangle |Nz|=0.510. Shift only this context camera 0.10m toward the building to UV[7,20.9], actual near-horizontal ground Z=9.9713134766, |Nz|=0.999836. ENTRY and REVERSE remain unchanged.'
path.write_text(json.dumps(d,indent=2),encoding='utf-8')
print(d['version'],d['handrail_post_v'],d['camera_correction_basis'])
