"""Original metre-scale coating microstructure, not a photograph of the site."""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image
from scipy.ndimage import gaussian_filter
R=Path(__file__).resolve().parents[1];D=R/'derived/materials/satin_grey_coat';D.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(1205);N=2048
def noise(sigma):
 a=gaussian_filter(rng.normal(size=(N,N)).astype(np.float32),sigma,mode='wrap');return a/max(float(a.std()),1e-7)
fine=noise(.75);medium=noise(13);broad=noise(102)
base=np.array([.24,.28,.27],np.float32)
rgb=base[None,None,:]*(1+.012*fine[:,:,None]+.013*medium[:,:,None]+.016*broad[:,:,None])
rgb=np.clip(rgb,0,1);srgb=np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)
Image.fromarray(np.uint8(np.clip(srgb*255,0,255))).save(D/'albedo.png')
rough=np.clip(.51+.017*fine+.025*medium+.015*broad,.38,.64)
Image.fromarray(np.uint8(rough*255),'L').save(D/'roughness.png')
height=.000012*fine+.000008*medium;dy,dx=np.gradient(height,1/N);normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8((normal*.5+.5)*255)).save(D/'normal_gl.png')
(D/'receipt.json').write_text(json.dumps({'basis':'Original inferred satin exterior paint; no on-site scan or observed wear claimed. Coating has small roughness variation and micrometre microrelief, without invented rust.','seed':1205,'tile_metres':[1,1],'pixels':[N,N],'normal_relief_rms_m':.000014,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.png')}},indent=2))
print(json.dumps({'directory':str(D),'maps':3,'size':N}))
