import bpy,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld')
scene=bpy.context.scene
out=ROOT/'evidence'/scene['version'];out.mkdir(parents=True,exist_ok=True)
scene.cycles.samples=12
scene.camera=bpy.data.objects['QA_Whole_context_SW']
scene.render.resolution_x=1440;scene.render.resolution_y=1000
scene.render.filepath=str(out/'PHOTO_SOURCE_OVERVIEW.png')
bpy.ops.render.render(write_still=True)
print(json.dumps({'render':scene.render.filepath,'purpose':'unmodified source quality assessment'}))
