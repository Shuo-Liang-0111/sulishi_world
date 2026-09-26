"""Negative control for the visible v06 wall-foot/plinth corner joint."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
from check_geometry import bvh
from check_left_interface import wall_join_check
assert bpy.context.scene['sf1_version']=='SF1_v06'
before=sha(bpy.data.filepath)
r=wall_join_check(bpy.data.collections[D['import_collection']],bvh)
assert not r['passed']
r.update(process_id=os.getpid(),native=bpy.data.filepath,native_sha256=before,
    expected_failure_detected=True,saved=False)
write('evidence/v06/known_wall_foot_join_gap.json',r)
assert sha(bpy.data.filepath)==before
print('V06_WALL_FOOT_JOIN_GAP',sum(not s['passed'] for s in r['samples']),'of',len(r['samples']),flush=True)
