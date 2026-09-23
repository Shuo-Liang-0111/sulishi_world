"""Read the actual Radiance RGBE file and inspect bounded receiver samples."""
import json,re
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];V='G1_015r3'
path=R/'web/assets'/f'{V}_service_diffuse.hdr'
with path.open('rb') as stream:
    assert stream.readline().startswith(b'#?')
    while stream.readline().strip():pass
    size=stream.readline().decode().strip();match=re.fullmatch(r'-Y (\d+) \+X (\d+)',size);assert match,size
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
                assert n>0 and x+n<=width
                x+=n
rgb=np.ldexp(rgbe[:,:,:3].astype(np.float32),rgbe[:,:,3,None].astype(np.int32)-136)
assert np.isfinite(rgb).all() and np.any(rgb>.02)
manifest=json.loads((R/'derived/runtime_occlusion'/V/'manifest.json').read_text());uvs=np.load(R/manifest['uv_file'])
samples={}
for rec in manifest['receivers']:
    if rec['name'] not in ['SV_SOURCE_SOFFIT','SV_NORTH_SUBSTRATE','SV_CERAMIC_FACE_TILES','BS_ASPHALT']:continue
    uv=uvs[rec['uv_key']]
    # Loop vertices provide a diagnostic distribution, not a full texel coverage proof.
    xy=np.clip((uv*np.array([width,height])).astype(int),[0,0],[width-1,height-1]);value=rgb[height-1-xy[:,1],xy[:,0]].mean(axis=1)
    samples[rec['name']]={'sample_count':len(value),'linear_mean_percentiles':np.percentile(value,[5,50,95]).tolist()}
thumb=rgb[::4,::4];thumb=np.power(thumb/(1+thumb),1/2.2)
preview=R/'evidence'/V/'diffuse_atlas_diagnostic.png';Image.fromarray((np.clip(thumb,0,1)*255).astype(np.uint8)).save(preview)
report={'version':V,'resolution':[width,height],'all_values_finite':True,'samples':samples,
    'preview':'Reinhard/gamma diagnostic atlas only; not a scene render or visual acceptance.'}
(R/'evidence'/V/'diffuse_atlas_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
