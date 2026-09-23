"""Reuse proven continuous UV topology; illumination must be freshly computed."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];V='G1_017r1'
w=json.loads((R/'runtime/station_road_working.json').read_text());assert w['version']==V
repair=json.loads((R/'evidence'/V/'canopy_repair.json').read_text());assert repair['authored_identity_list_unchanged'] and repair['original_source_count']==2039
source_path=R/'derived/runtime_occlusion/G1_016r1/manifest.json';source=json.loads(source_path.read_text())
assert 'contiguous' in source['uv_file']
source.update(version=V,native=w['native'],layout_inherited_from='G1_016r1',layout_parent_manifest_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    limitation='Continuous UV1 layout retained for unchanged authored geometry. Export and bake verify every receiver topology hash. Neutral scalar carrier has no old illumination. All diffuse and reflection captures must be newly computed after photographic occluder cleanup.')
D=R/'derived/runtime_occlusion'/V;D.mkdir(exist_ok=True);(D/'manifest.json').write_text(json.dumps(source,indent=2))
print('Continuous UV layout prepared; no prior illumination or visual acceptance copied.')
