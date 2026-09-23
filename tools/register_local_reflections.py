"""Register inspected native reflection captures on their matching runtime only."""
import hashlib
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3'],default='G1_015r3');parser.add_argument('--include-east',action='store_true');parser.add_argument('--include-fountain',action='store_true');args=parser.parse_args();VERSION=args.version
metadata_path = ROOT / 'web/assets' / f'{VERSION}_bellevue.json'
metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
assert metadata['version'] == VERSION
probes = []
for key in ['north', 'front']+(['east_info','east_bin'] if args.include_east else [])+(['fountain'] if args.include_fountain else []):
    receipt_path = ROOT / 'evidence' / VERSION / f'service_reflection_{key}.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    assert receipt['version'] == VERSION and receipt['native_unchanged']
    path = ROOT / 'web/assets' / receipt['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
    probes.append(receipt)
metadata['local_reflection_probes'] = probes
metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'version': VERSION, 'local_reflections': [p['key'] for p in probes],
                  'native_geometry_and_materials_unchanged': True,
                  'runtime_visual_acceptance': False}))
