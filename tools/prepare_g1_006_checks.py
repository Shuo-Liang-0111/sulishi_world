import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
code="import bpy,json\nfrom pathlib import Path\np=Path('F:/MyWorld/ZurichWorld')\nw=json.loads((p/'runtime/bellevue_working.json').read_text())\nbpy.ops.wm.open_mainfile(filepath=w['native'])\nassert bpy.context.scene['version']==w['version']\nprint('Reopened saved '+w['version'])"
calls=[{'tool':'execute_blender_code','arguments':{'code':code}}]
for name in ['blender_export_bellevue.py','blender_export_review_sky.py','blender_verify_bellevue_export.py']:
    calls.append({'tool':'execute_blender_code','arguments':{'code':(ROOT/'tools'/name).read_text()}})
(ROOT/'runtime/g1_006_export_calls.json').write_text(json.dumps(calls))
