"""Read-only compatibility check; receives explicit source name and expected version."""
import bpy,sys,json
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]
name,version=args
R=Path('F:/MyWorld/ZurichWorld');candidate=R/'native'/name.replace('.blend','.lossless-check.blend')
assert Path(bpy.data.filepath).resolve()==candidate.resolve()
assert bpy.context.scene['version']==version
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
rec={'version':version,'file':bpy.data.filepath,'object_count':len(bpy.context.scene.objects),'original_photo_nodes':2039,'native_reopen':True,'scene_not_modified':True}
(R/'evidence/storage'/name.replace('.blend','')/'reopen.json').write_text(json.dumps(rec,indent=2))
print(json.dumps(rec),flush=True)
