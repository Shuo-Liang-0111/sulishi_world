"""Save a clearly unaccepted027 working checkpoint, preserving all prior files."""
from pathlib import Path
import contextlib,hashlib,io,json,runpy,shutil
import bpy
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;E=R/'evidence/G1_027'
assert s['version']=='G1_027' and Path(bpy.data.filepath).name=='G1_026_bridgehead_portal_working.blend'
target=R/'native/G1_027_bridge_deck_working.blend';assert not target.exists()
assert shutil.disk_usage(R).free>350_000_000
checks=['blender_check_bridge_deck.py','blender_check_quaibruecke.py','blender_check_quaibruecke_water.py',
        'blender_check_bridgehead_bank.py','blender_check_bridgehead_portal.py','blender_check_riviera_lower.py',
        'blender_check_riviera_trees.py','blender_check_riviera_quay.py','blender_check_utoquai_kiosk.py','blender_check_limmat_sidewalk.py']
for name in checks:
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):runpy.run_path(str(R/'tools'/name))
    (E/(Path(name).stem+'.txt')).write_text(buf.getvalue(),encoding='utf-8')
    print('CHECK_RAN',name,flush=True)
qa=json.loads((E/'deck_checks.json').read_text())
assert not qa['geometry_globally_accepted'] and qa['unresolved_large_level_transitions']
s.camera=bpy.data.objects['BD_QA_EAST'];bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=False)
record=json.loads((R/'evidence/G1_026/checkpoint.json').read_text())
with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
record.update(version=s['version'],native=target.relative_to(R).as_posix(),native_bytes=target.stat().st_size,native_sha256=digest,
    objects=len(s.objects),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256((R/s['photo_cut_file']).read_bytes()).hexdigest(),
    visual_acceptance=False,natural_use_verified=False,runtime_exported=False,geometry_globally_accepted=False,
    unresolved_level_transitions=len(qa['unresolved_large_level_transitions']),largest_transition_m=max(abs(q['difference_m']) for q in qa['level_transitions']),
    storage_sharing_applied=True,shared_meshes_unchanged_from='G1_026',pre_save_checks=checks)
(E/'checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('BRIDGE_DECK_DRAFT_SAVED',target.stat().st_size,digest,flush=True)
