"""Run independent Blender workers sequentially, recording real process IDs."""
import datetime,json,subprocess,sys,argparse
from pathlib import Path
R=Path(__file__).resolve().parents[1]
V='G1_015r3';native=R/'native/G1_015r3_service_surface_working.blend';E=R/'evidence'/V
blender='F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe'
base=[blender,'--factory-startup','-b',str(native),'--threads','10','--python-exit-code','1','--python']
jobs=[
 ('north_native',base+[str(R/'tools/render_native_checkpoint.py'),'--','BE_QA_SERVICE_NORTH','surface-check']),
 ('diffuse_bake',base+[str(R/'tools/bake_service_diffuse.py')]),
 ('export',base+[str(R/'tools/export_native_checkpoint.py')]),
 ('reflection_north',base+[str(R/'tools/render_service_reflection.py'),'--','NORTH']),
 ('reflection_front',base+[str(R/'tools/render_service_reflection.py'),'--','FRONT']),
 ('roundtrip',base+[str(R/'tools/verify_native_checkpoint.py')]),
 ('runtime_encoding',[sys.executable,str(R/'tools/pack_bellevue_runtime.py'),'--version',V]),
 ('runtime_externalization',[sys.executable,str(R/'tools/externalize_bellevue_runtime.py'),'--version',V])
]
parser=argparse.ArgumentParser();parser.add_argument('--from-stage',choices=[x[0] for x in jobs]);args=parser.parse_args()
completed=[]
if args.from_stage:
 state=json.loads((E/'surface_pipeline.json').read_text());assert state['version']==V and state['status']=='failed'
 index=next(i for i,job in enumerate(jobs) if job[0]==args.from_stage)
 assert state['completed']==[x[0] for x in jobs[:index]],'Resume must preserve only actually completed stages'
 completed=state['completed'];jobs=jobs[index:]
def write(stage,status,pid=None,exit_code=None):
 (E/'surface_pipeline.json').write_text(json.dumps({'version':V,'stage':stage,'status':status,
  'pid':pid,'exit_code':exit_code,'completed':completed,'updated_at':datetime.datetime.now().isoformat(),
  'visual_acceptance':False,'default_unchanged':'G1_007r5'},indent=2))
for stage,command in jobs:
 with (R/'runtime/logs'/f'{V}_{stage}_surface_pipeline.log').open('w',encoding='utf-8') as log:
  process=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  write(stage,'running',process.pid)
  result=process.wait()
 if result:
  write(stage,'failed',process.pid,result)
  raise RuntimeError(f'{stage} failed: {result}; inspect its log')
 completed.append(stage)
write('all','complete',exit_code=0)
print('SURFACE_FILES_READY_FOR_REGISTRATION_AND_VISUAL_REVIEW',V,flush=True)
