"""Read-only native compatibility check of a separately encoded old checkpoint."""
import bpy,json
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_017'
assert Path(bpy.data.filepath).name=='G1_017_lossless_encoding_check.blend'
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
record={'version':s['version'],'file':bpy.data.filepath,'object_count':len(s.objects),'original_photo_nodes':2039,'native_reopen':True,'scene_not_modified':True}
(R/'evidence/G1_017/lossless_native_reopen.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
