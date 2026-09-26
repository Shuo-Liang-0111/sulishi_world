"""Fresh-process Cycles review; native construction remains untouched."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
import bpy
from pathlib import Path
import sys
R=WORKSPACE
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
assert len(args) in [1,2]
REVIEW_CAMERA=args[0]
REVIEW_DEVICE='CPU'
if len(args)==2:
    assert args[1]=='surface-check'
    REVIEW_SAMPLES=24
    REVIEW_RESOLUTION=(1280,840)
    if REVIEW_CAMERA.startswith(('SF1_QA_','BST_QA_')):
        REVIEW_SAMPLES=32
        REVIEW_RESOLUTION=(1400,960)
    if REVIEW_CAMERA in ['BE_QA_FOUNTAIN_RIM','BE_QA_FOUNTAIN_OVERFLOW']:
        REVIEW_SAMPLES=48
        REVIEW_RESOLUTION=(1600,1050)
s=bpy.context.scene
assert s['version'].startswith(('G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')), 'Older checkpoint review recipes need an explicit path migration first.'
s.render.threads_mode='FIXED';s.render.threads=10
s.render.use_sequencer=False
s.render.use_compositing=False
s.render.use_persistent_data=False
if hasattr(s.cycles,'denoising_use_gpu'):
    s.cycles.denoising_use_gpu=False
print('CPU_DENOISING',getattr(s.cycles,'denoising_use_gpu','property_absent'),flush=True)
bpy.context.view_layer.update()
if s['version'] in ['G1_015r1','G1_015r2','G1_015r3','G1_016','G1_016r1','G1_017','G1_017r1']:
    exec(compile((read_path(R/'tools/blender_check_pit_edges.py')).read_text(encoding='utf-8'),'check_pit_seams','exec'))
if s['version'].startswith(('G1_016','G1_017')):
    exec(compile((read_path(R/'tools/blender_check_east_facilities.py')).read_text(encoding='utf-8'),'check_east_contacts','exec'))
if s['version'].startswith('G1_018r'):
    exec(compile((read_path(R/'tools/blender_check_fountain59.py')).read_text(encoding='utf-8'),'check_fountain_connections','exec'))
if s['version'].startswith(('G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    import runpy
    runpy.run_path(str(R/'tools/blender_check_utoquai_kiosk.py'))
if s['version'].startswith(('G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_riviera_quay.py'))
    if '34_RIVIERA_TREES' in bpy.data.collections:
        runpy.run_path(str(R/'tools/blender_check_riviera_trees.py'))
if s['version'].startswith(('G1_023','G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_quaibruecke.py'))
if s['version'].startswith(('G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_quaibruecke_water.py'))
if s['version'].startswith(('G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_bridgehead_bank.py'))
if s['version'].startswith(('G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_verify_bank_sharing.py'))
    runpy.run_path(str(R/'tools/blender_check_bridgehead_portal.py'))
if s['version'].startswith('G1_027'):
    runpy.run_path(str(R/'tools/blender_check_bridge_deck.py'))
    if s['version']=='G1_027r1':
        runpy.run_path(str(R/'tools/blender_check_bridge_grade_patch.py'))
    if s['version'] in ['G1_027r2','G1_027r3','G1_027r4','G1_027r5','G1_027r6','G1_027r7','G1_027r8','G1_027r9','G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_bridge_grade_refinement.py'))
    if s['version']=='G1_027r3':
        runpy.run_path(str(R/'tools/blender_check_bridge_photo_cleanup.py'))
    if s['version'] in ['G1_027r5','G1_027r6','G1_027r7','G1_027r8','G1_027r9','G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_sternen_grill.py'))
    if s['version'] in ['G1_027r8','G1_027r9','G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_sternen_doors.py'),run_name='__main__')
    if s['version'] in ['G1_027r9','G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_ubs_frontages.py'),run_name='__main__')
    if s['version'] in ['G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_ubs_nearfront.py'),run_name='__main__')
    if s['version']=='G1_027r10':
        runpy.run_path(str(R/'tools/blender_probe_bank_tram_shelter.py'),run_name='__main__')
    if s['version'] in ['G1_027r11','G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_stadelhofen_01.py'),run_name='__main__')
    if s['version'] in ['G1_027r12','G1_027r13','G1_027r14']:
        runpy.run_path(str(R/'tools/blender_check_bank_tram_shelter.py'),run_name='__main__')
    if s['version']=='G1_027r4':
        runpy.run_path(str(R/'tools/blender_check_bridge_fittings.py'))
if s['version'].startswith(('G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_riviera_lower.py'))
if s['version'].startswith(('G1_019','G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    exec(compile((read_path(R/'tools/blender_check_limmat_sidewalk.py')).read_text(encoding='utf-8'),'check_limmat_geometry','exec'))
    from blender_render_memory import prepare_review_memory
    prepare_review_memory(REVIEW_CAMERA)
exec(compile((read_path(R/'tools/blender_render_bellevue.py')).read_text(encoding='utf-8'),'fresh_native_review','exec'))
print('FRESH_REVIEW_FINISHED',s['version'],REVIEW_CAMERA,flush=True)
