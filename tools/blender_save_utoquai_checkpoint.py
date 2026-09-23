"""Persist the completed G1_020 authoring batch after independent geometry checks."""
from pathlib import Path
import hashlib
import json
import runpy
import shutil
import bpy

root=Path('F:/MyWorld/ZurichWorld')
assert bpy.context.scene['version']=='G1_020'
native=root/'native/G1_020_utoquai_kiosk_working.blend'
assert not native.exists(),'Keep existing saved checkpoints intact'
assert shutil.disk_usage(root).free>2_000_000_000
runpy.run_path(str(root/'tools/blender_check_utoquai_kiosk.py'))
runpy.run_path(str(root/'tools/blender_check_limmat_sidewalk.py'))
components=root/'native/components';components.mkdir(exist_ok=True)
component=components/'G1_020_utoquai_kiosk.blend'
bpy.data.libraries.write(str(component),{bpy.data.collections['32_UTOQUAI_RIVIERA_KIOSK']},compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
path=root/'evidence/G1_020/construction.json';rec=json.loads(path.read_text())
rec.update(native=str(native),native_saved=True,component_library=str(component.relative_to(root)))
path.write_text(json.dumps(rec,indent=2),encoding='utf-8')
path=root/'runtime/station_road_working.json';working=json.loads(path.read_text())
cut=root/bpy.context.scene['photo_cut_file']
working.update(version='G1_020',native=str(native),source_cut_file=bpy.context.scene['photo_cut_file'],source_cut_sha256=hashlib.sha256(cut.read_bytes()).hexdigest(),accepted=False,not_published=True,next='Inspect actual counter, north, staff entrance and same south-approach views; revise material/construction defects. No matching export yet. Runtime018r3/default007r5 unchanged.')
path.write_text(json.dumps(working,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(native),'bytes':native.stat().st_size,'component_bytes':component.stat().st_size}))
