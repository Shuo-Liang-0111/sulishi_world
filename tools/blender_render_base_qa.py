import bpy
import json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld')
out=ROOT/'evidence/G1_001';out.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
paths=[]
for name,size in [('QA_Topdown',(1400,1400)),('QA_Whole_context_SW',(1600,1100))]:
    scene.camera=bpy.data.objects[name]
    scene.render.resolution_x,scene.render.resolution_y=size
    scene.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    paths.append(scene.render.filepath)
print(json.dumps({'renders':paths,'purpose':'geographic_alignment_only_not_final_visual_quality'}))
