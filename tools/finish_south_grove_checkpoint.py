"""Sequential verification and lossless runtime packaging of the saved checkpoint."""
from pathlib import Path
import json
import subprocess
import sys
import datetime

R=Path(__file__).resolve().parents[1]
working=json.loads((R/'runtime/station_road_working.json').read_text())
V=working['version'];assert V in ['G1_015r1','G1_015r2','G1_015r3'];E=R/'evidence'/V
BLENDER=Path('F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe')
native=Path(working['native']).resolve();assert native.is_relative_to((R/'native').resolve())
assert json.loads((R/'web/assets'/f'{V}_bellevue.json').read_text())['indirect_occlusion']['image_sha256']==json.loads((R/'derived/runtime_occlusion'/V/'manifest.json').read_text())['image_sha256']
jobs=[
    ('roundtrip',[str(BLENDER),'--factory-startup','-b',str(native),'--threads','10','--python-exit-code','1','--python',str(R/'tools/verify_native_checkpoint.py')]),
    ('runtime_encoding',[sys.executable,str(R/'tools/pack_bellevue_runtime.py'),'--version',V]),
    ('runtime_externalization',[sys.executable,str(R/'tools/externalize_bellevue_runtime.py'),'--version',V]),
    ('register_candidate',[sys.executable,str(R/'tools/register_haus_candidate.py'),'--version',V]),
]
completed=[]
def write(stage,status):
    (E/'package_pipeline.json').write_text(json.dumps({'version':V,'stage':stage,'status':status,'completed':completed,'updated_at':datetime.datetime.now().isoformat(),'visual_or_use_acceptance':False},indent=2))
for stage,command in jobs:
    write(stage,'running')
    with (R/'runtime/logs'/f'{V}_{stage}_pipeline.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        write(stage,'failed');raise RuntimeError(f'{stage}: exit {result.returncode}; inspect stage log')
    completed.append(stage)
write('all','complete')
print('CHECKPOINT_READY_FOR_REALTIME_REVIEW',V,flush=True)
