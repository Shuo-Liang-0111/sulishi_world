"""Bounded photo replacement and original metre-scale granite PBR maps.

The three downloaded photographs are visual references, never texture inputs.
"""
import json, hashlib, runpy
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter, zoom, map_coordinates
from PIL import Image
from shapely.geometry import Point, mapping

R=Path(__file__).resolve().parents[1]
D=R/'derived/bellevue/fountain59'; D.mkdir(exist_ok=True)
T=D/'textures'; T.mkdir(exist_ok=True)
rng=np.random.default_rng(590466); n=2048
def field(k):
    a=rng.normal(size=(k,k)).astype(np.float32)
    y,x=np.mgrid[0:n,0:n].astype(np.float32)*k/n
    b=map_coordinates(a,[y,x],order=3,mode='grid-wrap')
    return b/(b.std()+1e-8)
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
coarse=field(5); grains=field(630); fine=field(1024)
warp=.014*field(7)+.006*field(17)
veins=np.sin(2*np.pi*(y*19+x*2+warp*10))
mica=(grains<-.83).astype(np.float32)
quartz=(grains>.75).astype(np.float32)
base=.47+.027*coarse+.055*grains+.018*fine+.027*veins-.095*mica+.054*quartz
rgb=np.stack([base*1.035,base*1.015,base*.975],axis=-1)
height=(gaussian_filter(grains,.65,mode='wrap')*.00012+fine*.000018)
gy,gx=np.gradient(height,1/n); normal=np.stack([-gx,-gy,np.ones_like(gx)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(T/'granite_normal.png')
rough=np.clip(.63+.038*grains+.024*coarse,.44,.83)
for kind,colorfac,roughfac in [('dry',1.,1.),('wet',.74,.60),('underside',.88,1.04)]:
    Image.fromarray(np.uint8(np.clip(rgb*colorfac,0,1)*255)).save(T/f'granite_{kind}_color.png')
    Image.fromarray(np.uint8(np.clip(rough*roughfac,0,1)*255)).save(T/f'granite_{kind}_roughness.png')
receipt={'method':'Original seeded mineral field; no photographic pixels used. Castione grain and subtle banding are an inferred visual proxy, not a scan of the actual basin.',
 'tile_size_m':1.,'resolution':n,'normal_height_std_m':float(height.std()),
 'images':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in T.glob('*.png')}}
(D/'material_basis.json').write_text(json.dumps(receipt,indent=2))
centre=[2683606.575,1246801.044996]; ground=408.3791313
mask=Point(centre).buffer(2.08,quad_segs=96)
cut='fountain59_photo_cut.json'
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_BASE':'grove_continuous_upper_photo_cut.json','CUT_MASK':mask,
 'CUT_LOWER':ground-.13,'CUT_UPPER':ground+1.46,'CUT_OUTPUT':cut,
 'CUT_STATS_KEY':'fountain59_stats',
 'CUT_DESCRIPTION':'Fountain59: replace only its 4m basin footprint +8cm margin between LN02 408.249..409.839m. Existing physical AV3573 ground backs the cut. Keep trees, nearby facilities and original source collection.'})
input={'base_version':'G1_017r1','version':'G1_018','source_id':'wvz_brunnen.466','fountain_number':'59',
 'origin':[2683775,1246700,400],'centre_lv95':centre,'ground_local':ground-400,
 'basin_diameter_m':4.,'basin_rim_height_m':.78,'maximum_sculpture_height_m':.29,
 'source_cut_file':'derived/bellevue/west_context/'+cut,
 'source_cut_sha256':hashlib.sha256((R/'derived/bellevue/west_context'/cut).read_bytes()).hexdigest(),
 'reference_basis':'Official inventory for identity/XY/approximate dimensions; actually inspected Roland Fischer2010 overall+figure and2011 overflow photos. Profile, rotation, unseen sculpture surfaces and water hydraulics inferred.',
 'reference_photos':['overall_2010.jpg','detail_2010.jpg','detail_2011.jpg'],
 'natural_use_status':'Working native geometry; running water is a normal facility state. No task props/buttons/events. Runtime water interaction not yet implemented.'}
(D/'input.json').write_text(json.dumps(input,indent=2))
print(json.dumps({'textures':len(receipt['images']),'cut':input['source_cut_file'],'ready':True}))
