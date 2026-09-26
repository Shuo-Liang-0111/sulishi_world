"""Linear HDR from the exact native world; no foreign city panorama added."""
import bpy,json,math,sys,hashlib,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path,validate_native
original=bpy.context.scene;V=original['version']
native=validate_native(bpy.data.filepath);native_stat=native.stat()
with native.open('rb') as stream:native_hash=hashlib.file_digest(stream,'sha256').hexdigest()
checkpoint=json.loads(read_path(f'evidence/{V}/checkpoint.json').read_text())
assert checkpoint['native_sha256']==native_hash
target=write_path(f'web/assets/{V}_sky.hdr')
pending=target.with_name(target.stem+'.pending.hdr')
assert not target.exists() and not pending.exists(),'Preserve previous export attempts.'
qa=bpy.data.scenes.new('TEMP_NATIVE_SKY_EXPORT');qa.world=original.world
cd=bpy.data.cameras.new('TEMP_SKY_CAMERA');co=bpy.data.objects.new('TEMP_SKY_CAMERA',cd);qa.collection.objects.link(co)
cd.type='PANO';cd.panorama_type='EQUIRECTANGULAR';co.rotation_euler=(math.pi/2,0,0);qa.camera=co
qa.render.engine='CYCLES';qa.cycles.device=globals().get('SKY_DEVICE','CPU');qa.cycles.samples=8
qa.render.threads_mode='FIXED';qa.render.threads=10
qa.render.resolution_x=1024;qa.render.resolution_y=512;qa.render.resolution_percentage=100
qa.render.image_settings.file_format='HDR';qa.render.filepath=str(pending)
try:
    bpy.context.window.scene=qa;bpy.ops.render.render(write_still=True)
finally:
    bpy.context.window.scene=original;bpy.data.objects.remove(co,do_unlink=True);bpy.data.cameras.remove(cd);bpy.data.scenes.remove(qa)
assert pending.is_file() and pending.stat().st_size>10000
pending.rename(target)
assert native.stat().st_size==native_stat.st_size and native.stat().st_mtime_ns==native_stat.st_mtime_ns
report={'version':V,'native_sha256':native_hash,'process_id':os.getpid(),'hdr':str(target),
        'hdr_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'basis':'Exact current native world in a temporary geometry-free scene; linear radiance, no exposure bake',
        'native_unmodified':True,'runtime_same_version_verified':False,'natural_use_verified':False}
write_path(f'evidence/{V}/sky_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NATIVE_SKY_EXPORTED',json.dumps(report),flush=True)
