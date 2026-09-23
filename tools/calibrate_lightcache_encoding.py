"""Check the actual saved HDR against the in-memory native bake."""
import bpy,json,sys
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');sys.path.insert(0,str(R/'tools'))
from radiance_cache_io import read_hdr,write_hdr
code=(R/'tools/calibrate_diffuse_cache.py').read_text()
code=code.replace("assert 'FINISHED' in bpy.ops.object.bake", "before_bake_colorspace=image.colorspace_settings.name\nassert 'FINISHED' in bpy.ops.object.bake")
exec(compile(code.split('report=')[0],'independent_constant_light_test','exec'))
after_bake_colorspace=image.colorspace_settings.name
path=R/'evidence/runtime_diffuse_calibration_saved.hdr'
image.filepath_raw=str(path);image.file_format='HDR';after_format_colorspace=image.colorspace_settings.name;image.save()
raw=read_hdr(path);saved=raw[8,8].tolist()
report={'in_memory':pixel,'saved_hdr':saved,'max_error':max(abs(a-b) for a,b in zip(pixel,saved)),
        'image_colorspace':image.colorspace_settings.name,'file_format':image.file_format,
        'view_as_render':image.use_view_as_render,'source_native_loaded':False,
        'colorspace_trace':{'before_bake':before_bake_colorspace,'after_bake':after_bake_colorspace,'after_format':after_format_colorspace,'after_save':image.colorspace_settings.name}}
import numpy as np
array=np.empty(16*16*4,np.float32);image.pixels.foreach_get(array)
rgb=np.ascontiguousarray(array.reshape(16,16,4)[::-1,:,:3])
linear_path=R/'evidence/runtime_diffuse_calibration_linear.hdr';write_hdr(linear_path,rgb)
linear=read_hdr(linear_path)[8,8].tolist()
report['direct_linear_hdr']=linear
report['direct_max_error']=max(abs(a-b) for a,b in zip(pixel,linear))
assert report['direct_max_error']<.004,report
ob.hide_render=True
camera_data=bpy.data.cameras.new('CALIBRATION_CAMERA');camera_obj=bpy.data.objects.new('CALIBRATION_CAMERA',camera_data)
s.collection.objects.link(camera_obj);s.camera=camera_obj
s.render.resolution_x=16;s.render.resolution_y=16;s.render.resolution_percentage=100
s.cycles.samples=4;s.cycles.use_denoising=False
s.render.image_settings.file_format='HDR';s.render.filepath=str(R/'evidence/runtime_sky_calibration_saved.hdr')
assert 'FINISHED' in bpy.ops.render.render(write_still=True)
sky=read_hdr(Path(s.render.filepath))[8,8].tolist()
report['render_write_still_hdr']=sky
report['render_write_still_max_error']=max(abs(value-.6) for value in sky)
assert report['render_write_still_max_error']<.004,report
(R/'evidence/runtime_lightcache_encoding.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
