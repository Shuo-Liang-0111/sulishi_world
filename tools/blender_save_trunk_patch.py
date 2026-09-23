"""Check and persist the source-located tree surface batch without repacking."""
from pathlib import Path
import hashlib
import json
import runpy
import shutil
import bpy

root = Path('F:/MyWorld/ZurichWorld')
scene = bpy.context.scene
assert scene['version'] == 'G1_020r4'
native = root/'native/G1_020r4_tree_bark_working.blend'
assert not native.exists() and shutil.disk_usage(root).free > 350_000_000
evidence = root/'evidence/G1_020r4'
assert (evidence/'permanent_surface_images.json').is_file()
runpy.run_path(str(root/'tools/blender_check_utoquai_kiosk.py'))
runpy.run_path(str(root/'tools/blender_check_limmat_sidewalk.py'))
assert Path(bpy.path.abspath(bpy.data.libraries[0].filepath)).resolve() == root/'native/G1_020r2_utoquai_coating_working.blend'
scene['storage_variant_of'] = 'G1_020r2 with shared heavy geometry and subsequent local repairs'
bpy.ops.wm.save_as_mainfile(filepath=str(native), compress=True)
path = evidence/'bark_revision.json'
record = json.loads(path.read_text())
sources = ['blender_refine_plane_trunk_patch.py', 'create_plane_trunk_patch_atlas.py',
           'blender_preserve_packed_surface_images.py', 'blender_save_trunk_patch.py']
record.update(native_saved=True, native=str(native.relative_to(root)), native_bytes=native.stat().st_size,
              native_sha256=hashlib.file_digest(native.open('rb'), 'sha256').hexdigest(),
              source_code_sha256={name: hashlib.sha256((root/'tools'/name).read_bytes()).hexdigest() for name in sources})
path.write_text(json.dumps(record, indent=2), encoding='utf-8')
path = root/'runtime/station_road_working.json'
working = json.loads(path.read_text())
working.update(version=scene['version'], native=str(native), accepted=False, not_published=True,
               next='Review south approach and Platanus root at the same cameras; inspect a separate station tree. Shared geometry library020r2 remains required. Matching runtime export/use pending.')
path.write_text(json.dumps(working, indent=2), encoding='utf-8')
print('TRUNK_PATCH_SAVED', json.dumps({'native': str(native), 'bytes': native.stat().st_size}), flush=True)
