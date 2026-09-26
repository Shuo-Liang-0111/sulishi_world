import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
from check_geometry import bvh
from check_returns import check
assert bpy.context.scene.get('sf1_version')=='SF1_v03'
r=check(bpy.data.collections[D['import_collection']],bvh)
assert not r['passed']
r['process_id']=os.getpid();r['known_visual_defect_detected']=True
write('evidence/v03/known_return_gap_detection.json',r)
print('SF1_V03_RETURN_GAP_DETECTED',sum(not x['blocked_gap'] for x in r['samples']),flush=True)
