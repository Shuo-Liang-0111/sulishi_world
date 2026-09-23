"""Promote a checked working revision, never a claim that G1 is finished."""
import json,hashlib,shutil,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['bellevue','station'],default='bellevue');args=parser.parse_args()
working_path='runtime/station_road_working.json' if args.scope=='station' else 'runtime/bellevue_working.json'
preview_path='web/assets/station_preview.json' if args.scope=='station' else 'web/assets/bellevue_preview.json'
working=json.loads((ROOT/working_path).read_text())
V=working['version'];evidence=ROOT/'evidence'/V
roundtrip=json.loads((evidence/'roundtrip.json').read_text())
runtime=json.loads((evidence/'runtime_review.json').read_text())
assert roundtrip['version']==runtime['version']==V and roundtrip['native_reopen_verified'] and runtime['loading_verified']
assert runtime.get('candidate_can_replace_default') is True, 'Actual visual review has not accepted this working candidate; keep the existing default.'
metadata=json.loads((ROOT/f'web/assets/{V}_bellevue.json').read_text())
assert metadata['version']==V and metadata['exported_authored_objects']==roundtrip['identities_verified']
assert (ROOT/f'web/assets/{V}_sky.hdr').is_file()
for key in ['authored','authored_runtime','context_patch']:
    item=metadata[key];path=ROOT/'web/assets'/item['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
old=json.loads((ROOT/'runtime/current_scene.json').read_text())
if old['version']!=V:
    (ROOT/'runtime'/f"{old['version']}_scene_pointer.json").write_text(json.dumps(old,indent=2))
    shutil.copyfile(ROOT/'web/assets/current.json',ROOT/'web/assets'/f"{old['version']}_manifest.json")
manifest=json.loads((ROOT/preview_path).read_text())
assert manifest['version']==V and manifest['construction_version']==V
(ROOT/'web/assets/current.json').write_text(json.dumps(manifest,indent=2))
record={**old,'version':V,'native':working['native'],'viewer_version':V,
        'stage':'Bellevue_local_reconstruction_working','accepted':False,
        'native_sha256':hashlib.sha256(Path(working['native']).read_bytes()).hexdigest(),
        'authored_export':str(ROOT/'web/assets'/metadata['authored']['file']),
        'authored_runtime':str(ROOT/'web/assets'/metadata['authored_runtime']['file']),
        'context_patch':str(ROOT/'web/assets'/metadata['context_patch']['file']),
        'viewer_note':f'Same-version local native reconstruction plus immutable original photo base and verified {len(metadata["changed_nodes"])}-node delta. No whole-area acceptance.'}
(ROOT/'runtime/current_scene.json').write_text(json.dumps(record,indent=2))
print(json.dumps({'version':V,'native':working['native'],'accepted':False,'goal':'active'}))
