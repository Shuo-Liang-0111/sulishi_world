import json
from pathlib import Path
p=Path('tools/blender_render_bellevue.py').read_text()
calls=[{'tool':'execute_blender_code','arguments':{'code':'REVIEW_CAMERA='+repr(c)+'\n'+p}} for c in ['BE_QA_ROAD_SOUTH','BE_QA_STATION_STREETS']]
Path('runtime/g1_007_render_calls.json').write_text(json.dumps(calls))
