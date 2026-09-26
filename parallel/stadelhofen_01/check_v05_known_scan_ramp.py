"""Negative control: the new contact test must reject the saved v05 ramp."""
import sys, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
from check_geometry import bvh
from check_left_interface import check
assert bpy.context.scene['sf1_version']=='SF1_v05'
before=sha(bpy.data.filepath)
r=check(bpy.data.collections[D['import_collection']],bvh)
assert r['applicable'] and not r['passed'], 'Known v05 visible ramp was not detected.'
assert any(not s['passed'] for s in r['samples']), 'Missing v06 wall is not sufficient to establish the old ground defect.'
r.update(process_id=os.getpid(),native=bpy.data.filepath,native_sha256=before,
    expected_failure_detected=True,saved=False)
write('evidence/v05/known_scan_ramp_detected.json',r)
assert sha(bpy.data.filepath)==before
print('V05_RAMP_DETECTED',sum(not s['passed'] for s in r['samples']),'of',len(r['samples']),flush=True)
