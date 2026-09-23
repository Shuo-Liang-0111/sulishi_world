"""Small exact-geometry reproduction, deliberately separate from the city export."""
import bpy,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_007r2'
selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
names=['BE_DISPLAY_CASE_BASE','BE_DISPLAY_GLASS_front','BE_DISPLAY_GLASS_top','BE_DISPLAY_GLASS_left','BE_DISPLAY_GLASS_right']
out=ROOT/'web/assets/diagnostics';out.mkdir(exist_ok=True)
try:
    for o in scene.objects:o.select_set(False)
    for name in names:bpy.data.objects[name].select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out/'glass_case.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_tangents=True)
finally:
    for o in scene.objects:o.select_set(False)
    for o in selected:o.select_set(True)
    bpy.context.view_layer.objects.active=active
print(json.dumps({'version':scene['version'],'names':names,'file':str(out/'glass_case.glb'),'bytes':(out/'glass_case.glb').stat().st_size,'native_modified':False}))
