"""Persist a new editable021 checkpoint after independent physical checks."""
from pathlib import Path
import json,hashlib,shutil,runpy
import bpy
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_021'
native=R/'native/G1_021_riviera_quay_working.blend'
assert not native.exists() and shutil.disk_usage(R).free>300_000_000
for script in ['blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/script))
assert any(Path(bpy.path.abspath(lib.filepath)).resolve()==R/'native/G1_020r2_utoquai_coating_working.blend' for lib in bpy.data.libraries)
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
record_path=R/'evidence/G1_021/construction.json';record=json.loads(record_path.read_text())
record.update(native_saved=True,native=str(native.relative_to(R)),native_bytes=native.stat().st_size,
              native_sha256=hashlib.file_digest(native.open('rb'),'sha256').hexdigest(),
              source_code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'tools').glob('*riviera_quay*.py')})
record_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
path=R/'runtime/station_road_working.json';w=json.loads(path.read_text())
cut=R/s['photo_cut_file']
w.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cut.read_bytes()).hexdigest(),
         source_cut_nodes=len(json.loads(cut.read_text())['overrides']),accepted=False,not_published=True,
         next='Review both directions and stair detail from saved021; reconstruct bounded residual source context only after identifying it. Export and natural use pending.')
path.write_text(json.dumps(w,indent=2),encoding='utf-8')
print(json.dumps({'native':str(native),'bytes':native.stat().st_size}),flush=True)
