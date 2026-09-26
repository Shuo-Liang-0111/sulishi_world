"""Read actual GLB accessors and node transforms without loading image payloads."""
import json
import mmap
import struct
from pathlib import Path
import numpy as np


class GLB:
    def __init__(self,path):
        path=Path(path)
        if path.suffix=='.gltf':
            self.doc=json.loads(path.read_text(encoding='utf-8'));assert len(self.doc['buffers'])==1
            buffer=self.doc['buffers'][0];binary=path.parent/buffer['uri']
            assert binary.resolve().parent==path.resolve().parent and binary.suffix=='.bin'
            self.stream=binary.open('rb');self.raw=mmap.mmap(self.stream.fileno(),0,access=mmap.ACCESS_READ)
            self.base=0;self.bin_length=len(self.raw);assert self.bin_length==buffer['byteLength']
        else:
            self.stream=path.open('rb');self.raw=mmap.mmap(self.stream.fileno(),0,access=mmap.ACCESS_READ)
            magic,version,total=struct.unpack_from('<4sII',self.raw)
            assert magic==b'glTF' and version==2 and total==len(self.raw)
            length,tag=struct.unpack_from('<II',self.raw,12);assert tag==0x4e4f534a
            self.doc=json.loads(self.raw[20:20+length]);offset=20+length
            self.bin_length,tag=struct.unpack_from('<II',self.raw,offset);assert tag==0x004e4942
            self.base=offset+8;assert self.base+self.bin_length==total
        self.parents={};self.matrices={}
        for i,node in enumerate(self.doc['nodes']):
            for child in node.get('children',[]):
                assert child not in self.parents
                self.parents[child]=i

    def accessor(self,index):
        a=self.doc['accessors'][index]
        assert not a.get('normalized',False)
        dtype=np.dtype({5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']])
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        def read(view_index,byte_offset,count,components,kind,sparse=False):
            view=self.doc['bufferViews'][view_index];assert view['buffer']==0
            if sparse:assert 'byteStride' not in view and 'target' not in view
            offset=view.get('byteOffset',0)+byte_offset
            stride=view.get('byteStride',components*kind.itemsize)
            assert byte_offset>=0 and stride>=components*kind.itemsize
            if count==0:return np.empty((0,components),dtype=kind)
            assert offset+(count-1)*stride+components*kind.itemsize<=view.get('byteOffset',0)+view['byteLength']
            return np.ndarray((count,components),dtype=kind,buffer=self.raw,offset=self.base+offset,strides=(stride,kind.itemsize)).copy()
        if 'bufferView' in a:
            result=read(a['bufferView'],a.get('byteOffset',0),a['count'],width,dtype)
        else:
            assert 'sparse' in a and a.get('byteOffset',0)==0
            result=np.zeros((a['count'],width),dtype=dtype)
        if 'sparse' in a:
            sparse=a['sparse'];count=sparse['count'];assert 0<count<=a['count']
            indices=sparse['indices'];values=sparse['values']
            index_dtype=np.dtype({5121:'u1',5123:'<u2',5125:'<u4'}[indices['componentType']])
            ids=read(indices['bufferView'],indices.get('byteOffset',0),count,1,index_dtype,True).ravel().astype(np.int64)
            assert np.all(np.diff(ids)>0) and ids[0]>=0 and ids[-1]<a['count']
            replacement=read(values['bufferView'],values.get('byteOffset',0),count,width,dtype,True)
            result[ids]=replacement
        assert np.isfinite(result).all()
        return result

    def world(self,index,stack=()):
        assert index not in stack,'Hierarchy cycle'
        if index in self.matrices:return self.matrices[index]
        n=self.doc['nodes'][index]
        if 'matrix' in n:m=np.asarray(n['matrix'],dtype=np.float64).reshape(4,4).T
        else:
            x,y,z,w=n.get('rotation',[0,0,0,1]);assert abs(x*x+y*y+z*z+w*w-1)<1e-5
            r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
            m=np.eye(4);m[:3,:3]=r@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
        if index in self.parents:m=self.world(self.parents[index],stack+(index,))@m
        self.matrices[index]=m;return m

    def close(self):self.raw.close();self.stream.close()
