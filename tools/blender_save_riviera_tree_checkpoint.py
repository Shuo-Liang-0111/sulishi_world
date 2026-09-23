"""Save021r1 only after all nine source trees and the retained works pass checks."""
from pathlib import Path
import json, hashlib, shutil, runpy
import bpy
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_021r1'
native=R/'native/G1_021r1_riviera_trees_working.blend'
assert not native.exists() and shutil.disk_usage(R).free>800_000_000
for name in ['blender_check_riviera_trees.py','blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']:
    runpy.run_path(str(R/'tools'/name))
library=R/'native/G1_020r2_utoquai_coating_working.blend'
assert hashlib.file_digest(library.open('rb'),'sha256').hexdigest()=='9de0f5d2d50cb599fb140e9837ade183fe6bd538e06f879889299a858d19ca13'
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
record={'version':s['version'],'native':str(native.relative_to(R)),'native_bytes':native.stat().st_size,
        'native_sha256':hashlib.file_digest(native.open('rb'),'sha256').hexdigest(),
        'previous_checkpoint_retained':'native/G1_021_riviera_quay_working.blend','immutable_shared_library_unchanged':True,
        'new_inventory_trees':9,'new_tree_pits':9,'objects':len(s.objects),'visual_acceptance':False,'runtime_use_verified':False,
        'script_sha256':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (R/'tools').glob('*riviera_tree*.py')}}
(R/'evidence/G1_021r1/checkpoint.json').write_text(json.dumps(record,indent=2))
wpath=R/'runtime/station_road_working.json';w=json.loads(wpath.read_text());cutpath=R/s['photo_cut_file']
w.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),
         source_cut_nodes=len(json.loads(cutpath.read_text())['overrides']),accepted=False,not_published=True,
         next='Reopen saved021r1 and inspect both quay directions, treads, a new root and the existing kiosk. No new matching export or natural-use acceptance yet.')
wpath.write_text(json.dumps(w,ensure_ascii=False,indent=2))
print(json.dumps(record),flush=True)
