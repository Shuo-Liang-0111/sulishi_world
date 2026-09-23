"""Linear HDR from the exact native world; no foreign city panorama added."""
import bpy,json,math
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');original=bpy.context.scene;V=original['version']
qa=bpy.data.scenes.new('TEMP_NATIVE_SKY_EXPORT');qa.world=original.world
cd=bpy.data.cameras.new('TEMP_SKY_CAMERA');co=bpy.data.objects.new('TEMP_SKY_CAMERA',cd);qa.collection.objects.link(co)
cd.type='PANO';cd.panorama_type='EQUIRECTANGULAR';co.rotation_euler=(math.pi/2,0,0);qa.camera=co
qa.render.engine='CYCLES';qa.cycles.device=globals().get('SKY_DEVICE','CPU');qa.cycles.samples=8
qa.render.resolution_x=1024;qa.render.resolution_y=512;qa.render.resolution_percentage=100
qa.render.image_settings.file_format='HDR';qa.render.filepath=str(ROOT/f'web/assets/{V}_sky.hdr')
try:
    bpy.context.window.scene=qa;bpy.ops.render.render(write_still=True)
finally:
    bpy.context.window.scene=original;bpy.data.objects.remove(co,do_unlink=True);bpy.data.cameras.remove(cd);bpy.data.scenes.remove(qa)
print(json.dumps({'version':V,'hdr':str(ROOT/f'web/assets/{V}_sky.hdr'),'basis':'Exact native Nishita world, sun disc off; linear radiance, no exposure bake'}))
