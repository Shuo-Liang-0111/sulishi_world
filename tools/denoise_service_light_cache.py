"""Use bundled OIDN's RT HDR filter; preserve raw source samples separately."""
import ctypes as C
import hashlib,json,os,time,argparse
from pathlib import Path
import numpy as np
from radiance_cache_io import read_hdr,write_hdr

parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3'],default='G1_015r3');args=parser.parse_args()
R=Path(__file__).resolve().parents[1];V=args.version
manifest=json.loads((R/'derived/runtime_lighting'/V/'manifest.json').read_text())
source=R/'web/assets'/manifest['file'];assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['sha256']
assert manifest.get('written_linear_max_relative_error',1)<.009,'Only verified linear cache may be denoised for runtime'
rgb=read_hdr(source);output=np.empty_like(rgb);height,width,_=rgb.shape
directory=Path('F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.shared')
# OIDN loads its device plugin by filename through the Windows loader. Scope the
# DLL search path to this worker; AddDllDirectory alone does not cover that call.
os.environ['PATH']=str(directory)+os.pathsep+os.environ['PATH']
dll_path=os.add_dll_directory(str(directory));lib=C.CDLL(str(directory/'OpenImageDenoise.dll'))
def fn(name,restype,args):
    result=getattr(lib,name);result.restype=restype;result.argtypes=args;return result
pointer=C.c_void_p;integer=C.c_int;string=C.c_char_p;size=C.c_size_t
new_device=fn('oidnNewDevice',pointer,[integer]);commit_device=fn('oidnCommitDevice',None,[pointer])
set_device_int=fn('oidnSetDeviceInt',None,[pointer,string,integer])
new_filter=fn('oidnNewFilter',pointer,[pointer,string]);commit_filter=fn('oidnCommitFilter',None,[pointer])
set_image=fn('oidnSetSharedFilterImage',None,[pointer,string,pointer,integer,size,size,size,size,size])
set_filter_int=fn('oidnSetFilterInt',None,[pointer,string,integer])
set_filter_bool=fn('oidnSetFilterBool',None,[pointer,string,C.c_bool])
execute=fn('oidnExecuteFilter',None,[pointer]);error=fn('oidnGetDeviceError',integer,[pointer,C.POINTER(string)])
release_filter=fn('oidnReleaseFilter',None,[pointer]);release_device=fn('oidnReleaseDevice',None,[pointer])
device=new_device(1)
def check():
    message=string();code=error(device,C.byref(message))
    if code:raise RuntimeError((code,message.value.decode() if message.value else 'OIDN error'))
check();assert device
set_device_int(device,b'numThreads',4);commit_device(device);check()
filter=None
try:
    # This Blender bundle has no usable RTLightmap input-weight combination.
    # Use its standard HDR RT filter and record that narrower approximation.
    filter=new_filter(device,b'RT');check();assert filter
    for name,array in [(b'color',rgb),(b'output',output)]:
        set_image(filter,name,array.ctypes.data,3,width,height,0,0,0)
    set_filter_bool(filter,b'hdr',True)
    set_filter_int(filter,b'maxMemoryMB',1024);commit_filter(filter);check()
    print('LIGHTMAP_DENOISE_STARTED',V,flush=True);start=time.monotonic();execute(filter);check()
    assert np.isfinite(output).all() and output.min()>=0
    path=R/'web/assets'/f'{V}_service_diffuse_linear_denoised.hdr';write_hdr(path,output)
    written=read_hdr(path)
    relative=np.abs(written-output)/(np.max(output,axis=2,keepdims=True)+1e-8)
    assert float(relative.max())<.009
    report={'version':V,'source':source.name,'source_sha256':manifest['sha256'],
      'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'filter':'OpenImageDenoise RT HDR (bundled Blender library), CPU/high default',
      'lightmap_filter_unavailable':'Bundled RTLightmap commit reported unsupported combination of input features; its output was not produced or used.',
      'seconds':time.monotonic()-start,'resolution':[width,height],
      'source_preserved':True,'linear_radiance':True,'exposure_rescaled':False,
      'source_mean_rgb':rgb.mean(axis=(0,1)).tolist(),'filtered_mean_rgb':output.mean(axis=(0,1)).tolist(),
      'written_RGBE_max_channel_relative_quantization':float(relative.max()),
      'visual_acceptance':False,'limitation':'Statistical denoising of fixed-light cache; inspect UV edges and contact shadows before use.',
      'documentation':'https://www.openimagedenoise.org/documentation.html#rtlightmap'}
    (R/'evidence'/V/'diffuse_linear_denoise.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
finally:
    if filter:release_filter(filter)
    release_device(device);dll_path.close()
