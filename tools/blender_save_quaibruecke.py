"""Save023 only after connection and retained-scene regression checks."""
from pathlib import Path
import hashlib,json,runpy,shutil
import bpy

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version'] in ['G1_023','G1_023r1']
filename={'G1_023':'G1_023_quaibruecke_connection_working.blend','G1_023r1':'G1_023r1_quaibruecke_portals_working.blend'}[s['version']]
native=R/'native'/filename
assert not native.exists() and shutil.disk_usage(R).free>450_000_000
for script in ['blender_check_quaibruecke.py','blender_check_riviera_lower.py',
               'blender_check_riviera_trees.py','blender_check_riviera_quay.py',
               'blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/script))
libraries=json.loads((R/'evidence/G1_022r2/checkpoint.json').read_text())['required_immutable_libraries']
for name,digest in libraries.items():
    with (R/'native'/name).open('rb') as handle:
        assert hashlib.file_digest(handle,'sha256').hexdigest()==digest
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
with native.open('rb') as handle:digest=hashlib.file_digest(handle,'sha256').hexdigest()
record=dict(version=s['version'],native=native.relative_to(R).as_posix(),native_bytes=native.stat().st_size,
            native_sha256=digest,required_immutable_libraries=libraries,objects=len(s.objects),
            previous_checkpoints_retained=True,hidden_floor_profile_inferred=True,
            visual_acceptance=False,natural_use_verified=False,runtime_exported=False,
            source_scripts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'tools').glob('*quaibruecke*.py')})
(R/'evidence'/s['version']/'checkpoint.json').write_text(json.dumps(record,indent=2))
pointer=R/'runtime/station_road_working.json';work=json.loads(pointer.read_text())
work.update(version=s['version'],native=str(native),accepted=False,not_published=True,
            source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256((R/s['photo_cut_file']).read_bytes()).hexdigest(),
            next='Inspect023 north/interior/eastern bridge underside/lake approach/stair and unchanged north bank. Matching runtime and actual natural use remain incomplete.')
pointer.write_text(json.dumps(work,ensure_ascii=False,indent=2))
print('UNDERPASS_NATIVE_SAVED',json.dumps(record),flush=True)
