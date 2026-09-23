"""Sequential review of the saved repair: entire frames, aperture and prior crop."""
import json,datetime,subprocess,argparse
from pathlib import Path
R=Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['G1_016r1','G1_017','G1_017r1'],default='G1_016r1');parser.add_argument('--cameras',nargs='+');args=parser.parse_args();version=args.version;completed=[]
working=json.loads((R/'runtime/station_road_working.json').read_text());assert working['version']==version
cameras=args.cameras or ['BE_QA_SOUTH_EAST_'+x for x in ['INFO_WIDE','REVERSE_WIDE','BIN_OPENING','INFO','REVERSE']]
for camera in cameras:
    assert camera.startswith('BE_QA_')
    command=['F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe','--factory-startup','-b',working['native'],'--threads','10','--python-exit-code','1','--python',str(R/'tools/render_native_checkpoint.py'),'--',camera,'surface-check']
    with (R/'runtime/logs'/f'{version}_{camera}.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state={'version':version,'current_camera':camera,'pid':process.pid,'status':'running','completed':completed,'updated_at':datetime.datetime.now().isoformat()}
        (R/'runtime/east_surface_review.json').write_text(json.dumps(state,indent=2));code=process.wait()
    if code:
        state.update(status='failed',exit_code=code);(R/'runtime/east_surface_review.json').write_text(json.dumps(state,indent=2));raise RuntimeError(state)
    completed.append(camera)
state.update(status='complete',completed=completed,updated_at=datetime.datetime.now().isoformat());(R/'runtime/east_surface_review.json').write_text(json.dumps(state,indent=2))
print('EAST_SURFACE_IMAGES_READY_FOR_VISUAL_REVIEW')
