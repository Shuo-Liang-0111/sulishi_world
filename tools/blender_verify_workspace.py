"""Read the current checkpoint and run its existing checks from the active checkout.

This produces H-side evidence only. It does not save, simplify, relight or render
the city, and passing it is not visual or natural-use acceptance.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import os
import runpy
import time
import bpy
from workspace_paths import ROOT, CONFIG, validate_native, write_path

native = validate_native(bpy.data.filepath)
assert native == Path(CONFIG['working_native']).resolve()
scene = bpy.context.scene
assert scene['version'] == 'G1_027r2', 'Update the explicit version checks before reusing this migration receipt.'
assert Path(scene['project_root']).resolve() == ROOT
before = (native.stat().st_size, native.stat().st_mtime_ns)
checks = ['blender_check_utoquai_kiosk','blender_check_riviera_quay','blender_check_riviera_trees',
          'blender_check_quaibruecke','blender_check_quaibruecke_water','blender_check_bridgehead_bank',
          'blender_verify_bank_sharing','blender_check_bridgehead_portal','blender_check_bridge_deck',
          'blender_check_bridge_grade_refinement','blender_check_riviera_lower','blender_check_limmat_sidewalk']
completed=[]
start=time.time()
for name in checks:
    runpy.run_path(str(ROOT/'tools'/f'{name}.py'),run_name='__main__')
    completed.append(name)
    print('WORKSPACE_CHECK',name,flush=True)
assert before == (native.stat().st_size, native.stat().st_mtime_ns)
report = dict(workspace=str(ROOT),input_native=str(native),version=scene['version'],objects=len(scene.objects),
              completed=completed,seconds=time.time()-start,source_native_unchanged=True,
              project_root=scene['project_root'],temporary=os.environ.get('TEMP'),
              blender_user_config=os.environ.get('BLENDER_USER_CONFIG'),
              native_saved=False,visual_acceptance=False,natural_use_verified=False)
write_path('runtime/migration/native_reopen.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
