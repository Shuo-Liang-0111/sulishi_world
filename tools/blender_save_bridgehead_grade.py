"""Save027r1 only after actual mesh checks; keep all previous checkpoints."""
from pathlib import Path
import contextlib,hashlib,io,json,runpy,shutil
import bpy
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;E=R/'evidence/G1_027r1'
assert s['version']=='G1_027r1' and Path(bpy.data.filepath).name=='G1_027_bridge_deck_working.blend'
target=R/'native/G1_027r1_bridgehead_grade_working.blend';assert not target.exists()
assert shutil.disk_usage(R).free>350_000_000
checks=['blender_check_bridge_grade_patch.py','blender_check_bridge_deck.py','blender_check_quaibruecke.py',
        'blender_check_quaibruecke_water.py','blender_check_bridgehead_bank.py','blender_check_bridgehead_portal.py',
        'blender_check_riviera_lower.py','blender_check_riviera_trees.py','blender_check_riviera_quay.py',
        'blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']
for name in checks:
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):runpy.run_path(str(R/'tools'/name))
    (E/(Path(name).stem+'.txt')).write_text(buf.getvalue(),encoding='utf-8')
    print('CHECK_RAN',name,flush=True)
qa=json.loads((E/'deck_checks.json').read_text());assert not qa['unresolved_large_level_transitions']
bpy.context.preferences.filepaths.save_version=0
bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=False)
record=json.loads((R/'evidence/G1_027/checkpoint.json').read_text())
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
record.update(version=s['version'],native=target.relative_to(R).as_posix(),native_bytes=target.stat().st_size,native_sha256=digest,
    objects=len(s.objects),unresolved_level_transitions=0,largest_transition_m=max(abs(q['difference_m']) for q in qa['level_transitions']),
    visual_acceptance=False,natural_use_verified=False,runtime_exported=False,geometry_globally_accepted=False,
    grade_patch_file=s['grade_patch_file'],grade_patch_sha256=hashlib.sha256((R/s['grade_patch_file']).read_bytes()).hexdigest(),
    pre_save_checks=checks)
(E/'checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('BRIDGE_GRADE_DRAFT_SAVED',target.stat().st_size,digest,flush=True)
