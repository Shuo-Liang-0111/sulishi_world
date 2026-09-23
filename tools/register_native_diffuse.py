"""Register a fixed-light transport cache, without claiming visual acceptance."""
import hashlib
import json
import argparse
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3'],default='G1_015r3');version=parser.parse_args().version
manifest=json.loads((root/'derived/runtime_lighting'/version/'manifest.json').read_text())
path=root/'web/assets'/f'{version}_bellevue.json'
metadata=json.loads(path.read_text())
assert manifest['version']==metadata['version']==version
assert manifest['uv_topology_verified'] and not manifest['native_saved']
assert manifest.get('written_linear_max_relative_error',1)<.009
assert hashlib.sha256((root/'web/assets'/manifest['file']).read_bytes()).hexdigest()==manifest['sha256']
assert len(manifest['receivers'])==metadata['indirect_occlusion']['receivers_verified']
denoise=json.loads((root/'evidence'/version/'diffuse_linear_denoise.json').read_text())
assert denoise['version']==version and denoise['source_sha256']==manifest['sha256']
assert denoise['linear_radiance'] and not denoise['exposure_rescaled']
assert hashlib.sha256((root/'web/assets'/denoise['file']).read_bytes()).hexdigest()==denoise['sha256']
manifest['raw_file']=manifest['file'];manifest['raw_sha256']=manifest['sha256']
manifest['file']=denoise['file'];manifest['sha256']=denoise['sha256']
manifest['denoising']=denoise['filter']
metadata['static_diffuse_lighting']=manifest
path.write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'version':version,'receivers':len(manifest['receivers']),'fixed_native_light_state':True,'visual_acceptance':False}))
