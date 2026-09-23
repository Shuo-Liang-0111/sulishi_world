"""Original numerical PBR maps for inferred gray-brown, furrowed Sophora bark."""
from pathlib import Path
import json,hashlib,numpy as np
from scipy.ndimage import gaussian_filter,zoom
from PIL import Image
R=Path(__file__).resolve().parents[1];D=R/'derived/materials/sophora_bark';D.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(119453);H,W=4096,1024
def noise(h,w,sy,sx):
 a=gaussian_filter(rng.standard_normal((h,w)).astype(np.float32),(sy,sx),mode='wrap');a/=a.std();return zoom(a,(H/h,W/w),order=3,mode='grid-wrap',grid_mode=True)
x=np.arange(W,dtype=np.float32)[None,:]/W;y=np.arange(H,dtype=np.float32)[:,None]/H
warp=.009*noise(512,128,16,6);phase=x+warp+.006*np.sin(2*np.pi*y*3+2*np.pi*x*2)
furrows=np.zeros((H,W),dtype=np.float32)
for i in range(30):
 center=(i+rng.uniform(-.28,.28))/30;width=rng.uniform(.0015,.0045)
 dist=abs((phase-center+.5)%1-.5);groove=np.exp(-(dist/width)**2)
 modulation=.70+.30*np.sin(2*np.pi*y*rng.integers(2,7)+rng.uniform(0,6.28))**2
 furrows=np.maximum(furrows,groove*modulation)
grain=noise(1024,256,.6,.65);coarse=noise(512,128,12,3);long=noise(512,128,8,.8)
height=.00030*long+.00006*grain-.0022*furrows
shade=np.clip(.014*grain+.022*np.tanh(coarse)-.12*furrows,-.18,.08)
color=np.clip(np.array([.36,.323,.28])[None,None,:]+shade[:,:,None],.07,.62)
rough=np.clip(.84+.04*furrows+.022*grain,.70,.98)
dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*1.2/W);dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*4/H)
normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
files=[]
for name,a in [('albedo',color),('roughness',rough),('normal_gl',normal*.5+.5)]:
 f=D/(name+'.png');Image.fromarray(np.uint8(np.clip(a*255,0,255))).save(f,compress_level=6);files.append({'name':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(D/'receipt.json').write_text(json.dumps({'creator':'Project-authored numerical PBR surface; no reference photo pixels used','physical_extent_m':[1.2,4.0],'resolution':[W,H],'seed':119453,'basis':'Inferred individual texture. NC State describes gray-brown bark with age-related reddish brown furrows; this is not a scan of a Zurich tree.','morphology_reference':'https://plants.ces.ncsu.edu/plants/styphnolobium-japonicum/','files':files},indent=2))
print(json.dumps({'material':str(D),'generated':len(files)}))
