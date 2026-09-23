"""Persist020r2 after a material-only correction observed in020r1 renders."""
from pathlib import Path
import hashlib
import json
import runpy
import shutil
import bpy

root=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_020r2'
native=root/'native/G1_020r2_utoquai_coating_working.blend'
component=root/'native/components/G1_020r2_utoquai_kiosk.blend'
assert not native.exists() and not component.exists()
assert shutil.disk_usage(root).free>1_500_000_000
runpy.run_path(str(root/'tools/blender_check_utoquai_kiosk.py'))
runpy.run_path(str(root/'tools/blender_check_limmat_sidewalk.py'))
dependencies=root/'evidence/G1_020r1/verified_image_dependencies.json';assert dependencies.is_file()
bpy.data.libraries.write(str(component),{bpy.data.collections['32_UTOQUAI_RIVIERA_KIOSK']},path_remap='RELATIVE_ALL',compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
path=root/'evidence/G1_020r2/coating_repair.json';record=json.loads(path.read_text())
sources=['tools/blender_refine_utoquai_coating.py','tools/blender_check_utoquai_kiosk.py','tools/blender_save_utoquai_coating.py']
record.update(native_saved=True,native=str(native),native_bytes=native.stat().st_size,component=str(component),component_bytes=component.stat().st_size,image_dependencies_inherited_from=str(dependencies.relative_to(root)),source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources})
path.write_text(json.dumps(record,indent=2),encoding='utf-8')
path=root/'runtime/station_road_working.json';working=json.loads(path.read_text())
working.update(version=scene['version'],native=str(native),accepted=False,not_published=True,next='Check new same-camera coating renders, especially staff-door interior vs exterior. Preserve020r1 geometry and source cut. Matching runtime material baking/export and natural use pending.')
path.write_text(json.dumps(working,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(native),'bytes':native.stat().st_size,'component_bytes':component.stat().st_size}))
