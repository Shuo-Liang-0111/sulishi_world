"""The strengthened contact test must detect the visually observed v01 defect."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
from check_geometry import bvh
from check_supports import check
assert bpy.context.scene.get('sf1_version')=='SF1_v01'
C=bpy.data.collections[D['import_collection']]
ground=bvh([o for o in C.objects if o.get('sf1_role') in {'walk_surface','walk_support','step_support','step_surface','plinth'}])
r=check(C,ground,bvh)
assert not r['passed'] and any(p['actual_post_rail_intersecting_triangles']==0 for p in r['posts'])
r['known_observed_failure_detected']=True;r['process_id']=os.getpid()
write('evidence/v01/known_failure_contact_detection.json',r)
print('SF1_V01_OBSERVED_FAILURE_DETECTED',sum(p['actual_post_rail_intersecting_triangles']==0 for p in r['posts']),flush=True)
