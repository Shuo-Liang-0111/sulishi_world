import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
from check_geometry import bvh
from check_foundations import check
assert bpy.context.scene.get('sf1_version')=='SF1_v04'
r=check(bpy.data.collections[D['import_collection']],bvh)
assert not r['passed'] and r['maximum_gap_m']>.01
r['process_id']=os.getpid();r['known_visual_defect_detected']=True
write('evidence/v04/known_foundation_gap_detection.json',r)
print('SF1_V04_FOUNDATION_GAP_DETECTED',r['maximum_gap_m'],len(r['samples']),flush=True)
