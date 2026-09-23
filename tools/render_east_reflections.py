"""Capture local native radiance beside the inspected eastern street furniture."""
import datetime,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];V='G1_016r1';E=R/'evidence'/V
completed=[]
for key in ['EAST_INFO','EAST_BIN']:
    command=['F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe','--factory-startup','-b',str(R/'native/G1_016r1_east_surface_working.blend'),'--threads','10','--python-exit-code','1','--python',str(R/'tools/render_service_reflection.py'),'--',key]
    with (R/'runtime/logs'/f'{V}_{key.lower()}_reflection.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state={'version':V,'key':key,'status':'running','pid':process.pid,'completed':completed,'updated_at':datetime.datetime.now().isoformat()}
        (E/'east_reflection_process.json').write_text(json.dumps(state,indent=2))
        code=process.wait()
    state.update(status='failed' if code else 'complete',exit_code=code,updated_at=datetime.datetime.now().isoformat())
    if not code:completed.append(key)
    (E/'east_reflection_process.json').write_text(json.dumps(state,indent=2))
    if code:raise RuntimeError(f'{key}: {code}')
print('EAST_REFLECTIONS_READY_FOR_VISUAL_REVIEW')
