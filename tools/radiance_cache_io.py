"""Linear RGBE light-cache I/O. Row zero remains the top (-Y Radiance order)."""
import re
import numpy as np

def read_hdr(path):
    with open(path,'rb') as stream:
        assert stream.readline().startswith(b'#?')
        while stream.readline().strip():pass
        match=re.fullmatch(r'-Y (\d+) \+X (\d+)',stream.readline().decode().strip())
        assert match
        height,width=map(int,match.groups());rgbe=np.empty((height,width,4),np.uint8)
        for y in range(height):
            header=stream.read(4);assert header[:2]==b'\x02\x02' and header[2]*256+header[3]==width
            for channel in range(4):
                x=0
                while x<width:
                    count=stream.read(1)[0]
                    if count>128:
                        n=count-128;value=stream.read(1)[0];rgbe[y,x:x+n,channel]=value
                    else:
                        n=count;rgbe[y,x:x+n,channel]=np.frombuffer(stream.read(n),np.uint8)
                    assert n>0 and x+n<=width;x+=n
    rgb=np.ldexp(rgbe[:,:,:3].astype(np.float32),rgbe[:,:,3,None].astype(np.int32)-136)
    assert np.isfinite(rgb).all()
    return np.ascontiguousarray(rgb,dtype=np.float32)

def write_hdr(path,rgb):
    assert rgb.ndim==3 and rgb.shape[2]==3 and np.isfinite(rgb).all() and rgb.min()>=0
    height,width,_=rgb.shape;assert 8<=width<32768
    maximum=rgb.max(axis=2);fraction,exponent=np.frexp(maximum)
    multiplier=np.ldexp(np.full_like(maximum,256),-exponent)
    rgbe=np.empty((height,width,4),np.uint8)
    rgbe[:,:,:3]=np.clip(rgb*multiplier[:,:,None],0,255).astype(np.uint8)
    rgbe[:,:,3]=np.where(maximum>1e-30,exponent+128,0).astype(np.uint8)
    with open(path,'wb') as stream:
        stream.write(f'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {height} +X {width}\n'.encode())
        for y in range(height):
            stream.write(bytes([2,2,width//256,width%256]))
            for channel in range(4):
                values=np.ascontiguousarray(rgbe[y,:,channel]).tobytes()
                for x in range(0,width,127):
                    chunk=values[x:x+127];stream.write(bytes([len(chunk)]));stream.write(chunk)
