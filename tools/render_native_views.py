"""Review several cameras from one fresh native load; never save that process.

The first view runs all original geometry/memory checks. Further views reuse the
same visible scene and original image buffers, with no construction mutations.
"""
from pathlib import Path
import hashlib
import json
import runpy
import sys
import time
import bpy

root = Path('F:/MyWorld/ZurichWorld')
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
assert len(args) >= 1 and len(args) == len(set(args))
scene = bpy.context.scene
version = scene['version']
assert version.startswith(('G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027'))
native = Path(bpy.data.filepath)
assert native.resolve().parent == root/'native'
for camera in args:
    assert bpy.data.objects[camera].type == 'CAMERA'
evidence = root/'evidence'/version
evidence.mkdir(exist_ok=True)
stat = native.stat()
started = time.time()
saved_argv = sys.argv[:]
completed = []
try:
    sys.argv = saved_argv[:saved_argv.index('--')]+['--',args[0],'surface-check']
    runpy.run_path(str(root/'tools/render_native_checkpoint.py'),run_name='__main__')
    visible_signature = sorted((ob.name,len(ob.data.vertices),len(ob.data.polygons)) for ob in scene.objects if ob.type=='MESH')
    for index,camera in enumerate(args):
        if index:
            assert scene['version'] == version
            assert sorted((ob.name,len(ob.data.vertices),len(ob.data.polygons)) for ob in scene.objects if ob.type=='MESH') == visible_signature
            runpy.run_path(str(root/'tools/blender_render_bellevue.py'),init_globals={'REVIEW_CAMERA':camera,'REVIEW_DEVICE':'CPU','REVIEW_SAMPLES':24,'REVIEW_RESOLUTION':(1280,840)})
        path = evidence/f'{camera}.png'
        assert path.is_file() and path.stat().st_mtime >= started
        completed.append({'camera':camera,'file':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        (evidence/'fresh_view_batch.json').write_text(json.dumps({'version':version,'native':str(native),'camera_sequence':args,'completed':completed,'full_geometry_checks_before_first_render':True,'same_scene_without_construction_edits':True,'native_saved':False,'visual_acceptance':False},indent=2),encoding='utf-8')
        print('NATIVE_VIEW_COMPLETE',camera,flush=True)
finally:
    sys.argv = saved_argv
assert native.stat().st_size == stat.st_size and native.stat().st_mtime_ns == stat.st_mtime_ns
print('NATIVE_VIEW_BATCH_COMPLETE',version,flush=True)
