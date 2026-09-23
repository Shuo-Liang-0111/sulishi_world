"""Save a new024 native only after new-water and retained-place checks."""
from pathlib import Path
import hashlib,json,runpy,shutil
import bpy

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_024'
native=R/'native/G1_024_bridge_water_context_working.blend'
assert not native.exists() and shutil.disk_usage(R).free>500_000_000
for name in ['blender_check_quaibruecke.py','blender_check_quaibruecke_water.py',
             'blender_check_riviera_lower.py','blender_check_riviera_trees.py',
             'blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/name))
libraries=json.loads((R/'evidence/G1_023r1/checkpoint.json').read_text())['required_immutable_libraries']
for name,digest in libraries.items():
    with (R/'native'/name).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
record=dict(version=s['version'],native=native.relative_to(R).as_posix(),native_bytes=native.stat().st_size,
    native_sha256=digest,objects=len(s.objects),required_immutable_libraries=libraries,
    previous_checkpoints_retained=True,visual_acceptance=False,natural_use_verified=False,runtime_exported=False,
    source_scripts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'tools').glob('*quaibruecke*.py')})
(R/'evidence'/s['version']/'checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
p=R/'runtime/station_road_working.json';work=json.loads(p.read_text(encoding='utf-8'))
work.update(version=s['version'],native=str(native),accepted=False,not_published=True,source_cut_file=s['photo_cut_file'],
            source_cut_sha256=hashlib.sha256((R/s['photo_cut_file']).read_bytes()).hexdigest(),
            next='Inspect024 same six saved-native views. Source-shape water/whole-bridge context added; remaining photography, runtime and actual natural use not accepted.')
p.write_text(json.dumps(work,ensure_ascii=False,indent=2),encoding='utf-8')
print('BRIDGE_WATER_SAVED',json.dumps(record),flush=True)
