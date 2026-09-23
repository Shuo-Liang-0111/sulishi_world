"""Original subtle brushed-steel roughness, with documented physical scale."""
from pathlib import Path
import numpy as np,json,hashlib
from scipy.ndimage import gaussian_filter
from PIL import Image
R=Path(__file__).resolve().parents[1];D=R/'derived/materials/ground_stainless';D.mkdir(parents=True,exist_ok=True)
N=2048;rng=np.random.default_rng(631)
def field(sig):
 x=gaussian_filter(rng.normal(size=(N,N)).astype(np.float32),sig,mode='wrap');return x/max(float(x.std()),1e-6)
grain=field((10,.6));fine=field(.6);broad=field(80)
rough=np.clip(.47+.018*grain+.012*fine+.013*broad,.36,.58)
Image.fromarray(np.uint8(rough*255)).save(D/'roughness.png')
height=.0000025*grain+.000001*fine;dy,dx=np.gradient(height,1/N);normal=np.stack([-dx,dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8((normal*.5+.5)*255)).save(D/'normal_gl.png')
(D/'receipt.json').write_text(json.dumps({'basis':'Original inferred dry-ground stainless microstructure; not a scan of this specific installation. No invented rust or large damage.','tile_metres':[1,1],'resolution':[N,N],'seed':631,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.png')}},indent=2))
print(json.dumps({'maps':2,'resolution':N}))
