"""Fresh native process, full scene, actual human-height fountain views."""
import json, datetime, subprocess, argparse
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--version',default='G1_018');p.add_argument('--cameras',nargs='+');a=p.parse_args()
w=json.loads((R/'runtime/station_road_working.json').read_text());assert w['version']==a.version and a.version.startswith('G1_018')
completed=[];path=R/'runtime/fountain_review.json'
for camera in a.cameras or ['BE_QA_FOUNTAIN_OVERVIEW','BE_QA_FOUNTAIN_REVERSE','BE_QA_FOUNTAIN_RIM']:
    assert camera.startswith('BE_QA_')
    cmd=['F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe','--factory-startup','-b',w['native'],'--threads','10','--python-exit-code','1','--python',str(R/'tools/render_native_checkpoint.py'),'--',camera,'surface-check']
    with (R/'runtime/logs'/f'{a.version}_{camera}.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state={'version':a.version,'camera':camera,'pid':process.pid,'status':'running','completed':completed,'updated_at':datetime.datetime.now().isoformat()};path.write_text(json.dumps(state,indent=2));code=process.wait()
    if code:
        state.update(status='failed',exit_code=code);path.write_text(json.dumps(state,indent=2));raise RuntimeError(state)
    completed.append(camera)
state.update(status='complete',completed=completed,pid=None,updated_at=datetime.datetime.now().isoformat());path.write_text(json.dumps(state,indent=2))
print('Native fountain images ready for actual visual inspection.')
