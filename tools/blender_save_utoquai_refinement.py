"""Save the checked020r1 candidate, retaining all earlier native checkpoints."""
from pathlib import Path
import hashlib
import json
import runpy
import shutil
import bpy

root=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_020r1'
native=root/'native/G1_020r1_utoquai_surfaces_working.blend'
component=root/'native/components/G1_020r1_utoquai_kiosk.blend'
assert not native.exists() and not component.exists()
assert shutil.disk_usage(root).free>1_500_000_000
evidence=root/'evidence/G1_020r1'
assert (evidence/'verified_image_dependencies.json').is_file()
runpy.run_path(str(root/'tools/blender_check_utoquai_kiosk.py'))
runpy.run_path(str(root/'tools/blender_check_limmat_sidewalk.py'))
image_paths={im.name:im.filepath for im in bpy.data.images}
bpy.data.libraries.write(str(component),{bpy.data.collections['32_UTOQUAI_RIVIERA_KIOSK']},path_remap='RELATIVE_ALL',compress=True)
assert image_paths=={im.name:im.filepath for im in bpy.data.images}
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
sources=['tools/blender_refine_utoquai_kiosk.py','tools/blender_complete_utoquai_roof.py','tools/prepare_utoquai_kiosk_refinement.py','tools/prepare_utoquai_roof_clearance.py','tools/blender_externalize_verified_images.py','tools/blender_check_utoquai_kiosk.py','tools/blender_save_utoquai_refinement.py']
path=evidence/'refinement.json';record=json.loads(path.read_text())
record.update(native_saved=True,native=str(native),native_bytes=native.stat().st_size,component=str(component),component_bytes=component.stat().st_size,source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources})
path.write_text(json.dumps(record,indent=2),encoding='utf-8')
path=root/'runtime/station_road_working.json';working=json.loads(path.read_text());cut=root/scene['photo_cut_file']
working.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],source_cut_sha256=hashlib.sha256(cut.read_bytes()).hexdigest(),accepted=False,not_published=True,next='Reopen020r1 and inspect same north/counter/staff/south-approach views. Bake matching surface maps before runtime export. Default007r5 and candidate018r3 unchanged.')
path.write_text(json.dumps(working,indent=2),encoding='utf-8')
print(json.dumps({'native':str(native),'native_bytes':native.stat().st_size,'component_bytes':component.stat().st_size,'image_paths_unchanged':True,'saved':True}))
