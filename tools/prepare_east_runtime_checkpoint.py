"""Carry only verified UV layout, not old illumination acceptance, to016r1."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];V='G1_016r1'
w=json.loads((R/'runtime/station_road_working.json').read_text());assert w['version']==V
repair=json.loads((R/'evidence'/V/'surface_repair.json').read_text());assert repair['removed_faces']==71
source=json.loads((R/'derived/runtime_occlusion/G1_015r3/manifest.json').read_text())
source.update(version=V,native=w['native'],layout_inherited_from='G1_015r3',
    invalid_scalar_ao_receivers=[x['name'] for x in source['receivers']],
    limitation='Previous scalar AO is disabled for all receivers; only its UV layout is reused. Export and new diffuse bake independently verify every evaluated receiver topology hash. Fresh016r1 diffuse transport replaces scalar AO.')
D=R/'derived/runtime_occlusion'/V;D.mkdir(exist_ok=True);(D/'manifest.json').write_text(json.dumps(source,indent=2))
views=['INFO_WIDE','REVERSE_WIDE','BIN_OPENING','INFO','REVERSE'];images=[]
for suffix in views:
    path=R/'evidence'/V/('BE_QA_SOUTH_EAST_'+suffix+'.png');assert path.is_file()
    images.append({'file':str(path.relative_to(R)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
receipt={'version':V,'images_actually_inspected':images,'local_repairs_verified':['Full information frames and feet visible from both sides','Correct readable map orientation on reverse','Bin aperture and separate liner visible','Dark root-atlas repeat removed in same INFO camera','Ray-identified low photographic remnant absent in same REVERSE camera'],
    'limitations':['Background photographic trees, temporary tents and unrebuilt buildings still visibly unfit','Material/use-wear detail remains inferred','No collision, opening, disposal or other natural-use acceptance','Full-area visual quality not accepted'],
    'accepted':False,'full_G1_complete':False}
(R/'evidence'/V/'native_visual_review.json').write_text(json.dumps(receipt,indent=2))
print('EAST_NATIVE_LOCAL_VIEWS_RECORDED_AND_UV_LAYOUT_PREPARED',V)
