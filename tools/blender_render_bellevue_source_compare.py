import bpy,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
names=['03_I3S_PHOTOGRAPHIC_REFERENCE','04_RETAINED_PHOTO_CONTEXT','10_BELLEVUE_RECONSTRUCTION']
previous={n:bpy.data.collections[n].hide_render for n in names}
old_camera=scene.camera
try:
    bpy.data.collections[names[0]].hide_render=False
    bpy.data.collections[names[1]].hide_render=True
    bpy.data.collections[names[2]].hide_render=True
    scene.camera=bpy.data.objects['BE_QA_STRUCTURE'];scene.cycles.samples=16
    scene.render.filepath=str(ROOT/'evidence/G1_005r2/BE_SOURCE_SAME_STRUCTURE_VIEW.png')
    bpy.ops.render.render(write_still=True)
finally:
    for n,v in previous.items():bpy.data.collections[n].hide_render=v
    scene.camera=old_camera
print(json.dumps({'image':scene.render.filepath,'kind':'original photography reference from identical structural review camera'}))
