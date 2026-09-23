"""Fresh matching geometry, illumination and roundtrip; never promote automatically."""
import datetime,json,subprocess,sys,argparse
from pathlib import Path
R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['G1_016r1','G1_017','G1_017r1','G1_018r3'],default='G1_016r1');parser.add_argument('--resume-failed',action='store_true');args=parser.parse_args();V=args.version;E=R/'evidence'/V
working=json.loads((R/'runtime/station_road_working.json').read_text());assert working['version']==V
base=['F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe','--factory-startup','-b',working['native'],'--threads','10','--python-exit-code','1','--python']
jobs=[('diffuse',base+[str(R/'tools/bake_service_diffuse.py')]),
 ('denoise',[sys.executable,str(R/'tools/denoise_service_light_cache.py'),'--version',V]),
 ('export',base+[str(R/'tools/export_native_checkpoint.py')]),
 ('reflection_north',base+[str(R/'tools/render_service_reflection.py'),'--','NORTH']),
 ('reflection_front',base+[str(R/'tools/render_service_reflection.py'),'--','FRONT']),
 ('roundtrip',base+[str(R/'tools/verify_native_checkpoint.py')]),
 ('encode',[sys.executable,str(R/'tools/pack_bellevue_runtime.py'),'--version',V]),
 ('externalize',[sys.executable,str(R/'tools/externalize_bellevue_runtime.py'),'--version',V]),
 ('register_diffuse',[sys.executable,str(R/'tools/register_native_diffuse.py'),'--version',V]),
 ('register_reflections',[sys.executable,str(R/'tools/register_local_reflections.py'),'--version',V])]
if V.startswith('G1_017') or V=='G1_018r3':
    jobs[5:5]=[('reflection_east_info',base+[str(R/'tools/render_service_reflection.py'),'--','EAST_INFO']),('reflection_east_bin',base+[str(R/'tools/render_service_reflection.py'),'--','EAST_BIN'])]
    jobs[-1][1].append('--include-east')
if V=='G1_018r3':
    jobs[7:7]=[('reflection_fountain',base+[str(R/'tools/render_service_reflection.py'),'--','FOUNTAIN'])]
    jobs[-1][1].append('--include-fountain')
completed=[]
path=E/'runtime_pipeline.json'
if args.resume_failed:
    old=json.loads(path.read_text());assert old['version']==V and old['status']=='failed';completed=old['completed'];assert completed==[j[0] for j in jobs[:len(completed)]];jobs=jobs[len(completed):]
else:assert not path.exists(),'Inspect existing state before starting a second worker'
def save(stage,status,pid=None,code=None):
    path.write_text(json.dumps({'version':V,'stage':stage,'status':status,'pid':pid,'exit_code':code,'completed':completed,'updated_at':datetime.datetime.now().isoformat(),'candidate_registered':False,'accepted':False},indent=2))
for stage,command in jobs:
    with (R/'runtime/logs'/f'{V}_{stage}_runtime_pipeline.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);save(stage,'running',process.pid);code=process.wait()
    if code:save(stage,'failed',process.pid,code);raise RuntimeError(f'{stage} exit{code}')
    completed.append(stage)
save('all','complete',code=0);print('EAST_RUNTIME_READY_FOR_MANUAL_CANDIDATE_REGISTRATION_AND_ACTUAL_REVIEW')
