"""Fresh load only; no native mutation/save. Actual image decoding is a separate check."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sf1_common import *
assert bpy.context.scene.get('sf1_version')==D['version']
tag=D['version'].split('_')[-1]
native=Path(bpy.data.filepath);digest=sha(native)
from check_geometry import run
run()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['SF1_QA_ENTRY','SF1_QA_REVERSE','SF1_QA_APPROACH','SF1_QA_CONTEXT','SF1_QA_DOOR_DETAIL','SF1_QA_DOOR_OPEN']
for name in args:
    control=bpy.data.objects['SF1_DOOR_CENTRE_CONTROL'];control['open_fraction']=1. if name=='SF1_QA_DOOR_OPEN' else 0.
    control.update_tag();bpy.context.view_layer.update();bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    render(name,'evidence/'+tag,32);print('SF1_RENDER_COMPLETE',name,flush=True)
control['open_fraction']=0.;control.update_tag();bpy.context.view_layer.update()
assert sha(native)==digest
write(f'evidence/{tag}/fresh_render_batch.json',dict(native=str(native),sha256=digest,process_id=os.getpid(),cameras=args,blender=bpy.app.version_string,saved=False,visually_accepted=False))
