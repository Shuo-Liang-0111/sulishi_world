"""Derived, portable trunk PBR: spatially continuous flaking transition.

Original Poly Haven maps are preserved. These are new 8-bit working derivatives,
not an assertion of lossless source conversion or a scan of either local tree.
"""
from pathlib import Path
import json,hashlib,numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,zoom,map_coordinates
R=Path(__file__).resolve().parents[1];D=R/'derived/materials/plane_trunk';D.mkdir(parents=True,exist_ok=True)
N=4096;rng=np.random.default_rng(119962)
u=np.arange(N,dtype=np.float32)[None,:]/N;z=(1-np.arange(N,dtype=np.float32)[:,None]/(N-1))*4.5
def noise(size,sigma):
 a=gaussian_filter(rng.standard_normal((size,size)).astype(np.float32),sigma,mode='wrap');a/=a.std()
 return zoom(a,N/size,order=1,mode='grid-wrap',grid_mode=True)
field=.43*noise(128,3.2)+.15*noise(512,2.5)+.05*noise(1024,1.2)
front=1.65+field+.24*np.sin(2*np.pi*u*3)
mask=np.clip((z-front)/.055+.5,0,1);mask=mask*mask*(3-2*mask)
def sample(path,tile,mode):
 im=np.array(Image.open(path).convert(mode),dtype=np.float32)/255
 yy=np.broadcast_to(np.mod(-z/tile,1)*im.shape[0],(N,N));xx=np.broadcast_to(np.mod(u*2.5/tile,1)*im.shape[1],(N,N))
 return map_coordinates(im,[yy,xx],order=1,mode='wrap') if im.ndim==2 else np.stack([map_coordinates(im[:,:,c],[yy,xx],order=1,mode='wrap') for c in range(3)],axis=-1)
src=R/'sources/textures/polyhaven/bark_platanus';pale=R/'derived/materials/platanus_flaking';files=[]
for kind,old,new,mode in [('albedo','Diffuse','albedo','RGB'),('roughness','Rough','roughness','L'),('normal_gl','nor_gl','normal_gl','RGB')]:
 a=sample(src/f'bark_platanus_{old}_4k.png',1.5,mode);b=sample(pale/f'{new}.png',2.4,mode);m=mask if mode=='L' else mask[:,:,None]
 if kind=='albedo':
  # Blend linear colors, not gamma-encoded colors.
  linear=lambda x:np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
  c=linear(a)*(1-m)+linear(b)*m;c=np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
 elif kind=='normal_gl':
  c=(a*2-1)*(1-m)+(b*2-1)*m;c/=np.maximum(np.linalg.norm(c,axis=-1)[:,:,None],1e-6);c=c*.5+.5
 else:c=a*(1-m)+b*m
 p=D/f'{kind}.png';Image.fromarray(np.uint8(np.clip(c*255,0,255))).save(p,compress_level=6);files.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 del a,b,c
(D/'receipt.json').write_text(json.dumps({'kind':'inferred trunk atlas, not measured local bark','source':'Poly Haven bark_platanus CC0 + original procedural flaking material','physical_size_m':[2.5,4.5],'resolution':[N,N],'bit_depth':8,'source_files_untouched':True,'files':files},indent=2))
print(json.dumps({'atlas':str(D),'files':len(files),'resolution':N}))
