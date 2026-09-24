"""Reject empty/truncated render files even when Blender reports FINISHED."""
from pathlib import Path
import hashlib,struct,zlib

def verify_png(path,expected_size=None):
    data=Path(path).read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n',('Missing PNG signature',str(path),len(data))
    offset=8;header=None;image_chunks=[];ended=False
    while offset<len(data):
        assert offset+12<=len(data),('Truncated PNG chunk',str(path))
        size=struct.unpack_from('>I',data,offset)[0];kind=data[offset+4:offset+8]
        end=offset+12+size;assert end<=len(data),('Truncated PNG payload',str(path))
        payload=data[offset+8:offset+8+size]
        crc=struct.unpack_from('>I',data,offset+8+size)[0]
        assert zlib.crc32(kind+payload)&0xffffffff==crc,('PNG CRC mismatch',str(path),kind)
        if kind==b'IHDR':
            assert header is None and offset==8 and size==13
            header=struct.unpack('>IIBBBBB',payload)
        elif kind==b'IDAT':image_chunks.append(payload)
        elif kind==b'IEND':
            assert size==0 and end==len(data);ended=True
        offset=end
    assert ended and header and image_chunks,('Incomplete PNG',str(path))
    width,height,depth,color,compression,filtering,interlace=header
    assert width*height<=64_000_000 and depth in [8,16] and color in [2,6]
    assert compression==0 and filtering==0 and interlace==0
    if expected_size is not None:assert (width,height)==tuple(expected_size),(str(path),header,expected_size)
    channels=3 if color==2 else 4;stride=1+width*channels*depth//8
    decoder=zlib.decompressobj();pixels=decoder.decompress(b''.join(image_chunks),height*stride+1)
    assert decoder.eof and not decoder.unused_data and len(pixels)==height*stride,('Invalid PNG scanlines',str(path))
    assert all(pixels[i*stride]<=4 for i in range(height))
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),size=[width,height],decoded_scanlines_verified=True)
