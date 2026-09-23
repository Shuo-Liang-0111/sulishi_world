"""Inspect the registered linear cache without changing any scene pixels."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from radiance_cache_io import read_hdr
R=Path(__file__).resolve().parents[1];V='G1_015r3'
record=json.loads((R/'web/assets'/f'{V}_bellevue.json').read_text())['static_diffuse_lighting']
rgb=read_hdr(R/'web/assets'/record['file']);height,width,_=rgb.shape
layout=json.loads((R/'derived/runtime_occlusion'/V/'manifest.json').read_text());uvs=np.load(R/layout['uv_file'])
samples={}
for item in layout['receivers']:
    if item['name'] not in ['SV_SOURCE_SOFFIT','BS_ASPHALT']:continue
    uv=uvs[item['uv_key']].reshape(-1,3,2).mean(axis=1)
    xy=np.clip((uv*np.array([width,height])).astype(int),[0,0],[width-1,height-1])
    values=rgb[height-1-xy[:,1],xy[:,0]].mean(axis=1)
    samples[item['name']]={'triangle_centers_sampled':len(values),'percentiles_5_50_95':np.percentile(values,[5,50,95]).tolist()}
thumbnail=rgb[::4,::4];thumbnail=np.power(thumbnail/(1+thumbnail),1/2.2)
Image.fromarray((np.clip(thumbnail,0,1)*255).astype(np.uint8)).save(R/'evidence'/V/'linear_diffuse_atlas_diagnostic.png')
report={'version':V,'file':record['file'],'sha256':record['sha256'],'samples':samples,
        'preview':'Reinhard/gamma atlas diagnostic only, not a scene render','scene_visual_acceptance':False}
(R/'evidence'/V/'linear_diffuse_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
