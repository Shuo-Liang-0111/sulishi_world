"""Save026 after construction checks; native is not a runtime publication."""
from pathlib import Path
import hashlib,json,runpy,shutil
import bpy

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_026' and Path(bpy.data.filepath).name=='G1_025r1_bank_tree_replacement_working.blend'
target=R/'native/G1_026_bridgehead_portal_working.blend';assert not target.exists()
assert shutil.disk_usage(R).free>500_000_000
for name in ['blender_check_quaibruecke.py','blender_check_quaibruecke_water.py','blender_check_bridgehead_bank.py',
             'blender_check_bridgehead_portal.py','blender_check_riviera_lower.py','blender_check_riviera_trees.py',
             'blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/name))
s.camera=bpy.data.objects['QB_QA_SOUTH'];bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=False)
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
record=dict(version=s['version'],native=target.relative_to(R).as_posix(),native_sha256=digest,native_bytes=target.stat().st_size,
    objects=len(s.objects),required_immutable_libraries=json.loads((R/'evidence/G1_025r1/checkpoint.json').read_text())['required_immutable_libraries'],
    source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256((R/s['photo_cut_file']).read_bytes()).hexdigest(),
    visual_acceptance=False,natural_use_verified=False,runtime_exported=False,storage_sharing_applied=False)
(R/'evidence/G1_026/checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('BRIDGEHEAD_PORTAL_SAVED',json.dumps(record),flush=True)
