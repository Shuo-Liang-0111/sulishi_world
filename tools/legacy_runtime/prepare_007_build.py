import json
from pathlib import Path
code='REVIEW_CAMERA='+repr('BE_QA_INTERIOR')+'\n'+Path('tools/blender_render_bellevue.py').read_text()
calls=[{'tool':'execute_blender_code','arguments':{'code':code}},{'tool':'execute_blender_code','arguments':{'code':Path('tools/blender_build_bellevue_roads.py').read_text()}}]
Path('runtime/g1_007_build_calls.json').write_text(json.dumps(calls))
