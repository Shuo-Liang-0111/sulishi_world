"""Fresh bounded r16 audit followed by unhidden scene views; no native save."""
from pathlib import Path
import hashlib,json,os,runpy,sys,time
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path,write_path
from png_integrity import verify_png

s=bpy.context.scene;assert s['version']=='G1_027r16'
native=Path(bpy.data.filepath);stat=native.stat();start=time.time()
runpy.run_path(str(ROOT/'tools/blender_check_stadelhofen_wallfoot.py'),run_name='__main__')
receipt=read_path('evidence/G1_027r16/wallfoot_fresh_checks.json')
assert receipt.stat().st_mtime>=start and json.loads(receipt.read_text())['process_id']==os.getpid()
completed=[]
s.render.threads_mode='FIXED';s.render.threads=10
s.render.use_sequencer=False;s.render.use_compositing=False;s.render.use_persistent_data=False
if hasattr(s.cycles,'denoising_use_gpu'):s.cycles.denoising_use_gpu=False
from blender_render_memory import prepare_review_memory
prepare_review_memory('SJ_QA_WALLFOOT')
for name in ['SJ_QA_WALLFOOT','SJ_QA_SIDE','SF1_QA_ENTRY','SF1_QA_APPROACH']:
    runpy.run_path(str(ROOT/'tools/blender_render_bellevue.py'),init_globals={
        'REVIEW_CAMERA':name,'REVIEW_DEVICE':'CPU','REVIEW_SAMPLES':32,'REVIEW_RESOLUTION':(1400,960)})
    p=read_path('evidence/G1_027r16/'+name+'.png')
    complete={'camera':name,**verify_png(p,(1400,960))}
    completed.append(complete)
    write_path('evidence/G1_027r16/wallfoot_view_batch.json').write_text(json.dumps({
        'process_id':os.getpid(),'native':str(native),'completed':completed,
        'bounded_joint_checks_before_render':True,'full_G1_checks_run':False,
        'native_saved':False,'visual_acceptance':False},indent=2),encoding='utf-8')
    print('WALLFOOT_VIEW_COMPLETE',name,flush=True)
assert native.stat().st_size==stat.st_size and native.stat().st_mtime_ns==stat.st_mtime_ns
