"""Correct radiance serialization, then inspect the new facilities sequentially."""
import datetime,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
calibration=json.loads((R/'evidence/runtime_lightcache_encoding.json').read_text())
assert calibration['direct_max_error']<.004
blender='F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe'
def run_native(path,script,*args):
    command=[blender,'--factory-startup','-b',str(R/'native'/path),'--threads','10','--python-exit-code','1','--python',str(R/'tools'/script)]
    if args:command+=['--',*args]
    return command
jobs=[('linear_diffuse_bake',run_native('G1_015r3_service_surface_working.blend','bake_service_diffuse.py')),
      ('linear_diffuse_denoise',[sys.executable,str(R/'tools/denoise_service_light_cache.py')])]
for view in ['INFO','REVERSE','BIN']:
    jobs.append(('east_'+view.lower(),run_native('G1_016_south_east_facilities_working.blend','render_native_checkpoint.py','BE_QA_SOUTH_EAST_'+view,'surface-check')))
completed=[]
def state(stage,status,pid=None,exit_code=None):
    (R/'runtime/linear_light_and_facilities.json').write_text(json.dumps({'stage':stage,'status':status,'pid':pid,'exit_code':exit_code,'completed':completed,'updated_at':datetime.datetime.now().isoformat(),'runtime_acceptance':False},indent=2))
for stage,command in jobs:
    with (R/'runtime/logs'/f'linear_facilities_{stage}.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state(stage,'running',process.pid);result=process.wait()
    if result:
        state(stage,'failed',process.pid,result);raise RuntimeError(f'{stage}: exit {result}')
    completed.append(stage)
state('all','complete',exit_code=0)
print('READY_FOR_ACTUAL_LINEAR_LIGHT_AND_FACILITY_REVIEW',flush=True)
