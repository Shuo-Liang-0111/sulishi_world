"""Review several cameras from one fresh native load; never save that process.

The first view runs all original geometry/memory checks. Further views reuse the
same visible scene and original image buffers, with no construction mutations.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
from pathlib import Path
import hashlib
import json
import os
import runpy
import sys
import time
import bpy

root = WORKSPACE
sys.path.insert(0,str(root/'tools'))
from png_integrity import verify_png
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
assert len(args) >= 1 and len(args) == len(set(args))
scene = bpy.context.scene
version = scene['version']
assert version.startswith(('G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027'))
if version in ['G1_027r8','G1_027r9','G1_027r10']:
    assert args[0]!='SG_QA_DOOR_OPEN','Run the closed architectural checks/view first, then the operated-door comparison.'
native = Path(bpy.data.filepath)
validate_native(native)
for camera in args:
    assert bpy.data.objects[camera].type == 'CAMERA'
evidence = root/'evidence'/version
evidence.mkdir(parents=True,exist_ok=True)
stat = native.stat()
started = time.time()
saved_argv = sys.argv[:]
completed = []
try:
    sys.argv = saved_argv[:saved_argv.index('--')]+['--',args[0],'surface-check']
    runpy.run_path(str(root/'tools/render_native_checkpoint.py'),run_name='__main__')
    if version in ['G1_027r8','G1_027r9','G1_027r10']:
        door_check=evidence/'door_fresh_checks.json'
        assert door_check.is_file() and door_check.stat().st_mtime>=started,'Door main entry point did not execute in this fresh process'
        assert json.loads(door_check.read_text())['process_id']==os.getpid()
    if version in ['G1_027r9','G1_027r10']:
        ubs_check=evidence/'ubs_fresh_checks.json'
        assert ubs_check.is_file() and ubs_check.stat().st_mtime>=started
        assert json.loads(ubs_check.read_text())['process_id']==os.getpid()
    if version=='G1_027r10':
        nearfront_check=evidence/'nearfront_fresh_checks.json'
        assert nearfront_check.is_file() and nearfront_check.stat().st_mtime>=started
        assert json.loads(nearfront_check.read_text())['process_id']==os.getpid()
    visible_signature = sorted((ob.name,len(ob.data.vertices),len(ob.data.polygons)) for ob in scene.objects if ob.type=='MESH')
    for index,camera in enumerate(args):
        if index:
            assert scene['version'] == version
            assert sorted((ob.name,len(ob.data.vertices),len(ob.data.polygons)) for ob in scene.objects if ob.type=='MESH') == visible_signature
            if version in ['G1_027r8','G1_027r9','G1_027r10']:
                from blender_check_sternen_doors import set_door_fraction
                set_door_fraction(1. if camera=='SG_QA_DOOR_OPEN' else 0.)
            runpy.run_path(str(root/'tools/blender_render_bellevue.py'),init_globals={'REVIEW_CAMERA':camera,'REVIEW_DEVICE':'CPU','REVIEW_SAMPLES':24,'REVIEW_RESOLUTION':(1280,840)})
        path = evidence/f'{camera}.png'
        assert path.is_file() and path.stat().st_mtime >= started
        verified=verify_png(path,(scene.render.resolution_x*scene.render.resolution_percentage//100,
                                 scene.render.resolution_y*scene.render.resolution_percentage//100))
        completed.append({'camera':camera,'file':str(path.relative_to(root)),**verified,
                          'sternen_door_open_fraction':float(bpy.data.objects['SG_R8_RESTAURANT_DOOR_CONTROL']['open_fraction']) if version in ['G1_027r8','G1_027r9','G1_027r10'] else None})
        (write_path(evidence/'fresh_view_batch.json')).write_text(json.dumps({'version':version,'native':str(native),'camera_sequence':args,'completed':completed,'full_geometry_checks_before_first_render':True,'same_scene_without_construction_edits':True,'native_saved':False,'visual_acceptance':False},indent=2),encoding='utf-8')
        print('NATIVE_VIEW_COMPLETE',camera,flush=True)
finally:
    if version in ['G1_027r8','G1_027r9','G1_027r10']:
        from blender_check_sternen_doors import set_door_fraction
        set_door_fraction(0.)
    sys.argv = saved_argv
assert native.stat().st_size == stat.st_size and native.stat().st_mtime_ns == stat.st_mtime_ns
print('NATIVE_VIEW_BATCH_COMPLETE',version,flush=True)
