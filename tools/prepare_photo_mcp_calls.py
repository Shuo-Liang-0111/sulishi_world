from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
code=(ROOT/'tools/blender_import_photo_batch.py').read_text(encoding='utf-8')
calls=[]
for start in range(0,manifest['leaf_count'],150):
    calls.append({'tool':'execute_blender_code','arguments':{'code':f'START={start}\nEND={start+150}\n'+code}})
(ROOT/'runtime/photo_import_calls.json').write_text(json.dumps(calls),encoding='utf-8')
print(json.dumps({'calls':len(calls),'nodes':manifest['leaf_count']}))
