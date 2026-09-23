"""Original fine-grained, compacted soil maps for inferred public tree pits."""
from pathlib import Path
import numpy as np,json,hashlib
from scipy.ndimage import gaussian_filter,zoom
from PIL import Image
R=Path(__file__).resolve().parents[1];D=R/'derived/materials/tree_soil';D.mkdir(exist_ok=True);N=2048;rng=np.random.default_rng(1800)
def noise(s,sigma):
 a=gaussian_filter(rng.standard_normal((s,s)).astype(np.float32),sigma,mode='wrap');a/=a.std();return zoom(a,N/s,order=1,mode='grid-wrap',grid_mode=True)
grain=noise(1024,.65);clump=noise(256,1.7);broad=noise(64,2)
color=np.array([.25,.219,.177])+(.037*grain+.021*clump+.009*broad)[:,:,None];rough=np.clip(.88+.025*grain,.72,.98)
h=.0006*grain+.0012*clump+.001*broad;dx=(np.roll(h,-1,1)-np.roll(h,1,1))*N/2;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*N/2
normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
files=[]
for name,a in [('albedo',color),('roughness',rough),('normal_gl',normal*.5+.5)]:
 p=D/f'{name}.png';Image.fromarray(np.uint8(np.clip(a*255,0,255))).save(p);files.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(D/'receipt.json').write_text(json.dumps({'kind':'Original procedural inference, not a soil scan','physical_tile_m':1,'resolution':N,'files':files},indent=2))
print(json.dumps({'soil':str(D),'resolution':N}))
