"""Save the complete022 scene only after source/contact and regression checks."""
from pathlib import Path
import hashlib,json,runpy,shutil
import bpy

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_022'
native=R/'native/G1_022_riviera_lower_working.blend'
assert not native.exists() and shutil.disk_usage(R).free>500_000_000
for script in ['blender_check_riviera_lower.py','blender_check_riviera_trees.py',
               'blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/script))
libraries={
    'G1_020r2_utoquai_coating_working.blend':'9de0f5d2d50cb599fb140e9837ade183fe6bd538e06f879889299a858d19ca13',
    'G1_021r2_riviera_continuous_working.blend':'6783e9ce386f6ae2c53e24bfa3a5ba9d61a3a6f0b5dac0eda0e1e48733e4b756'}
for name,digest in libraries.items():
    assert hashlib.file_digest((R/'native'/name).open('rb'),'sha256').hexdigest()==digest
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
record={'version':s['version'],'native':str(native.relative_to(R)),'native_bytes':native.stat().st_size,
        'native_sha256':hashlib.file_digest(native.open('rb'),'sha256').hexdigest(),
        'required_immutable_libraries':libraries,'objects':len(s.objects),
        'previous_checkpoints_retained':True,'native_geometry_checks_passed':True,
        'visual_acceptance':False,'natural_use_verified':False,'runtime_exported':False,
        'script_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'tools').glob('*riviera_lower*.py')}}
(R/'evidence/G1_022/checkpoint.json').write_text(json.dumps(record,indent=2))
pointer=R/'runtime/station_road_working.json';work=json.loads(pointer.read_text())
work.update(version=s['version'],native=str(native),accepted=False,not_published=True,
            source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256((R/s['photo_cut_file']).read_bytes()).hexdigest(),
            next='Inspect022 from four lower-approach cameras and an upper promenade regression. Bridge underpass, matching runtime and natural use remain incomplete.')
pointer.write_text(json.dumps(work,ensure_ascii=False,indent=2))
print('LOWER_NATIVE_SAVED',json.dumps(record),flush=True)
